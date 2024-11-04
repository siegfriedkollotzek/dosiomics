import os
from datetime import datetime
from pathlib import Path

import cv2
import easyocr
import numpy as np
import pandas as pd
import tifffile
from PIL import Image
from django.core.files.storage import FileSystemStorage
from openpyxl import Workbook
from openpyxl.drawing.image import Image as OpenpyxlImage
from openpyxl.utils.dataframe import dataframe_to_rows
from scipy import ndimage
from scipy.ndimage import binary_fill_holes
from skimage import io, measure, color


class CellAnalyzer:
    def __init__(self, file_path):
        self.merged_image = None
        self.largest_cell_mask = None
        self.mfi_results = None
        self.r_path = None
        self.g_path = None
        self.b_path = None
        fs = FileSystemStorage(location='tempfiles')  # defaults to   MEDIA_ROOT
        filename = fs.save(file_path.name, file_path)
        self.file_path = str(Path('tempfiles') / filename)

    def load_image(self):
        """Loads the image from the specified file path."""
        if not self.file_path:
            print("File path is not specified.")
            return
        self.merged_image = np.array(Image.open(self.file_path))
        print(f"Loaded image from {self.file_path}")

    def detect_scale_bar_and_calculate_size(self):
        """Detects scale bar and calculates pixel size in micrometers using EasyOCR."""
        reader = easyocr.Reader(['en'], gpu=False)
        default_scale_bar_length_um = 20
        image = tifffile.imread(self.file_path)

        if len(image.shape) == 3 and image.shape[2] == 3:
            gray_image = np.mean(image, axis=2).astype(np.uint8)
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
        try:
            scale_bar_length_um = float(
                ocr_result[0].replace('µm', '').replace('um', '').replace('wm', '').replace(' ', '').replace('m',
                                                                                                             '').replace(
                    'l', '').replace('µ', ''))
        except (ValueError, IndexError):
            print("OCR failed to detect the correct scale bar length. Using default value.")
            scale_bar_length_um = default_scale_bar_length_um

        pixel_size_um = scale_bar_length_um / scale_bar_length_pixels
        image_height_pixels, image_width_pixels = gray_image.shape
        image_width_um = image_width_pixels * pixel_size_um
        image_height_um = image_height_pixels * pixel_size_um

        print(f"Image Size in Pixels: {image_width_pixels}x{image_height_pixels}")
        print(f"Scale Bar Length in µm: {scale_bar_length_um}")
        print(f"Pixel Size in µm: {pixel_size_um}")
        return (image_height_pixels, image_width_pixels, scale_bar_length_um, scale_bar_length_pixels,
                pixel_size_um, image_width_um, image_height_um, ocr_result, number_region)

    def extract_channels(self):
        """Extracts R, G, B channels and saves them as separate files."""
        if self.merged_image is None:
            print("No image loaded.")
            return

        R_channel, G_channel, B_channel = (self.merged_image[:, :, 0],
                                           self.merged_image[:, :, 1],
                                           self.merged_image[:, :, 2])
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.dirname(self.file_path)
        self.r_path = os.path.join(output_dir, f'R_channel_{now}.tif')
        self.g_path = os.path.join(output_dir, f'G_channel_{now}.tif')
        self.b_path = os.path.join(output_dir, f'B_channel_{now}.tif')

        io.imsave(self.r_path, R_channel)
        io.imsave(self.g_path, G_channel)
        io.imsave(self.b_path, B_channel)
        print(f"Channels saved: {self.r_path}, {self.g_path}, {self.b_path}")

    def find_largest_cell(self):
        """Finds and saves the largest cell region as a binary image."""
        if self.merged_image is None:
            print("No image loaded.")
            return

        gray_image = color.rgb2gray(self.merged_image)
        threshold_value = 0.08
        binary = gray_image > threshold_value
        labels = measure.label(binary)
        regions = measure.regionprops(labels)
        if regions:
            largest_region = max(regions, key=lambda r: r.area)
            self.largest_cell_mask = labels == largest_region.label
            filled_largest_cell_binary = binary_fill_holes(self.largest_cell_mask)
            now = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.binary_image_path = os.path.join(os.path.dirname(self.file_path), f'Largest_Cell_Binary_{now}.tif')
            io.imsave(self.binary_image_path, filled_largest_cell_binary.astype(np.uint8) * 255)
            print(f"Largest cell binary image saved: {self.binary_image_path}")

    def calculate_mfi(self):
        """Calculates Mean Fluorescence Intensity (MFI) for the largest cell."""
        if self.merged_image is None or self.largest_cell_mask is None:
            print("No image or cell mask available.")
            return

        def calculate_mfi_for_largest_cell(merged_image, largest_cell_mask):
            R_channel, G_channel, B_channel = merged_image[:, :, 0], merged_image[:, :, 1], merged_image[:, :, 2]
            R_mfi = np.mean(R_channel[largest_cell_mask])
            G_mfi = np.mean(G_channel[largest_cell_mask])
            B_mfi = np.mean(B_channel[largest_cell_mask])
            return R_mfi, G_mfi, B_mfi

        self.mfi_results = calculate_mfi_for_largest_cell(self.merged_image, self.largest_cell_mask)
        print(f"MFI - R: {self.mfi_results[0]:.2f}, G: {self.mfi_results[1]:.2f}, B: {self.mfi_results[2]:.2f}")

    def create_report(self):
        if self.merged_image is None or self.largest_cell_mask is None or not hasattr(self, 'mfi_results'):
            print("No data available to create a report.")
            return

        output_dir = os.path.dirname(self.file_path)
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(output_dir, f'Cell_Analysis_Report_{now}.xlsx')

        largest_cell_area_pixels = np.sum(self.largest_cell_mask)

        # Example usage

        image_height_pixels, image_width_pixels, scale_bar_length_um, scale_bar_length_pixels, pixel_size_um, image_width_um, image_height_um, ocr_result, number_region = self.detect_scale_bar_and_calculate_size()
        total_area_pixel = image_height_pixels * image_width_pixels
        total_area_um = image_width_um * image_height_um
        cell_area_percent = largest_cell_area_pixels / total_area_pixel
        cell_Area_um = total_area_um * cell_area_percent

        print(f"Image Size (Pixels): {image_width_pixels} x {image_height_pixels} (width x height)")
        print(f"Image Size (Micrometers): {image_width_um:.2f} µm x {image_height_um:.2f} µm (width x height)")

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
            'scale_bar_length_pixels': [scale_bar_length_pixels],
            'scale_bar_length_um': [scale_bar_length_um],
            'pixel_size_um': [pixel_size_um],
            'MFI R': [self.mfi_results[0]],
            'MFI G': [self.mfi_results[1]],
            'MFI B': [self.mfi_results[2]]
        }
        df = pd.DataFrame(data)

        wb = Workbook()
        ws = wb.active
        ws.title = "Cell Analysis Report"

        for r in dataframe_to_rows(df, index=False, header=True):
            ws.append(r)

        # Function to resize images
        def resize_image(image_path, scale=0.5):
            img = Image.open(image_path)
            img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
            resized_path = image_path.replace(".tif", "_resized.tif")
            img.save(resized_path)
            return resized_path

        # Rescale images to 50%
        img_merged_resized = resize_image(self.file_path)
        img_binary_resized = resize_image(self.binary_image_path)
        img_r_channel_resized = resize_image(self.r_path)
        img_g_channel_resized = resize_image(self.g_path)
        img_b_channel_resized = resize_image(self.b_path)

        img_merged = OpenpyxlImage(img_merged_resized)
        img_binary = OpenpyxlImage(img_binary_resized)
        img_r_channel = OpenpyxlImage(img_r_channel_resized)
        img_g_channel = OpenpyxlImage(img_g_channel_resized)
        img_b_channel = OpenpyxlImage(img_b_channel_resized)

        # Add images to the worksheet, placing them side by side
        ws.add_image(img_merged, 'A5')
        ws.add_image(img_binary, 'I5')  # Place binary image next to merged

        ws.add_image(img_r_channel, 'A35')
        ws.add_image(img_g_channel, 'I35')
        ws.add_image(img_b_channel, 'Q35')  # Place RGB channels side by side

        wb.save(report_path)
        print(f"Report saved: {report_path}")
        return report_path
