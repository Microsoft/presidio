import json
import os
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pydicom
from matplotlib import pyplot as plt  # necessary import for PIL typing # noqa: F401
from PIL import Image, ImageOps
from presidio_analyzer import PatternRecognizer
from pydicom.multival import MultiValue
from pydicom.pixel_data_handlers.util import apply_voi_lut

from presidio_image_redactor import (
    ImageAnalyzerEngine,  # noqa: F401
    ImageRedactorEngine,
)
from presidio_image_redactor.entities import ImageRecognizerResult


class DicomImageRedactorEngine(ImageRedactorEngine):
    """Performs OCR + PII detection + bounding box redaction."""

    def redact_and_return_bbox(
        self,
        image: pydicom.dataset.FileDataset,
        fill: str = "contrast",
        padding_width: int = 25,
        crop_ratio: float = 0.75,
        use_metadata: bool = True,
        ocr_kwargs: Optional[dict] = None,
        ad_hoc_recognizers: Optional[List[PatternRecognizer]] = None,
        **text_analyzer_kwargs,
    ) -> Tuple[pydicom.dataset.FileDataset, List[Dict[str, int]]]:
        """Redact method to redact the given DICOM image and return redacted bboxes.

        Please note, this method duplicates the image, creates a
        new instance and manipulates it.

        :param image: Loaded DICOM instance including pixel data and metadata.
        :param fill: Fill setting to use for redaction box ("contrast" or "background").
        :param padding_width: Padding width to use when running OCR.
        :param crop_ratio: Portion of image to consider when selecting
        most common pixel value as the background color value.
        :param use_metadata: Whether to redact text in the image that
        are present in the metadata.
        :param ocr_kwargs: Additional params for OCR methods.
        :param ad_hoc_recognizers: List of PatternRecognizer objects to use
        for ad-hoc recognizer.
        :param text_analyzer_kwargs: Additional values for the analyze method
        in AnalyzerEngine.

        :return: DICOM instance with redacted pixel data.
        """
        # Check input
        if type(image) not in [pydicom.dataset.FileDataset, pydicom.dataset.Dataset]:
            raise TypeError("The provided image must be a loaded DICOM instance.")
        try:
            image.PixelData
        except AttributeError as e:
            raise AttributeError(f"Provided DICOM instance lacks pixel data: {e}")
        except PermissionError as e:
            raise PermissionError(f"Unable to access pixel data (may not exist): {e}")
        except IsADirectoryError as e:
            raise IsADirectoryError(f"DICOM instance is a directory: {e}")

        instance = deepcopy(image)

        is_greyscale = self._check_if_greyscale(instance)
        image_np = self._rescale_dcm_pixel_array(instance, is_greyscale)
        if is_greyscale:
            # model L for grayscale, and has 8 bit-pixel to store the pixel value
            image_pil = Image.fromarray(image_np, mode="L")
        else:
            # model RGB, has 3x8 bit pixel available to store the value
            image_pil = Image.fromarray(image_np, mode="RGB")
        padded_image_pil = self._add_padding(image_pil, is_greyscale, padding_width)

        # Detect PII
        analyzer_results = self._get_analyzer_results(
            padded_image_pil,
            instance,
            use_metadata,
            ocr_kwargs,
            ad_hoc_recognizers,
            **text_analyzer_kwargs,
        )

        # Redact all bounding boxes from DICOM file
        analyzer_bboxes = self.bbox_processor.get_bboxes_from_analyzer_results(
            analyzer_results
        )
        bboxes = self.bbox_processor.remove_bbox_padding(analyzer_bboxes, padding_width)
        redacted_image = self._add_redact_box(instance, bboxes, crop_ratio, fill)

        return redacted_image, bboxes

    def redact(
        self,
        image: pydicom.dataset.FileDataset,
        fill: str = "contrast",
        padding_width: int = 25,
        crop_ratio: float = 0.75,
        ocr_kwargs: Optional[dict] = None,
        ad_hoc_recognizers: Optional[List[PatternRecognizer]] = None,
        **text_analyzer_kwargs,
    ) -> pydicom.dataset.FileDataset:
        """Redact method to redact the given DICOM image.

        Please note, this method duplicates the image, creates a
        new instance and manipulates it.

        :param image: Loaded DICOM instance including pixel data and metadata.
        :param fill: Fill setting to use for redaction box ("contrast" or "background").
        :param padding_width: Padding width to use when running OCR.
        :param crop_ratio: Portion of image to consider when selecting
        most common pixel value as the background color value.
        :param ocr_kwargs: Additional params for OCR methods.
        :param ad_hoc_recognizers: List of PatternRecognizer objects to use
        for ad-hoc recognizer.
        :param text_analyzer_kwargs: Additional values for the analyze method
        in AnalyzerEngine.

        :return: DICOM instance with redacted pixel data.
        """
        redacted_image, _ = self.redact_and_return_bbox(
            image=image,
            fill=fill,
            padding_width=padding_width,
            crop_ratio=crop_ratio,
            ocr_kwargs=ocr_kwargs,
            ad_hoc_recognizers=ad_hoc_recognizers,
            **text_analyzer_kwargs,
        )

        return redacted_image

    def redact_from_file(
        self,
        input_dicom_path: str,
        output_dir: str,
        padding_width: int = 25,
        crop_ratio: float = 0.75,
        fill: str = "contrast",
        use_metadata: bool = True,
        save_bboxes: bool = False,
        verbose: bool = True,
        ocr_kwargs: Optional[dict] = None,
        ad_hoc_recognizers: Optional[List[PatternRecognizer]] = None,
        **text_analyzer_kwargs,
    ) -> None:
        """Redact method to redact from a given file.

        :param input_dicom_path: String path to DICOM image.
        :param output_dir: String path to parent output directory.
        :param padding_width: Padding width to use when running OCR.
        :param crop_ratio: Portion of image to consider when selecting
        most common pixel value as the background color value.
        :param fill: Color setting to use for redaction box
        ("contrast" or "background").
        :param use_metadata: Whether to redact text in the image that
        are present in the metadata.
        :param save_bboxes: True if we want to save boundings boxes.
        :param verbose: True to print where redacted file was written to.
        :param ocr_kwargs: Additional params for OCR methods.
        :param ad_hoc_recognizers: List of PatternRecognizer objects to use
        for ad-hoc recognizer.
        :param text_analyzer_kwargs: Additional values for the analyze method
        in AnalyzerEngine.

        Please notice, this method duplicates the file, creates
        new instance and manipulate them.

        """
        # Verify the given paths
        if Path(input_dicom_path).is_dir() is True:
            raise TypeError("input_dicom_path must be file (not dir)")
        if Path(input_dicom_path).is_file() is False:
            raise TypeError("input_dicom_path must be a valid file")
        if Path(output_dir).is_file() is True:
            raise TypeError(
                "output_dir must be a directory (does not need to exist yet)"
            )

        # Create duplicate
        dst_path = self._copy_files_for_processing(input_dicom_path, output_dir)

        # Process DICOM file
        output_location = self._redact_single_dicom_image(
            dcm_path=dst_path,
            crop_ratio=crop_ratio,
            fill=fill,
            padding_width=padding_width,
            use_metadata=use_metadata,
            overwrite=True,
            dst_parent_dir=".",
            save_bboxes=save_bboxes,
            ocr_kwargs=ocr_kwargs,
            ad_hoc_recognizers=ad_hoc_recognizers,
            **text_analyzer_kwargs,
        )

        if verbose:
            print(f"Output written to {output_location}")

        return None

    def redact_from_directory(
        self,
        input_dicom_path: str,
        output_dir: str,
        padding_width: int = 25,
        crop_ratio: float = 0.75,
        fill: str = "contrast",
        use_metadata: bool = True,
        save_bboxes: bool = False,
        ocr_kwargs: Optional[dict] = None,
        ad_hoc_recognizers: Optional[List[PatternRecognizer]] = None,
        **text_analyzer_kwargs,
    ) -> None:
        """Redact method to redact from a directory of files.

        :param input_dicom_path: String path to directory of DICOM images.
        :param output_dir: String path to parent output directory.
        :param padding_width: Padding width to use when running OCR.
        :param crop_ratio: Portion of image to consider when selecting
        most common pixel value as the background color value.
        :param fill: Color setting to use for redaction box
        ("contrast" or "background").
        :param use_metadata: Whether to redact text in the image that
        are present in the metadata.
        :param save_bboxes: True if we want to save bounding boxes.
        :param ocr_kwargs: Additional params for OCR methods.
        :param ad_hoc_recognizers: List of PatternRecognizer objects to use
        for ad-hoc recognizer.
        :param text_analyzer_kwargs: Additional values for the analyze method
        in AnalyzerEngine.

        Please notice, this method duplicates the files, creates
        new instances and manipulate them.

        """
        # Verify the given paths
        if Path(input_dicom_path).is_dir() is False:
            raise TypeError("input_dicom_path must be a valid directory")
        if Path(input_dicom_path).is_file() is True:
            raise TypeError("input_dicom_path must be a directory (not file)")
        if Path(output_dir).is_file() is True:
            raise TypeError(
                "output_dir must be a directory (does not need to exist yet)"
            )

        # Create duplicates
        dst_path = self._copy_files_for_processing(input_dicom_path, output_dir)

        # Process DICOM files
        output_location = self._redact_multiple_dicom_images(
            dcm_dir=dst_path,
            crop_ratio=crop_ratio,
            fill=fill,
            padding_width=padding_width,
            use_metadata=use_metadata,
            ad_hoc_recognizers=ad_hoc_recognizers,
            overwrite=True,
            dst_parent_dir=".",
            save_bboxes=save_bboxes,
            ocr_kwargs=ocr_kwargs,
            **text_analyzer_kwargs,
        )

        print(f"Output written to {output_location}")

        return None

    @staticmethod
    def _get_all_dcm_files(dcm_dir: Path) -> List[Path]:
        """Return paths to all DICOM files in a directory and its sub-directories.

        :param dcm_dir: pathlib Path to a directory containing at least one .dcm file.

        :return: List of pathlib Path objects.
        """
        # Define applicable extensions
        extensions = ["[dD][cC][mM]", "[dD][iI][cC][oO][mM]"]

        # Get all files with any applicable extension
        all_files = []
        for extension in extensions:
            p = dcm_dir.glob(f"**/*.{extension}")
            files = [x for x in p if x.is_file()]
            all_files += files

        return all_files

    @staticmethod
    def _check_if_greyscale(instance: pydicom.dataset.FileDataset) -> bool:
        """Check if a DICOM image is in greyscale.

        :param instance: A single DICOM instance.

        :return: FALSE if the Photometric Interpretation is RGB.
        """
        # Check if image is grayscale using the Photometric Interpretation element
        try:
            color_scale = instance.PhotometricInterpretation
        except AttributeError:
            color_scale = None
        is_greyscale = color_scale in ["MONOCHROME1", "MONOCHROME2"]

        return is_greyscale

    @staticmethod
    def _rescale_dcm_pixel_array(
        instance: pydicom.dataset.FileDataset, is_greyscale: bool
    ) -> np.ndarray:
        """Rescale DICOM pixel_array.

        :param instance: A singe DICOM instance.
        :param is_greyscale: FALSE if the Photometric Interpretation is RGB.

        :return: Rescaled DICOM pixel_array.
        """
        # Normalize contrast
        if "WindowWidth" in instance:
            if is_greyscale:
                image_2d = apply_voi_lut(instance.pixel_array, instance)
            else:
                image_2d = instance.pixel_array
        else:
            image_2d = instance.pixel_array

        # Convert to float to avoid overflow or underflow losses.
        image_2d_float = image_2d.astype(float)

        if not is_greyscale:
            image_2d_scaled = image_2d_float
        else:
            # Rescaling grey scale between 0-255
            image_2d_scaled = (
                (image_2d_float.max() - image_2d_float)
                / (image_2d_float.max() - image_2d_float.min())
            ) * 255.0

        # Convert to uint
        image_2d_scaled = np.uint8(image_2d_scaled)

        return image_2d_scaled

    @staticmethod
    def _get_bg_color(
        image: Image.Image, is_greyscale: bool, invert: bool = False
    ) -> Union[int, Tuple[int, int, int]]:
        """Select most common color as background color.

        :param image: Loaded PIL image.
        :param colorscale: Colorscale of image (e.g., 'grayscale', 'RGB')
        :param invert: TRUE if you want to get the inverse of the bg color.

        :return: Background color.
        """
        # Invert colors if invert flag is True
        if invert:
            if image.mode == "RGBA":
                # Handle transparency as needed
                r, g, b, a = image.split()
                rgb_image = Image.merge("RGB", (r, g, b))
                inverted_image = ImageOps.invert(rgb_image)
                r2, g2, b2 = inverted_image.split()

                image = Image.merge("RGBA", (r2, g2, b2, a))

            else:
                image = ImageOps.invert(image)

        # Get background color
        if is_greyscale:
            # Select most common color as color
            bg_color = int(np.bincount(list(image.getdata())).argmax())
        else:
            # Reduce size of image to 1 pixel to get dominant color
            tmp_image = image.copy()
            tmp_image = tmp_image.resize((1, 1), resample=0)
            bg_color = tmp_image.getpixel((0, 0))

        return bg_color

    @staticmethod
    def _get_array_corners(pixel_array: np.ndarray, crop_ratio: float) -> np.ndarray:
        """Crop a pixel array to just return the corners in a single array.

        :param pixel_array: Numpy array containing the pixel data.
        :param crop_ratio: Portion of image to consider when selecting
        most common pixel value as the background color value.

        :return: Cropped input array.
        """
        if crop_ratio >= 1.0 or crop_ratio <= 0:
            raise ValueError("crop_ratio must be between 0 and 1")

        # Set dimensions
        width = pixel_array.shape[0]
        height = pixel_array.shape[1]
        crop_width = int(np.floor(width * crop_ratio / 2))
        crop_height = int(np.floor(height * crop_ratio / 2))

        # Get coordinates for corners
        # (left, top, right, bottom)
        box_top_left = (0, 0, crop_width, crop_height)
        box_top_right = (width - crop_width, 0, width, crop_height)
        box_bottom_left = (0, height - crop_height, crop_width, height)
        box_bottom_right = (width - crop_width, height - crop_height, width, height)
        boxes = [box_top_left, box_top_right, box_bottom_left, box_bottom_right]

        # Only keep box pixels
        cropped_pixel_arrays = [
            pixel_array[box[0] : box[2], box[1] : box[3]] for box in boxes
        ]

        # Combine the cropped pixel arrays
        cropped_array = np.vstack(cropped_pixel_arrays)

        return cropped_array

    @classmethod
    def _get_most_common_pixel_value(
        cls,
        instance: pydicom.dataset.FileDataset,
        crop_ratio: float,
        fill: str = "contrast",
    ) -> Union[int, Tuple[int, int, int]]:
        """Find the most common pixel value.

        :param instance: A singe DICOM instance.
        :param crop_ratio: Portion of image to consider when selecting
        most common pixel value as the background color value.
        :param fill: Determines how box color is selected.
        'contrast' - Masks stand out relative to background.
        'background' - Masks are same color as background.

        :return: Most or least common pixel value (depending on fill).
        """
        # Crop down to just only look at image corners
        cropped_array = cls._get_array_corners(instance.pixel_array, crop_ratio)

        # Get flattened pixel array
        flat_pixel_array = np.array(cropped_array).flatten()

        is_greyscale = cls._check_if_greyscale(instance)
        if is_greyscale:
            # Get most common value
            values, counts = np.unique(flat_pixel_array, return_counts=True)
            flat_pixel_array = np.array(flat_pixel_array)
            common_value = values[np.argmax(counts)]
        else:
            raise TypeError(
                "Most common pixel value retrieval is only supported for greyscale images at this point."  # noqa: E501
            )

        # Invert color as necessary
        if fill.lower() in ["contrast", "invert", "inverted", "inverse"]:
            pixel_value = np.max(flat_pixel_array) - common_value
        elif fill.lower() in ["background", "bg"]:
            pixel_value = common_value

        return pixel_value

    @classmethod
    def _add_padding(
        cls,
        image: Image.Image,
        is_greyscale: bool,
        padding_width: int,
    ) -> Image.Image:
        """Add border to image using most common color.

        :param image: Loaded PIL image.
        :param is_greyscale: Whether image is in grayscale or not.
        :param padding_width: Pixel width of padding (uniform).

        :return: PIL image with padding.
        """
        # Check padding width value
        if padding_width <= 0:
            raise ValueError("Enter a positive value for padding")
        elif padding_width >= 100:
            raise ValueError(
                "Excessive padding width entered. Please use a width under 100 pixels."
            )

        # Select most common color as border color
        border_color = cls._get_bg_color(image, is_greyscale)

        # Add padding
        right = padding_width
        left = padding_width
        top = padding_width
        bottom = padding_width

        width, height = image.size

        new_width = width + right + left
        new_height = height + top + bottom

        image_with_padding = Image.new(
            image.mode, (new_width, new_height), border_color
        )
        image_with_padding.paste(image, (left, top))

        return image_with_padding

    @staticmethod
    def _copy_files_for_processing(src_path: str, dst_parent_dir: str) -> Path:
        """Copy DICOM files. All processing should be done on the copies.

        :param src_path: String path to DICOM file or directory containing DICOM files.
        :param dst_parent_dir: String path to parent directory of output location.

        :return: Output location of the file(s).
        """
        # Identify output path
        tail = list(Path(src_path).parts)[-1]
        dst_path = Path(dst_parent_dir, tail)

        # Copy file(s)
        if Path(src_path).is_dir() is True:
            try:
                shutil.copytree(src_path, dst_path)
            except FileExistsError:
                raise FileExistsError(
                    "Destination files already exist. Please clear the destination files or specify a different dst_parent_dir."  # noqa: E501
                )
        elif Path(src_path).is_file() is True:
            # Create the output dir manually if working with a single file
            os.makedirs(Path(dst_path).parent, exist_ok=True)
            shutil.copyfile(src_path, dst_path)
        else:
            raise FileNotFoundError(f"{src_path} does not exist")

        return dst_path

    @staticmethod
    def _get_text_metadata(
        instance: pydicom.dataset.FileDataset,
    ) -> Tuple[list, list, list]:
        """Retrieve all text metadata from the DICOM image.

        :param instance: Loaded DICOM instance.

        :return: List of all the instance's element values (excluding pixel data),
        bool for if the element is specified as being a name,
        bool for if the element is specified as being related to the patient.
        """
        metadata_text = list()
        is_name = list()
        is_patient = list()

        for element in instance:
            # Save all metadata except the DICOM image itself
            if element.name != "Pixel Data":
                # Save the metadata
                metadata_text.append(element.value)

                # Track whether this particular element is a name
                if "name" in element.name.lower():
                    is_name.append(True)
                else:
                    is_name.append(False)

                # Track whether this particular element is directly tied to the patient
                if "patient" in element.name.lower():
                    is_patient.append(True)
                else:
                    is_patient.append(False)
            else:
                metadata_text.append("")
                is_name.append(False)
                is_patient.append(False)

        return metadata_text, is_name, is_patient

    @staticmethod
    def augment_word(word: str, case_sensitive: bool = False) -> list:
        """Apply multiple types of casing to the provided string.

        :param word: String containing the word or term of interest.
        :param case_sensitive: True if we want to preserve casing.

        :return: List of the same string with different casings and spacing.
        """
        word_list = []
        if word != "":
            # Replacing separator character with space, if any
            text_no_separator = word.replace("^", " ")
            text_no_separator = text_no_separator.replace("-", " ")
            text_no_separator = " ".join(text_no_separator.split())

            if case_sensitive:
                word_list.append(text_no_separator)
                word_list.extend(
                    [
                        text_no_separator.split(" "),
                    ]
                )
            else:
                # Capitalize all characters in string
                text_upper = text_no_separator.upper()

                # Lowercase all characters in string
                text_lower = text_no_separator.lower()

                # Capitalize first letter in each part of string
                text_title = text_no_separator.title()

                # Append iterations
                word_list.extend(
                    [text_no_separator, text_upper, text_lower, text_title]
                )

                # Adding each term as a separate item in the list
                word_list.extend(
                    [
                        text_no_separator.split(" "),
                        text_upper.split(" "),
                        text_lower.split(" "),
                        text_title.split(" "),
                    ]
                )

            # Flatten list
            flat_list = []
            for item in word_list:
                if isinstance(item, list):
                    flat_list.extend(item)
                else:
                    flat_list.append(item)

            # Remove any duplicates and empty strings
            word_list = list(set(flat_list))
            word_list = list(filter(None, word_list))

        return word_list

    @classmethod
    def _process_names(cls, text_metadata: list, is_name: list) -> list:
        """Process names to have multiple iterations in our PHI list.

        :param text_metadata: List of all the instance's element values
        (excluding pixel data).
        :param is_name: True if the element is specified as being a name.

        :return: List of PHI strings for elements where is_name is True,
        with additional name augmentations appended.
        """
        phi_list = []

        for i in range(0, len(text_metadata)):
            if is_name[i] is True:
                value = text_metadata[i]
                # Flatten MultiValue/list/tuple into individual elements
                items = (
                    value if isinstance(value, (MultiValue, list, tuple)) else [value]
                )
                for item in items:
                    text = str(item).strip()
                    if text:
                        phi_list.append(text)
                        phi_list += cls.augment_word(text)

        return phi_list

    @staticmethod
    def _add_known_generic_phi(phi_list: list) -> list:
        """Add known potential generic PHI values.

        :param phi_list: List of PHI to use with Presidio ad-hoc recognizer.

        :return: Same list with added known values.
        """
        known_generic_phi = ["[M]", "[F]", "[X]", "[U]", "M", "F", "X", "U"]
        phi_list.extend(known_generic_phi)

        return phi_list

    @classmethod
    def _make_phi_list(
        cls,
        original_metadata: List[Union[pydicom.multival.MultiValue, list, tuple]],
        is_name: List[bool],
        is_patient: List[bool],
    ) -> list:
        """Build a list of PHI strings for the ad-hoc recognizer.

        Combines names and patient-related fields, adds generic PHI, flattens nested
        collections, stringifies, trims empties, and de-duplicates while preserving
        order of first appearance.

        :param original_metadata: List of all the instance's element values
        (excluding pixel data).
        :param is_name: True if the element is specified as being a name.
        :param is_patient: True if the element is specified as being
        related to the patient.

        :return: List of PHI (str) to use with Presidio ad-hoc recognizer.
        """
        # 1) Base PHI via existing helpers
        phi: list = []
        phi.extend(cls._process_names(original_metadata, is_name))
        phi.extend(cls._process_names(original_metadata, is_patient))
        phi = cls._add_known_generic_phi(phi)

        # 2) Flatten safely (MultiValue/list/tuple) and stringify
        flattened: list = []
        for val in phi:
            if isinstance(val, (MultiValue, list, tuple)):
                for item in val:
                    if item is None:
                        continue
                    s = str(item).strip()
                    if s:
                        flattened.append(s)
            else:
                if val is None:
                    continue
                s = str(val).strip()
                if s:
                    flattened.append(s)

        # 3) Stable de-duplication
        seen = set()
        out: list = []
        for s in flattened:
            if s not in seen:
                seen.add(s)
                out.append(s)
        return out

    @classmethod
    def _set_bbox_color(
        cls, instance: pydicom.dataset.FileDataset, fill: str
    ) -> Union[int, Tuple[int, int, int]]:
        """Set the bounding box color.

        :param instance: A single DICOM instance.
        :param fill: Determines how box color is selected.
        'contrast' - Masks stand out relative to background.
        'background' - Masks are same color as background.

        :return: int or tuple of int values determining masking box color.
        """
        # Check if we want the box color to contrast with the background
        if fill.lower() in ["contrast", "invert", "inverted", "inverse"]:
            invert_flag = True
        elif fill.lower() in ["background", "bg"]:
            invert_flag = False
        else:
            raise ValueError("fill must be 'contrast' or 'background'")

        is_greyscale = cls._check_if_greyscale(instance)
        if is_greyscale:
            # model L for grayscale, and has 8 bit-pixel to store the pixel value
            image_pil = Image.fromarray(instance.pixel_array, mode="L")
        else:
            # model RGB, has 3x8 bit pixel available to store the value
            image_pil = Image.fromarray(instance.pixel_array, mode="RGB")
        box_color = cls._get_bg_color(image_pil, is_greyscale, invert_flag)

        return box_color

    @staticmethod
    def _check_if_compressed(instance: pydicom.dataset.FileDataset) -> bool:
        """Check if the pixel data is compressed.

        :param instance: DICOM instance.

        :return: Boolean for whether the pixel data is compressed.
        """
        # Calculate expected bytes
        rows = instance.Rows
        columns = instance.Columns
        samples_per_pixel = instance.SamplesPerPixel
        bits_allocated = instance.BitsAllocated
        try:
            number_of_frames = instance[0x0028, 0x0008].value
        except KeyError:
            number_of_frames = 1
        expected_num_bytes = (
            rows * columns * number_of_frames * samples_per_pixel * (bits_allocated / 8)
        )

        # Compare expected vs actual
        is_compressed = (int(expected_num_bytes)) > len(instance.PixelData)

        return is_compressed

    @staticmethod
    def _compress_pixel_data(
        instance: pydicom.dataset.FileDataset,
    ) -> pydicom.dataset.FileDataset:
        """Recompress pixel data that was decompressed during redaction.

        :param instance: Loaded DICOM instance.

        :return: Instance with compressed pixel data.
        """
        compression_method = pydicom.uid.RLELossless

        # Temporarily change syntax to an "uncompressed" method
        instance.file_meta.TransferSyntaxUID = pydicom.uid.UID("1.2.840.10008.1.2")

        # Compress and update syntax
        instance.compress(compression_method, encoding_plugin="gdcm")
        instance.file_meta.TransferSyntaxUID = compression_method

        return instance

    @staticmethod
    def _check_if_has_image_icon_sequence(
        instance: pydicom.dataset.FileDataset,
    ) -> bool:
        """Check if there is an image icon sequence tag in the metadata.

        This leads to pixel data being present in multiple locations.

        :param instance: DICOM instance.

        :return: Boolean for whether the instance has an image icon sequence tag.
        """
        has_image_icon_sequence = False
        try:
            _ = instance[0x0088, 0x0200]
            has_image_icon_sequence = True
        except KeyError:
            has_image_icon_sequence = False

        return has_image_icon_sequence

    @classmethod
    def _add_redact_box(
        cls,
        instance: pydicom.dataset.FileDataset,
        bounding_boxes_coordinates: list,
        crop_ratio: float,
        fill: str = "contrast",
    ) -> pydicom.dataset.FileDataset:
        """Add redaction bounding boxes on a DICOM instance.

        :param instance: A single DICOM instance.
        :param bounding_boxes_coordinates: Bounding box coordinates.
        :param crop_ratio: Portion of image to consider when selecting
        most common pixel value as the background color value.
        :param fill: Determines how box color is selected.
        'contrast' - Masks stand out relative to background.
        'background' - Masks are same color as background.

        :return: A new dicom instance with redaction bounding boxes.
        """
        # Copy instance
        redacted_instance = deepcopy(instance)
        is_compressed = cls._check_if_compressed(redacted_instance)
        has_image_icon_sequence = cls._check_if_has_image_icon_sequence(
            redacted_instance
        )

        # Select masking box color
        is_greyscale = cls._check_if_greyscale(instance)
        if is_greyscale:
            box_color = cls._get_most_common_pixel_value(instance, crop_ratio, fill)
        else:
            box_color = cls._set_bbox_color(redacted_instance, fill)

        # Apply mask
        for i in range(0, len(bounding_boxes_coordinates)):
            bbox = bounding_boxes_coordinates[i]
            top = bbox["top"]
            left = bbox["left"]
            width = bbox["width"]
            height = bbox["height"]
            redacted_instance.pixel_array[top : top + height, left : left + width] = (
                box_color
            )

        redacted_instance.PixelData = redacted_instance.pixel_array.tobytes()

        # If original pixel data is compressed, recompress after redaction
        if is_compressed or has_image_icon_sequence:
            # Temporary "fix" to manually set all YBR photometric interp as YBR_FULL
            if "YBR" in redacted_instance.PhotometricInterpretation:
                redacted_instance.PhotometricInterpretation = "YBR_FULL"
            redacted_instance = cls._compress_pixel_data(redacted_instance)

        return redacted_instance

    def _get_analyzer_results(
        self,
        image: Image.Image,
        instance: pydicom.dataset.FileDataset,
        use_metadata: bool,
        ocr_kwargs: Optional[dict],
        ad_hoc_recognizers: Optional[List[PatternRecognizer]],
        **text_analyzer_kwargs,
    ) -> List[ImageRecognizerResult]:
        """Analyze image with selected redaction approach.

        :param image: DICOM pixel data as PIL image.
        :param instance: DICOM instance (with metadata).
        :param use_metadata: Whether to redact text in the image that
        are present in the metadata.
        :param ocr_kwargs: Additional params for OCR methods.
        :param ad_hoc_recognizers: List of PatternRecognizer objects to use
        for ad-hoc recognizer.
        :param text_analyzer_kwargs: Additional values for the analyze method
        in AnalyzerEngine (e.g., allow_list).

        :return: Analyzer results.
        """
        # Check the ad-hoc recognizers list
        self._check_ad_hoc_recognizer_list(ad_hoc_recognizers)

        # Create custom recognizer using DICOM metadata
        if use_metadata:
            original_metadata, is_name, is_patient = self._get_text_metadata(instance)
            phi_list = self._make_phi_list(original_metadata, is_name, is_patient)
            deny_list_recognizer = PatternRecognizer(
                supported_entity="PERSON", deny_list=phi_list
            )

            if ad_hoc_recognizers is None:
                ad_hoc_recognizers = [deny_list_recognizer]
            elif isinstance(ad_hoc_recognizers, list):
                ad_hoc_recognizers.append(deny_list_recognizer)

        # Detect PII
        if ad_hoc_recognizers is None:
            analyzer_results = self.image_analyzer_engine.analyze(
                image,
                ocr_kwargs=ocr_kwargs,
                **text_analyzer_kwargs,
            )
        else:
            analyzer_results = self.image_analyzer_engine.analyze(
                image,
                ocr_kwargs=ocr_kwargs,
                ad_hoc_recognizers=ad_hoc_recognizers,
                **text_analyzer_kwargs,
            )

        return analyzer_results

    @staticmethod
    def _save_bbox_json(output_dcm_path: str, bboxes: List[Dict[str, int]]) -> None:
        """Save the redacted bounding box info as a json file.

        :param output_dcm_path: Path to the redacted DICOM file.

        :param bboxes: Bounding boxes used in redaction.
        """
        output_json_path = Path(output_dcm_path).with_suffix(".json")

        with open(output_json_path, "w") as write_file:
            json.dump(bboxes, write_file, indent=4)

    def _redact_single_dicom_image(
        self,
        dcm_path: str,
        crop_ratio: float,
        fill: str,
        padding_width: int,
        use_metadata: bool,
        overwrite: bool,
        dst_parent_dir: str,
        save_bboxes: bool,
        ocr_kwargs: Optional[dict] = None,
        ad_hoc_recognizers: Optional[List[PatternRecognizer]] = None,
        **text_analyzer_kwargs,
    ) -> str:
        """Redact text PHI present on a DICOM image.

        :param dcm_path: String path to the DICOM file.
        :param crop_ratio: Portion of image to consider when selecting
        most common pixel value as the background color value.
        :param fill: Color setting to use for bounding boxes
        ("contrast" or "background").
        :param padding_width: Pixel width of padding (uniform).
        :param use_metadata: Whether to redact text in the image that
        are present in the metadata.
        :param overwrite: Only set to True if you are providing the
        duplicated DICOM path in dcm_path.
        :param dst_parent_dir: String path to parent directory of where to store copies.
        :param save_bboxes: True if we want to save boundings boxes.
        :param ocr_kwargs: Additional params for OCR methods.
        :param ad_hoc_recognizers: List of PatternRecognizer objects to use
        for ad-hoc recognizer.
        :param text_analyzer_kwargs: Additional values for the analyze method
        in AnalyzerEngine.

        :return: Path to the output DICOM file.
        """
        # Ensure we are working on a single file
        if Path(dcm_path).is_dir():
            raise FileNotFoundError("Please ensure dcm_path is a single file")
        elif Path(dcm_path).is_file() is False:
            raise FileNotFoundError(f"{dcm_path} does not exist")

        # Copy file before processing if overwrite==False
        if overwrite is False:
            dst_path = self._copy_files_for_processing(dcm_path, dst_parent_dir)
        else:
            dst_path = dcm_path

        # Load instance
        instance = pydicom.dcmread(dst_path)

        try:
            instance.PixelData
        except AttributeError:
            raise AttributeError("Provided DICOM file lacks pixel data.")

        is_greyscale = self._check_if_greyscale(instance)
        image = self._rescale_dcm_pixel_array(instance, is_greyscale)
        if is_greyscale:
            # model L for grayscale, and has 8 bit-pixel to store the pixel value
            loaded_image = Image.fromarray(image, mode="L")
        else:
            loaded_image = Image.fromarray(image, mode="RGB")
        image = self._add_padding(loaded_image, is_greyscale, padding_width)

        # Detect PII
        analyzer_results = self._get_analyzer_results(
            image,
            instance,
            use_metadata,
            ocr_kwargs,
            ad_hoc_recognizers,
            **text_analyzer_kwargs,
        )

        # Redact all bounding boxes from DICOM file
        analyzer_bboxes = self.bbox_processor.get_bboxes_from_analyzer_results(
            analyzer_results
        )
        bboxes = self.bbox_processor.remove_bbox_padding(analyzer_bboxes, padding_width)
        redacted_dicom_instance = self._add_redact_box(
            instance, bboxes, crop_ratio, fill
        )
        redacted_dicom_instance.save_as(dst_path)

        # Save redacted bboxes
        if save_bboxes:
            self._save_bbox_json(dst_path, bboxes)

        return dst_path

    def _redact_multiple_dicom_images(
        self,
        dcm_dir: str,
        crop_ratio: float,
        fill: str,
        padding_width: int,
        use_metadata: bool,
        overwrite: bool,
        dst_parent_dir: str,
        save_bboxes: bool,
        ocr_kwargs: Optional[dict] = None,
        ad_hoc_recognizers: Optional[List[PatternRecognizer]] = None,
        **text_analyzer_kwargs,
    ) -> str:
        """Redact text PHI present on all DICOM images in a directory.

        :param dcm_dir: String path to directory containing DICOM files (can be nested).
        :param crop_ratio: Portion of image to consider when selecting
        most common pixel value as the background color value.
        :param fill: Color setting to use for bounding boxes
        ("contrast" or "background").
        :param padding_width: Pixel width of padding (uniform).
        :param use_metadata: Whether to redact text in the image that
        are present in the metadata.
        :param overwrite: Only set to True if you are providing
        the duplicated DICOM dir in dcm_dir.
        :param dst_parent_dir: String path to parent directory of where to store copies.
        :param save_bboxes: True if we want to save boundings boxes.
        :param ocr_kwargs: Additional params for OCR methods.
        :param ad_hoc_recognizers: List of PatternRecognizer objects to use
        for ad-hoc recognizer.
        :param text_analyzer_kwargs: Additional values for the analyze method
        in AnalyzerEngine.

        Return:
            dst_dir (str): Path to the output DICOM directory.
        """
        # Ensure we are working on a directory (can have sub-directories)
        if Path(dcm_dir).is_file():
            raise FileNotFoundError("Please ensure dcm_path is a directory")
        elif Path(dcm_dir).is_dir() is False:
            raise FileNotFoundError(f"{dcm_dir} does not exist")

        # List of files to process directly
        if overwrite is False:
            dst_dir = self._copy_files_for_processing(dcm_dir, dst_parent_dir)
        else:
            dst_dir = dcm_dir

        # Process each DICOM file directly
        all_dcm_files = self._get_all_dcm_files(Path(dst_dir))
        for dst_path in all_dcm_files:
            self._redact_single_dicom_image(
                dst_path,
                crop_ratio,
                fill,
                padding_width,
                use_metadata,
                overwrite,
                dst_parent_dir,
                save_bboxes,
                ocr_kwargs=ocr_kwargs,
                ad_hoc_recognizers=ad_hoc_recognizers,
                **text_analyzer_kwargs,
            )

        return dst_dir
