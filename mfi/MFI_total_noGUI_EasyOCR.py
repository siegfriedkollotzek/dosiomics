from datetime import timedelta
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from uuid import UUID

import cv2
import easyocr
import numpy as np
import pandas as pd
import tifffile
from PIL import Image
from django.core.files.base import ContentFile
from django.utils.timezone import now
from openpyxl import Workbook
from openpyxl.drawing.image import Image as OpenpyxlImage
from openpyxl.utils.dataframe import dataframe_to_rows
from scipy import ndimage
from scipy.ndimage import binary_fill_holes
from skimage import io, measure, color

from mfi.models import Mfi


class CellAnalyzer(Thread):
    def __init__(self, uuid: UUID):
        super().__init__()
        self._tempdir = TemporaryDirectory()
        self.tempdir_path = Path(self._tempdir.name)
        self.merged_image = None
        self.largest_cell_mask = None
        self.mfi_results = None
        self.r_path: Path = self.tempdir_path / 'R_channel.tif'
        self.g_path: Path = self.tempdir_path / 'G_channel.tif'
        self.b_path: Path = self.tempdir_path / 'B_channel.tif'
        self.binary_image = self.tempdir_path / f'Largest_Cell_Binary.tif'
        self.mfi = Mfi.objects.get(uuid=uuid)
        self.logs = ""
        self.log(
            "######################################################################\n"
            "-----------------------------Start------------------------------------\n"
            "######################################################################\n")

    def run(self):
        try:
            self.load_image()
            self.detect_scale_bar_and_calculate_size()
            self.extract_channels()
            self.find_largest_cell()
            self.calculate_mfi()
            self.create_report()
            self.mfi.status = 'finished'
            self.mfi.save()
        except Exception as e:
            print(e)
            self.mfi.status = 'error'
            self.mfi.save()
            raise e

        cleanup()

    def log(self, t: str):
        self.logs += t + "\n"
        self.mfi.log = self.logs
        self.mfi.save()

    def load_image(self):
        """Loads the image from the specified file path."""
        self.log(
            "######################################################################\n"
            "-------------------------------1--------------------------------------\n"
            "######################################################################\n")
        self.merged_image = np.array(Image.open(self.mfi.file))
        print(f"Loaded image from {self.mfi.file}")

    def detect_scale_bar_and_calculate_size(self):
        """Detects scale bar and calculates pixel size in micrometers using EasyOCR."""
        self.log("######################################################################\n"
                 "-------------------------------2--------------------------------------\n"
                 "######################################################################\n")
        reader = easyocr.Reader(
            ['en'],
            gpu=False,
            model_storage_directory='mfi/easyocr_models',
            download_enabled=False  # ganz wichtig: keine Downloads zulassen!
        )
        default_scale_bar_length_um = 20
        image = tifffile.imread(self.mfi.file.path)

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
        self.log("######################################################################\n"
                 "-------------------------------3--------------------------------------\n"
                 "######################################################################\n")
        if self.merged_image is None:
            print("No image loaded.")
            return

        r_channel, g_channel, b_channel = (self.merged_image[:, :, 0],
                                           self.merged_image[:, :, 1],
                                           self.merged_image[:, :, 2])

        io.imsave(self.tempdir_path / 'R_channel.tif', r_channel)
        io.imsave(self.tempdir_path / 'G_channel.tif', g_channel)
        io.imsave(self.tempdir_path / 'B_channel.tif', b_channel)
        print(777, self.tempdir_path.glob('*'))
        print(f"Channels saved: {self.r_path}, {self.g_path}, {self.b_path}")

    def find_largest_cell(self):
        """Finds and saves the largest cell region as a binary image."""
        self.log("######################################################################\n"
                 "-------------------------------4--------------------------------------\n"
                 "######################################################################\n")
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
            io.imsave(self.binary_image, filled_largest_cell_binary.astype(np.uint8) * 255)
            print(f"Largest cell binary image saved: {self.binary_image}")

    def calculate_mfi(self):
        """Calculates Mean Fluorescence Intensity (MFI) for the largest cell."""
        self.log("######################################################################\n"
                 "-------------------------------5--------------------------------------\n"
                 "######################################################################\n")
        if self.merged_image is None or self.largest_cell_mask is None:
            print("No image or cell mask available.")
            return

        def calculate_mfi_for_largest_cell(merged_image, largest_cell_mask):
            r_channel, g_channel, b_channel = merged_image[:, :, 0], merged_image[:, :, 1], merged_image[:, :, 2]
            r_mfi = np.mean(r_channel[largest_cell_mask])
            g_mfi = np.mean(g_channel[largest_cell_mask])
            b_mfi = np.mean(b_channel[largest_cell_mask])
            return r_mfi, g_mfi, b_mfi

        self.mfi_results = calculate_mfi_for_largest_cell(self.merged_image, self.largest_cell_mask)
        print(f"MFI - R: {self.mfi_results[0]:.2f}, G: {self.mfi_results[1]:.2f}, B: {self.mfi_results[2]:.2f}")

    def create_report(self):
        self.log("######################################################################\n"
                 "-------------------------------6--------------------------------------\n"
                 "######################################################################\n")
        if self.merged_image is None or self.largest_cell_mask is None or not hasattr(self, 'mfi_results'):
            print("No data available to create a report.")
            return

        largest_cell_area_pixels = np.sum(self.largest_cell_mask)

        # Example usage

        image_height_pixels, image_width_pixels, scale_bar_length_um, scale_bar_length_pixels, pixel_size_um, image_width_um, image_height_um, ocr_result, number_region = self.detect_scale_bar_and_calculate_size()
        total_area_pixel = image_height_pixels * image_width_pixels
        total_area_um = image_width_um * image_height_um
        cell_area_percent = largest_cell_area_pixels / total_area_pixel
        cell_area_um = total_area_um * cell_area_percent

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
            'cell_Area_um': [cell_area_um],
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
        def resize_image(image_path: Path, scale=0.5):
            img = Image.open(image_path)
            img = img.resize((int(img.width * scale), int(img.height * scale)), Image.Resampling.LANCZOS)
            img.save(image_path)

        # Rescale images to 50%
        resize_image(Path(self.mfi.file.path))
        resize_image(self.binary_image)
        resize_image(self.r_path)
        resize_image(self.g_path)
        resize_image(self.b_path)

        img_merged = OpenpyxlImage(self.mfi.file.path)
        img_binary = OpenpyxlImage(self.binary_image)
        img_r_channel = OpenpyxlImage(self.r_path)
        img_g_channel = OpenpyxlImage(self.g_path)
        img_b_channel = OpenpyxlImage(self.b_path)

        # Add images to the worksheet, placing them side by side
        ws.add_image(img_merged, 'A5')
        ws.add_image(img_binary, 'I5')  # Place binary image next to merged

        ws.add_image(img_r_channel, 'A35')
        ws.add_image(img_g_channel, 'I35')
        ws.add_image(img_b_channel, 'Q35')  # Place RGB channels side by side
        buffer = BytesIO()

        wb.save(buffer)
        buffer.seek(0)

        file_content = ContentFile(buffer.read())
        now_str = now().strftime("%Y%m%d_%H%M%S")
        filename = f'Cell_Analysis_Report_{now_str}_{str(self.mfi.uuid)[:6]}.xlsx'
        self.mfi.file_output.save(filename, file_content)
        self.mfi.save()
        self.log(
            "######################################################################\n"
            "-----------------------------End--------------------------------------\n"
            "######################################################################\n")


def cleanup():
    for mfi_object in Mfi.objects.filter(created__lt=(now() - timedelta(days=2))):
        mfi_object.file.delete()
        mfi_object.file_output.delete()
