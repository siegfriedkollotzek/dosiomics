"""
MFI cell analysis, decoupled from Django.

Same algorithm as mfi/MFI_total_noGUI_EasyOCR.py in the main repo, but works on
a plain file path inside a per-run working directory.
"""
import os
import re
from datetime import datetime
from pathlib import Path

import cv2
import easyocr
import numpy as np
import pandas as pd
import tifffile
from PIL import Image
from openpyxl import Workbook
from openpyxl.drawing.image import Image as OpenpyxlImage
from openpyxl.utils.dataframe import dataframe_to_rows
from scipy import ndimage
from scipy.ndimage import binary_fill_holes
from skimage import io, measure, color

MODEL_DIR = Path(__file__).resolve().parent / "easyocr_models"
DEFAULT_SCALE_BAR_UM = 20

_reader = None


def parse_scale_bar_um(ocr_texts):
    """First number in the OCR output ('20 µm', '20 pm', '5O um' → 20, 20, 50), else None."""
    for text in ocr_texts:
        cleaned = text.replace('O', '0').replace('o', '0').replace('l', '1').replace('I', '1')
        m = re.search(r'\d+(?:[.,]\d+)?', cleaned)
        if m:
            value = float(m.group().replace(',', '.'))
            if value > 0:
                return value
    return None


def get_reader():
    """EasyOCR reader is expensive to build – create it once and reuse it."""
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(
            ['en'],
            gpu=False,
            model_storage_directory=str(MODEL_DIR),
            download_enabled=False,  # models are shipped with the app, never download
        )
    return _reader


class CellAnalyzer:
    def __init__(self, file_path):
        self.file_path = str(file_path)
        self.merged_image = None
        self.largest_cell_mask = None
        self.mfi_results = None
        self.binary_image_path = None
        self.r_path = None
        self.g_path = None
        self.b_path = None

    def load_image(self):
        """Loads the image from the specified file path."""
        self.merged_image = np.array(Image.open(self.file_path))
        if self.merged_image.ndim != 3 or self.merged_image.shape[2] < 3:
            raise ValueError("Image must be an RGB image (3 channels).")
        self.merged_image = self.merged_image[:, :, :3]
        print(f"Loaded image from {self.file_path}")

    def detect_scale_bar_and_calculate_size(self):
        """Detects scale bar and calculates pixel size in micrometers using EasyOCR."""
        reader = get_reader()
        image = tifffile.imread(self.file_path)

        if len(image.shape) == 3 and image.shape[2] >= 3:
            gray_image = np.mean(image[:, :, :3], axis=2).astype(np.uint8)
        else:
            gray_image = image.astype(np.uint8)

        threshold = np.max(gray_image) * 0.9
        _, binary_image = cv2.threshold(gray_image, threshold, 255, cv2.THRESH_BINARY)
        labeled_image, num_features = ndimage.label(binary_image)
        sizes = ndimage.sum(binary_image, labeled_image, range(num_features + 1))
        max_label = np.argmax(sizes)
        scale_bar = labeled_image == max_label
        scale_bar_length_pixels = np.sum(np.max(scale_bar, axis=0))

        y_indices, x_indices = np.where(scale_bar)
        y_min = np.min(y_indices)
        x_min = np.min(x_indices)
        x_max = np.max(x_indices)
        number_region = gray_image[max(0, y_min - 30):y_min, x_min:x_max]

        ocr_result = reader.readtext(number_region, detail=0)
        scale_bar_length_um = parse_scale_bar_um(ocr_result)
        ocr_ok = scale_bar_length_um is not None
        if not ocr_ok:
            print("OCR failed to detect the correct scale bar length. Using default value.")
            scale_bar_length_um = DEFAULT_SCALE_BAR_UM

        pixel_size_um = scale_bar_length_um / scale_bar_length_pixels
        image_height_pixels, image_width_pixels = gray_image.shape
        image_width_um = image_width_pixels * pixel_size_um
        image_height_um = image_height_pixels * pixel_size_um

        print(f"Image Size in Pixels: {image_width_pixels}x{image_height_pixels}")
        print(f"Scale Bar Length in µm: {scale_bar_length_um}")
        print(f"Pixel Size in µm: {pixel_size_um}")
        return (image_height_pixels, image_width_pixels, scale_bar_length_um, scale_bar_length_pixels,
                pixel_size_um, image_width_um, image_height_um, ocr_result, ocr_ok)

    def extract_channels(self):
        """Extracts R, G, B channels and saves them as separate files."""
        R_channel, G_channel, B_channel = (self.merged_image[:, :, 0],
                                           self.merged_image[:, :, 1],
                                           self.merged_image[:, :, 2])
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.dirname(self.file_path)
        self.r_path = os.path.join(output_dir, f'R_channel_{now}.tif')
        self.g_path = os.path.join(output_dir, f'G_channel_{now}.tif')
        self.b_path = os.path.join(output_dir, f'B_channel_{now}.tif')

        io.imsave(self.r_path, R_channel, check_contrast=False)
        io.imsave(self.g_path, G_channel, check_contrast=False)
        io.imsave(self.b_path, B_channel, check_contrast=False)
        print(f"Channels saved: {self.r_path}, {self.g_path}, {self.b_path}")

    def find_largest_cell(self):
        """Finds and saves the largest cell region as a binary image."""
        gray_image = color.rgb2gray(self.merged_image)
        threshold_value = 0.08
        binary = gray_image > threshold_value
        labels = measure.label(binary)
        regions = measure.regionprops(labels)
        if not regions:
            raise ValueError("No cell region found in the image.")
        largest_region = max(regions, key=lambda r: r.area)
        self.largest_cell_mask = labels == largest_region.label
        filled_largest_cell_binary = binary_fill_holes(self.largest_cell_mask)
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.binary_image_path = os.path.join(os.path.dirname(self.file_path), f'Largest_Cell_Binary_{now}.tif')
        io.imsave(self.binary_image_path, filled_largest_cell_binary.astype(np.uint8) * 255, check_contrast=False)
        print(f"Largest cell binary image saved: {self.binary_image_path}")

    def calculate_mfi(self):
        """Calculates Mean Fluorescence Intensity (MFI) for the largest cell."""
        R_channel, G_channel, B_channel = (self.merged_image[:, :, 0],
                                           self.merged_image[:, :, 1],
                                           self.merged_image[:, :, 2])
        self.mfi_results = (np.mean(R_channel[self.largest_cell_mask]),
                            np.mean(G_channel[self.largest_cell_mask]),
                            np.mean(B_channel[self.largest_cell_mask]))
        print(f"MFI - R: {self.mfi_results[0]:.2f}, G: {self.mfi_results[1]:.2f}, B: {self.mfi_results[2]:.2f}")

    def create_report(self):
        """Writes the Excel report. Returns (report_path, results_dict)."""
        output_dir = os.path.dirname(self.file_path)
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(output_dir, f'Cell_Analysis_Report_{now}.xlsx')

        largest_cell_area_pixels = int(np.sum(self.largest_cell_mask))

        (image_height_pixels, image_width_pixels, scale_bar_length_um, scale_bar_length_pixels,
         pixel_size_um, image_width_um, image_height_um, ocr_result, ocr_ok) = \
            self.detect_scale_bar_and_calculate_size()
        total_area_pixel = image_height_pixels * image_width_pixels
        total_area_um = image_width_um * image_height_um
        cell_area_percent = largest_cell_area_pixels / total_area_pixel
        cell_Area_um = total_area_um * cell_area_percent

        data = {
            'image_width_pixel': [image_width_pixels],
            'image_height_pixel': [image_height_pixels],
            'image_width_um': [image_width_um],
            'image_height_um': [image_height_um],
            'total_area_pixel': [total_area_pixel],
            'cell_Area_pixels': [largest_cell_area_pixels],
            'cell_Area_percent': [cell_area_percent],
            'total_area_um': [total_area_um],
            'cell_Area_um': [cell_Area_um],
            'scale_bar_length_pixels': [int(scale_bar_length_pixels)],
            'scale_bar_length_um': [scale_bar_length_um],
            'pixel_size_um': [pixel_size_um],
            'MFI R': [self.mfi_results[0]],
            'MFI G': [self.mfi_results[1]],
            'MFI B': [self.mfi_results[2]],
        }
        df = pd.DataFrame(data)

        wb = Workbook()
        ws = wb.active
        ws.title = "Cell Analysis Report"
        for r in dataframe_to_rows(df, index=False, header=True):
            ws.append(r)

        def resize_image(image_path, scale=0.5):
            img = Image.open(image_path)
            img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
            p = Path(image_path)
            resized_path = str(p.with_name(p.stem + "_resized.png"))
            img.convert("RGB").save(resized_path)
            return resized_path

        ws.add_image(OpenpyxlImage(resize_image(self.file_path)), 'A5')
        ws.add_image(OpenpyxlImage(resize_image(self.binary_image_path)), 'I5')
        ws.add_image(OpenpyxlImage(resize_image(self.r_path)), 'A35')
        ws.add_image(OpenpyxlImage(resize_image(self.g_path)), 'I35')
        ws.add_image(OpenpyxlImage(resize_image(self.b_path)), 'Q35')

        wb.save(report_path)
        print(f"Report saved: {report_path}")

        results = {k: v[0] for k, v in data.items()}
        results['ocr_raw'] = ", ".join(ocr_result) if ocr_result else ""
        results['ocr_ok'] = ocr_ok
        return report_path, results


def run_analysis(file_path):
    """Full pipeline on one image. Returns (report_path, results_dict, binary_mask_path)."""
    analyzer = CellAnalyzer(file_path)
    analyzer.load_image()
    analyzer.extract_channels()
    analyzer.find_largest_cell()
    analyzer.calculate_mfi()
    report_path, results = analyzer.create_report()
    return report_path, results, analyzer.binary_image_path
