"""Test suite for dicom_image_redactor_engine.py"""

from pathlib import Path
import tempfile
import os
import json
import numpy as np
from PIL import Image
import pydicom
from presidio_image_redactor.dicom_image_redactor_engine import DicomImageRedactorEngine
from presidio_analyzer import PatternRecognizer
from typing import Union, List, Tuple, Dict, TypeVar, Optional
import pytest

T = TypeVar("T")

SCRIPT_DIR = os.path.dirname(__file__)
TEST_DICOM_PARENT_DIR = f"{SCRIPT_DIR}/test_data"
TEST_DICOM_DIR_1 = f"{SCRIPT_DIR}/test_data/dicom_dir_1"
TEST_DICOM_DIR_2 = f"{SCRIPT_DIR}/test_data/dicom_dir_1/dicom_dir_2"
TEST_DICOM_DIR_3 = f"{SCRIPT_DIR}/test_data/dicom_dir_1/dicom_dir_3"
TEST_NUMPY_DIR = f"{SCRIPT_DIR}/test_data/numpy_arrays"
TEST_PNG_DIR = f"{SCRIPT_DIR}/test_data/png_images"


@pytest.fixture(scope="module")
def mock_engine():
    """Instance of the DicomImageRedactorEngine"""
    # Arrange

    # Act
    dicom_image_redactor_engine = DicomImageRedactorEngine()

    return dicom_image_redactor_engine


# ------------------------------------------------------
# DicomImageRedactorEngine._get_all_dcm_files()
# ------------------------------------------------------
@pytest.mark.parametrize(
    "dcm_dir, expected_list",
    [
        (
            Path(TEST_DICOM_PARENT_DIR),
            [
                Path(TEST_DICOM_PARENT_DIR, "0_ORIGINAL.dcm"),
                Path(TEST_DICOM_PARENT_DIR, "0_ORIGINAL_no_pixels.dcm"),
                Path(TEST_DICOM_PARENT_DIR, "0_ORIGINAL_icon_image_sequence.dcm"),
                Path(TEST_DICOM_PARENT_DIR, "0_ORIGINAL_compressed.dcm"),
                Path(TEST_DICOM_PARENT_DIR, "RGB_ORIGINAL.dcm"),
                Path(TEST_DICOM_DIR_2, "1_ORIGINAL.DCM"),
                Path(TEST_DICOM_DIR_2, "2_ORIGINAL.dicom"),
                Path(TEST_DICOM_DIR_3, "3_ORIGINAL.DICOM"),
            ],
        ),
        (
            Path(TEST_DICOM_DIR_1),
            [
                Path(TEST_DICOM_DIR_2, "1_ORIGINAL.DCM"),
                Path(TEST_DICOM_DIR_2, "2_ORIGINAL.dicom"),
                Path(TEST_DICOM_DIR_3, "3_ORIGINAL.DICOM"),
            ],
        ),
        (
            Path(TEST_DICOM_DIR_2),
            [
                Path(TEST_DICOM_DIR_2, "1_ORIGINAL.DCM"),
                Path(TEST_DICOM_DIR_2, "2_ORIGINAL.dicom"),
            ],
        ),
        (
            Path(TEST_DICOM_DIR_3),
            [
                Path(TEST_DICOM_DIR_3, "3_ORIGINAL.DICOM"),
            ],
        ),
    ],
)
def test_get_all_dcm_files_happy_path(mock_engine: DicomImageRedactorEngine, dcm_dir: Path, expected_list: list):
    """Test happy path for DicomImageRedactorEngine._get_all_dcm_files

    Args:
        dcm_dir (pathlib.Path): Path to a directory containing at least one .dcm file.
        expected_list (list): List of pathlib Path objects.
    """
    # Arrange

    # Act
    test_files = mock_engine._get_all_dcm_files(dcm_dir)
    print("test_files")
    print(test_files)
    print("expected file")
    print(expected_list)

    # Assert
    assert set(test_files) == set(expected_list)


# ------------------------------------------------------
# DicomImageRedactorEngine._check_if_greyscale()
# ------------------------------------------------------
@pytest.mark.parametrize(
    "dcm_file, expected_result",
    [
        (Path(TEST_DICOM_PARENT_DIR, "0_ORIGINAL.dcm"), True),
        (Path(TEST_DICOM_PARENT_DIR, "RGB_ORIGINAL.dcm"), False),
    ],
)
def test_check_if_greyscale_happy_path(mock_engine: DicomImageRedactorEngine, dcm_file: Path, expected_result: bool):
    """Test happy path for DicomImageRedactorEngine._check_if_greyscale

    Args:
        dcm_file (pathlib.Path): Path to a DICOM file.
        expected_result (bool): Expected output of _check_if_greyscale.
    """
    # Arrange
    test_instance = pydicom.dcmread(dcm_file)

    # Act
    test_is_greyscale = mock_engine._check_if_greyscale(test_instance)

    # Assert
    assert test_is_greyscale == expected_result


# ------------------------------------------------------
# DicomImageRedactorEngine._rescale_dcm_pixel_array()
# ------------------------------------------------------
@pytest.mark.parametrize(
    "dcm_file, is_greyscale",
    [
        (Path(TEST_DICOM_PARENT_DIR, "0_ORIGINAL.dcm"), True),
        (Path(TEST_DICOM_PARENT_DIR, "RGB_ORIGINAL.dcm"), False),
        (Path(TEST_DICOM_DIR_2, "1_ORIGINAL.DCM"), True),
        (Path(TEST_DICOM_DIR_2, "2_ORIGINAL.dicom"), True),
        (Path(TEST_DICOM_DIR_3, "3_ORIGINAL.DICOM"), True),
    ],
)
def test_rescale_dcm_pixel_array_happy_path(mock_engine: DicomImageRedactorEngine, dcm_file: Path, is_greyscale: bool):
    """Test happy path for DicomImageRedactorEngine._rescale_dcm_pixel_array

    Args:
        dcm_file (pathlib.Path): Path to a DICOM file.
        is_greyscale (bool): If loaded DICOM image is greyscale or not.
    """
    # Arrange
    test_instance = pydicom.dcmread(dcm_file)
    test_original_image = test_instance.pixel_array

    # Act
    test_scaled_image = mock_engine._rescale_dcm_pixel_array(test_instance, is_greyscale)

    # Assert
    assert np.shape(test_original_image) == np.shape(test_scaled_image)
    assert np.min(test_scaled_image) >= 0
    assert np.max(test_scaled_image) <= 255
    if is_greyscale is True:
        assert np.max(test_original_image) != np.max(test_scaled_image)
        assert len(np.shape(test_scaled_image)) == 2
    else:
        assert len(np.shape(test_scaled_image)) == 3


# ------------------------------------------------------
# testing the conversation of np.array to PIL image
# ------------------------------------------------------
@pytest.mark.parametrize(
    "dcm_file, is_greyscale, rescaled_image_numpy_path",
    [
        (
            Path(TEST_DICOM_PARENT_DIR, "0_ORIGINAL.dcm"),
            True,
            Path(TEST_NUMPY_DIR, "0_ORIGINAL.npy"),
        ),
        (
            Path(TEST_DICOM_PARENT_DIR, "RGB_ORIGINAL.dcm"),
            False,
            Path(TEST_NUMPY_DIR, "RGB_ORIGINAL.npy"),
        ),
        (
            Path(TEST_DICOM_DIR_2, "1_ORIGINAL.DCM"),
            True,
            Path(TEST_NUMPY_DIR, "1_ORIGINAL.npy"),
        ),
        (
            Path(TEST_DICOM_DIR_2, "2_ORIGINAL.dicom"),
            True,
            Path(TEST_NUMPY_DIR, "2_ORIGINAL.npy"),
        ),
        (
            Path(TEST_DICOM_DIR_3, "3_ORIGINAL.DICOM"),
            True,
            Path(TEST_NUMPY_DIR, "3_ORIGINAL.npy"),
        ),
    ],
)
def test_convert_nparray_to_pil_image(
    mock_engine: DicomImageRedactorEngine,
    dcm_file: Path,
    is_greyscale: bool,
    rescaled_image_numpy_path: Path,
):
    """Test happy path for DicomImageRedactorEngine._save_pixel_array_as_png

    Args:
        dcm_file (pathlib.Path): Path to a DICOM file.
        is_greyscale (bool): If loaded DICOM image is greyscale or not.
        rescaled_image_numpy_path (pathlib.Path): Path to file containing numpy array of rescaled image.
    """
    # Arrange
    test_instance = pydicom.dcmread(dcm_file)
    test_image_np = mock_engine._rescale_dcm_pixel_array(test_instance, is_greyscale)

    if is_greyscale:
        # for greyscale, convert np.array to PIL image
        # model L for grayscale, and has 8 bit-pixel to store the pixel value
        image_pil = Image.fromarray(test_image_np, mode="L")
        (np_height, np_width) = np.shape(test_image_np)

    else:
        # model RGB, has 3x8 bit pixel available to store the value
        image_pil = Image.fromarray(test_image_np, mode="RGB")
        (np_height, np_width, np_channel) = np.shape(test_image_np)

    width, height = image_pil.size

    assert height == np_height
    assert width == np_width

    # convert PIL image back to np.arrary
    test_image_np_2 = np.asarray(image_pil)
    assert np.array_equal(test_image_np, test_image_np_2)



# ------------------------------------------------------
# DicomImageRedactorEngine._get_bg_color()
# ------------------------------------------------------
@pytest.mark.parametrize(
    "png_file, is_greyscale, invert_flag, expected_bg_color",
    [
        (Path(TEST_PNG_DIR, "0_ORIGINAL.png"), True, False, 243),
        (Path(TEST_PNG_DIR, "RGB_ORIGINAL.png"), False, False, (0, 0, 0)),
        (Path(TEST_PNG_DIR, "1_ORIGINAL.png"), True, False, 0),
        (Path(TEST_PNG_DIR, "2_ORIGINAL.png"), True, False, 0),
        (Path(TEST_PNG_DIR, "3_ORIGINAL.png"), True, False, 0),
        (Path(TEST_PNG_DIR, "0_ORIGINAL.png"), True, True, 12),
        (Path(TEST_PNG_DIR, "RGB_ORIGINAL.png"), False, True, (255, 255, 255)),
        (Path(TEST_PNG_DIR, "1_ORIGINAL.png"), True, True, 255),
        (Path(TEST_PNG_DIR, "2_ORIGINAL.png"), True, True, 255),
        (Path(TEST_PNG_DIR, "3_ORIGINAL.png"), True, True, 255),
    ],
)
def test_get_bg_color_happy_path(
    mock_engine: DicomImageRedactorEngine,
    png_file: Path,
    is_greyscale: bool,
    invert_flag: bool,
    expected_bg_color: Union[int, Tuple[int, int, int]],
):
    """Test happy path for DicomImageRedactorEngine._get_bg_color

    Args:
        png_file (pathlib.Path): Path to a PNG file.
        is_greyscale (bool): If loaded DICOM image is greyscale or not.
        invert_flag (bool): True if we want to invert image colors to get foreground.
        expected_bg_color (int or Tuple of int): The expected background color of the image.
    """
    # Arrange
    test_image = Image.open(png_file)

    # Act
    test_bg_color = mock_engine._get_bg_color(test_image, is_greyscale, invert_flag)

    # Assert
    assert test_bg_color == expected_bg_color


# ------------------------------------------------------
# DicomImageRedactorEngine._get_array_corners()
# ------------------------------------------------------
@pytest.mark.parametrize(
    "dcm_file, crop_ratio",
    [
        (Path(TEST_DICOM_PARENT_DIR, "0_ORIGINAL.dcm"), 0.5),
        (Path(TEST_DICOM_DIR_2, "1_ORIGINAL.DCM"), 0.5),
        (Path(TEST_DICOM_DIR_2, "2_ORIGINAL.dicom"), 0.5),
        (Path(TEST_DICOM_DIR_3, "3_ORIGINAL.DICOM"), 0.5),
        (Path(TEST_DICOM_PARENT_DIR, "0_ORIGINAL.dcm"), 0.75),
        (Path(TEST_DICOM_DIR_2, "1_ORIGINAL.DCM"), 0.25),
        (Path(TEST_DICOM_DIR_2, "2_ORIGINAL.dicom"), 0.31),
        (Path(TEST_DICOM_DIR_3, "3_ORIGINAL.DICOM"), 0.83),
    ],
)
def test_get_array_corners_happy_path(
    mock_engine: DicomImageRedactorEngine,
    dcm_file: Path,
    crop_ratio: float,
):
    """Test happy path for DicomImageRedactorEngine._get_array_corners

    Args:
        dcm_file (pathlib.Path): Path to a DICOM file.
        crop_ratio (float): Ratio to crop to.
    """
    # Arrange
    test_instance = pydicom.dcmread(dcm_file)
    test_pixel_array = test_instance.pixel_array
    full_width = test_pixel_array.shape[0]
    full_height = test_pixel_array.shape[1]
    full_min_pixel_val = np.min(test_pixel_array)
    full_max_pixel_val = np.max(test_pixel_array)

    # Act
    test_cropped_array = mock_engine._get_array_corners(test_pixel_array, crop_ratio)
    cropped_width = test_cropped_array.shape[0]
    cropped_height = test_cropped_array.shape[1]
    cropped_min_pixel_val = np.min(test_cropped_array)
    cropped_max_pixel_val = np.max(test_cropped_array)

    # Assert
    assert cropped_width * cropped_height < full_width * full_height
    assert cropped_min_pixel_val >= full_min_pixel_val
    assert cropped_max_pixel_val <= full_max_pixel_val


@pytest.mark.parametrize(
    "crop_ratio, expected_error_type",
    [
        (0, "ValueError"),
        (-0.4, "ValueError"),
        (1.3, "ValueError"),
    ],
)
def test_get_array_corners_exceptions(
    mock_engine: DicomImageRedactorEngine, crop_ratio: float, expected_error_type: str
):
    """Test error handling of _get_array_corners

    Args:
        crop_ratio (float): Ratio to crop to.
        expected_error_type (str): Type of error we expect to be raised.
    """
    with pytest.raises(Exception) as exc_info:
        # Arrange
        dcm_file = Path(TEST_DICOM_PARENT_DIR, "RGB_ORIGINAL.dcm")
        test_instance = pydicom.dcmread(dcm_file)
        test_pixel_array = test_instance.pixel_array

        # Act
        _ = mock_engine._get_array_corners(test_pixel_array, crop_ratio)

        # Assert
        assert expected_error_type == exc_info.typename


# ------------------------------------------------------
# DicomImageRedactorEngine._get_most_common_pixel_value()
# ------------------------------------------------------
@pytest.mark.parametrize(
    "dcm_file, fill, expected_color",
    [
        (Path(TEST_DICOM_PARENT_DIR, "0_ORIGINAL.dcm"), "contrast", 50),
        (Path(TEST_DICOM_DIR_2, "1_ORIGINAL.DCM"), "contrast", 16383),
        (Path(TEST_DICOM_DIR_2, "2_ORIGINAL.dicom"), "contrast", 32767),
        (Path(TEST_DICOM_DIR_3, "3_ORIGINAL.DICOM"), "contrast", 4095),
        (Path(TEST_DICOM_PARENT_DIR, "0_ORIGINAL.dcm"), "background", 973),
        (Path(TEST_DICOM_DIR_2, "1_ORIGINAL.DCM"), "background", 0),
        (Path(TEST_DICOM_DIR_2, "2_ORIGINAL.dicom"), "background", 0),
        (Path(TEST_DICOM_DIR_3, "3_ORIGINAL.DICOM"), "background", 0),
    ],
)
def test_get_most_common_pixel_value_happy_path(
    mock_engine: DicomImageRedactorEngine,
    dcm_file: Path,
    fill: str,
    expected_color: Union[int, Tuple[int, int, int]],
):
    """Test happy path for DicomImageRedactorEngine._get_most_common_pixel_value

    Args:
        dcm_file (pathlib.Path): Path to a DICOM file.
        fill (str): Color setting to use ("contrast" or "background").
        expected_color (int or Tuple of int): The expected color returned for the image.
    """
    # Arrange
    crop_ratio = 0.75
    test_instance = pydicom.dcmread(dcm_file)

    # Act
    test_color = mock_engine._get_most_common_pixel_value(test_instance, crop_ratio, fill)

    # Assert
    assert test_color == expected_color


@pytest.mark.parametrize(
    "dcm_file, expected_error_type",
    [
        (Path(TEST_DICOM_PARENT_DIR, "RGB_ORIGINAL.dcm"), "TypeError"),
    ],
)
def test_get_most_common_pixel_value_exceptions(
    mock_engine: DicomImageRedactorEngine, dcm_file: Path, expected_error_type: str
):
    """Test error handling of _get_most_common_pixel_value

    Args:
        dcm_file (pathlib.Path): Path to a DICOM file.
        expected_error_type (str): Type of error we expect to be raised.
    """
    with pytest.raises(Exception) as exc_info:
        # Arrange
        crop_ratio = 0.75
        test_instance = pydicom.dcmread(dcm_file)

        # Act
        _ = mock_engine._get_most_common_pixel_value(test_instance, crop_ratio, "contrast")

        # Assert
        assert expected_error_type == exc_info.typename


# ------------------------------------------------------
# DicomImageRedactorEngine._add_padding()
# ------------------------------------------------------
@pytest.mark.parametrize(
    "png_file, is_greyscale, padding_width",
    [
        (Path(TEST_PNG_DIR, "0_ORIGINAL.png"), True, 15),
        (Path(TEST_PNG_DIR, "RGB_ORIGINAL.png"), False, 15),
        (Path(TEST_PNG_DIR, "1_ORIGINAL.png"), True, 15),
        (Path(TEST_PNG_DIR, "2_ORIGINAL.png"), True, 15),
        (Path(TEST_PNG_DIR, "3_ORIGINAL.png"), True, 15),
        (Path(TEST_PNG_DIR, "0_ORIGINAL.png"), True, 30),
        (Path(TEST_PNG_DIR, "0_ORIGINAL.png"), True, 99),
    ],
)
def test_add_padding_happy_path(
    mock_engine: DicomImageRedactorEngine,
    png_file: Path,
    is_greyscale: bool,
    padding_width: int,
):
    """Test happy path for DicomImageRedactorEngine._add_padding

    Args:
        png_file (pathlib.Path): Path to a PNG file.
        is_greyscale (bool): If loaded DICOM image is greyscale or not.
        padding_width (int): Pixel width of padding (uniform).
    """
    # Arrange
    test_image = Image.open(png_file)

    # Act
    test_image_with_padding = mock_engine._add_padding(test_image, is_greyscale, padding_width)

    # Assert
    assert test_image_with_padding.height - test_image.height == 2 * padding_width
    assert test_image_with_padding.width - test_image.width == 2 * padding_width


@pytest.mark.parametrize(
    "png_file, is_greyscale, padding_width, expected_error_type",
    [
        (Path(TEST_PNG_DIR, "0_ORIGINAL.png"), True, -1, "ValueError"),
        (Path(TEST_PNG_DIR, "0_ORIGINAL.png"), True, 0, "ValueError"),
        (Path(TEST_PNG_DIR, "0_ORIGINAL.png"), True, 200, "ValueError"),
    ],
)
def test_add_padding_exceptions(
    mock_engine: DicomImageRedactorEngine,
    png_file: Path,
    is_greyscale: bool,
    padding_width: int,
    expected_error_type: str,
):
    """Test error handling of _add_padding

    Args:
        png_file (pathlib.Path): Path to a PNG file.
        is_greyscale (bool): If loaded DICOM image is greyscale or not.
        padding_width (int): Pixel width of padding (uniform).
        expected_error_type (str): Type of error we expect to be raised.
    """
    with pytest.raises(Exception) as exc_info:
        # Arrange
        test_image = Image.open(png_file)

        # Act
        _, _ = mock_engine._add_padding(test_image, is_greyscale, padding_width)

    # Assert
    assert expected_error_type == exc_info.typename


# ------------------------------------------------------
# DicomImageRedactorEngine._copy_files_for_processing()
# ------------------------------------------------------
@pytest.mark.parametrize(
    "src_path, expected_num_of_files",
    [
        (Path(TEST_DICOM_PARENT_DIR, "0_ORIGINAL.dcm"), 1),
        (Path(TEST_DICOM_PARENT_DIR), 18),
        (Path(TEST_DICOM_DIR_1), 3),
        (Path(TEST_DICOM_DIR_2), 2),
        (Path(TEST_DICOM_DIR_3), 1),
        (Path(TEST_PNG_DIR), 5),
        (Path(TEST_NUMPY_DIR), 5),
    ],
)
def test_copy_files_for_processing_happy_path(
    mock_engine: DicomImageRedactorEngine, src_path: Path, expected_num_of_files: int
):
    """Test happy path for DicomImageRedactorEngine._copy_files_for_processing

    Args:
        src_path (pathlib.Path): Path to a file or directory to copy.
        expected_num_of_files (int): Expected number of files to be copied.
    """
    # Arrange

    with tempfile.TemporaryDirectory() as tmpdirname:
        # Act
        test_dst_path = mock_engine._copy_files_for_processing(src_path, tmpdirname)

        # Arrange
        p = Path(tmpdirname).glob(f"**/*")
        files = [x for x in p if x.is_file()]

        # Assert
        assert Path(tmpdirname) < test_dst_path
        assert expected_num_of_files == len(files)


# ------------------------------------------------------
# DicomImageRedactorEngine._get_text_metadata()
# ------------------------------------------------------
@pytest.mark.parametrize(
    "dcm_path, metadata_text_len, is_name_true_len, is_patient_true_len",
    [
        (Path(TEST_DICOM_PARENT_DIR, "0_ORIGINAL.dcm"), 82, 4, 6),
        (Path(TEST_DICOM_PARENT_DIR, "RGB_ORIGINAL.dcm"), 93, 9, 10),
        (Path(TEST_DICOM_DIR_2, "1_ORIGINAL.DCM"), 83, 9, 8),
        (Path(TEST_DICOM_DIR_2, "2_ORIGINAL.dicom"), 118, 6, 10),
        (Path(TEST_DICOM_DIR_3, "3_ORIGINAL.DICOM"), 135, 8, 10),
    ],
)
def test_get_text_metadata_happy_path(
    mock_engine: DicomImageRedactorEngine,
    dcm_path: Path,
    metadata_text_len: int,
    is_name_true_len: int,
    is_patient_true_len: int,
):
    """Test happy path for DicomImageRedactorEngine._get_text_metadata

    Args:
        dcm_path (pathlib.Path): Path to DICOM file.
        metadata_text_len (int): Length of the expected returned metadata_text list.
        is_name_true_len (int): Number of true values in the returned is_name list.
        is_patient_true_len (int): Number of true values in the returned is_name list.
    """
    # Arrange
    test_instance = pydicom.dcmread(dcm_path)

    # Act
    test_metadata_text, test_is_name, test_is_patient = mock_engine._get_text_metadata(test_instance)

    # Assert
    idx_is_name = list(np.where(np.array(test_is_name) == True)[0])
    idx_is_patient = list(np.where(np.array(test_is_patient) == True)[0])

    assert len(test_metadata_text) == len(test_is_name) == len(test_is_patient)
    assert len(idx_is_name) == is_name_true_len
    assert len(idx_is_patient) == is_patient_true_len
    assert type(test_metadata_text[idx_is_name[0]]) == str


# ------------------------------------------------------
# DicomImageRedactorEngine.augment_word()
# ------------------------------------------------------
@pytest.mark.parametrize(
    "word, case_sensitive, expected_list",
    [
        ("", False, []),
        (" ", True, []),
        ("JOHN^DOE", False, ["JOHN", "DOE", "John", "Doe", "john", "doe", "JOHN DOE", "John Doe", "john doe"]),
        ("JOHN^DOE", True, ["JOHN", "DOE", "JOHN DOE"]),
        ("JOHN-DOE", False, ["JOHN", "DOE", "John", "Doe", "john", "doe", "JOHN DOE", "John Doe", "john doe"]),
        ("JOHN^-DOE", False, ["JOHN", "DOE", "John", "Doe", "john", "doe", "JOHN DOE", "John Doe", "john doe"]),
        (
            "City Hospital",
            False,
            [
                "City Hospital",
                "CITY HOSPITAL",
                "city hospital",
                "city",
                "hospital",
                "City",
                "Hospital",
                "CITY",
                "HOSPITAL",
            ],
        ),
        ("12345", False, ["12345"]),
    ],
)
def test_augment_word_happy_path(
    mock_engine: DicomImageRedactorEngine,
    word: str,
    case_sensitive: bool,
    expected_list: list,
):
    """Test happy path for DicomImageRedactorEngine.augment_word

    Args:
        word (str): String to augment.
        case_sensitive (bool): True if casing matters.
        expected_list (list): List of expected output.
    """
    # Arrange

    # Act
    test_list = mock_engine.augment_word(word, case_sensitive)

    # Assert
    assert set(test_list) == set(expected_list)


# ------------------------------------------------------
# DicomImageRedactorEngine._process_names()
# ------------------------------------------------------
@pytest.mark.parametrize(
    "text_metadata, is_name, expected_phi_list",
    [
        ([], [], []),
        (
            ["JOHN^DOE", "City Hospital", "12345"],
            [True, False, False],
            [
                "JOHN^DOE",
                "JOHN",
                "DOE",
                "John",
                "Doe",
                "john",
                "doe",
                "JOHN DOE",
                "John Doe",
                "john doe",
            ],
        ),
    ],
)
def test_process_names_happy_path(
    mock_engine: DicomImageRedactorEngine,
    text_metadata: list,
    is_name: list,
    expected_phi_list: list,
):
    """Test happy path for DicomImageRedactorEngine._process_names

    Args:
        text_metadata (list): List of text metadata.
        is_name (list): Whether each element is a name or not.
        expected_phi_list (list): List of expected output.
    """
    # Arrange

    # Act
    test_phi_list = mock_engine._process_names(text_metadata, is_name)

    # Assert
    assert set(test_phi_list) == set(expected_phi_list)


# ------------------------------------------------------
# DicomImageRedactorEngine._add_known_generic_phi()
# ------------------------------------------------------
@pytest.mark.parametrize(
    "phi_list, expected_return_list",
    [
        ([], ["M", "[M]", "F", "[F]", "X", "[X]", "U", "[U]"]),
        (
            ["JOHN^DOE", "City Hospital", "12345"],
            [
                "JOHN^DOE",
                "City Hospital",
                "12345",
                "M",
                "[M]",
                "F",
                "[F]",
                "X",
                "[X]",
                "U",
                "[U]",
            ],
        ),
    ],
)
def test_add_known_generic_phi_happy_path(
    mock_engine: DicomImageRedactorEngine, phi_list: list, expected_return_list: list
):
    """Test happy path for DicomImageRedactorEngine._add_known_generic_phi

    Args:
        phi_list (list): List of PHI.
        expected_return_list (list): List of expected output.
    """
    # Arrange

    # Act
    test_phi_list = mock_engine._add_known_generic_phi(phi_list)

    # Assert
    assert set(test_phi_list) == set(expected_return_list)


# ------------------------------------------------------
# DicomImageRedactorEngine._make_phi_list()
# ------------------------------------------------------
@pytest.mark.parametrize(
    "original_metadata, mock_process_names_val, mock_add_known_val, expected_return_list",
    [
        (
            [
                ["A", "B"],
                "A",
                123,
                "JOHN^DOE",
                "City Hospital",
                "12345",
            ],
            [
                ["A", "B"],
                "A",
                123,
                "JOHN^DOE",
                "City Hospital",
                "12345",
                "JOHN",
                "DOE",
                "John",
                "Doe",
                "john",
                "doe",
                "JOHN DOE",
                "John Doe",
                "john doe",
            ],
            [
                ["A", "B"],
                "A",
                123,
                "JOHN^DOE",
                "City Hospital",
                "12345",
                "JOHN",
                "DOE",
                "John",
                "Doe",
                "john",
                "doe",
                "JOHN DOE",
                "John Doe",
                "john doe",
                "M",
                "[M]",
                "F",
                "[F]",
                "X",
                "[X]",
                "U",
                "[U]",
            ],
            [
                "A",
                "B",
                "123",
                "JOHN^DOE",
                "City Hospital",
                "12345",
                "JOHN",
                "DOE",
                "John",
                "Doe",
                "john",
                "doe",
                "JOHN DOE",
                "John Doe",
                "john doe",
                "M",
                "[M]",
                "F",
                "[F]",
                "X",
                "[X]",
                "U",
                "[U]",
            ],
        ),
    ],
)
def test_make_phi_list_happy_path(
    mocker,
    mock_engine: DicomImageRedactorEngine,
    original_metadata: list,
    mock_process_names_val: list,
    mock_add_known_val: list,
    expected_return_list: list,
):
    """Test happy path for DicomImageRedactorEngine._make_phi_list

    Args:
        original_metadata (list): List extracted metadata (excluding pixel array).
        mock_process_names_val (list): Value to provide to mock process_names.
        mock_add_known_val (list): Value to provide to mock _add_known_generic_phi.
        expected_return_list (list): List of expected output.
    """
    # Arrange
    mock_process_names = mocker.patch(
        "presidio_image_redactor.dicom_image_redactor_engine.DicomImageRedactorEngine._process_names",
        return_value=mock_process_names_val,
    )
    mock_add_known_generic_phi = mocker.patch(
        "presidio_image_redactor.dicom_image_redactor_engine.DicomImageRedactorEngine._add_known_generic_phi",
        return_value=mock_add_known_val,
    )

    # Act
    test_phi_str_list = mock_engine._make_phi_list(original_metadata, [], [])

    # Assert
    # _make_phi_list calls _process_names twice: once for is_name and once for is_patient
    assert mock_process_names.call_count == 2
    assert mock_add_known_generic_phi.call_count == 1
    assert set(test_phi_str_list) == set(expected_return_list)


# ------------------------------------------------------
# DicomImageRedactorEngine._set_bbox_color()
# ------------------------------------------------------
@pytest.mark.parametrize(
    "fill, mock_box_color",
    [
        ("contrast", 0),
        ("contrast", (0, 0, 0)),
        ("background", 255),
        ("background", (255, 255, 255)),
    ],
)
def test_set_bbox_color_happy_path(
    mocker,
    fill: str,
    mock_box_color: Union[int, Tuple[int, int, int]],
):
    """Test happy path for DicomImageRedactorEngine._set_bbox_color

    Args:
        fill (str): Determines how box color is selected.
        mock_box_color (int or Tuple of int): Color value to assign to mocker.
    """
    # Arrange
    test_instance = pydicom.dcmread(Path(TEST_DICOM_PARENT_DIR, "0_ORIGINAL.dcm"))

    mock_Image_fromarray = mocker.patch(
        "presidio_image_redactor.dicom_image_redactor_engine.Image.fromarray",
        return_value=None,
    )
    mock_get_bg_color = mocker.patch.object(
        DicomImageRedactorEngine,
        "_get_bg_color",
        return_value=mock_box_color,
    )
    mock_engine = DicomImageRedactorEngine()

    # Act
    test_box_color = mock_engine._set_bbox_color(test_instance, fill)

    # Assert
    assert mock_Image_fromarray.call_count == 1
    assert mock_get_bg_color.call_count == 1
    assert test_box_color == mock_box_color


@pytest.mark.parametrize(
    "fill, expected_error_type",
    [
        ("typo", "ValueError"),
        ("somecolor", "ValueError"),
        ("0", "ValueError"),
        ("255", "ValueError"),
    ],
)
def test_set_bbox_color_exceptions(
    mock_engine: DicomImageRedactorEngine,
    fill: str,
    expected_error_type: str,
):
    """Test error handling of _set_bbox_color

    Args:
        fill (str): Determines how box color is selected.
        expected_error_type (str): Type of error we expect to be raised.
    """
    with pytest.raises(Exception) as exc_info:
        # Arrange
        test_instance = pydicom.dcmread(Path(TEST_DICOM_PARENT_DIR, "0_ORIGINAL.dcm"))

        # Act
        _ = mock_engine._set_bbox_color(test_instance, fill)

    # Assert
    assert expected_error_type == exc_info.typename


# ------------------------------------------------------
# DicomImageRedactorEngine._check_if_compressed()
# ------------------------------------------------------
@pytest.mark.parametrize(
    "dcm_path, compression_status",
    [
        (Path(TEST_DICOM_PARENT_DIR, "0_ORIGINAL.dcm"), False),
        (Path(TEST_DICOM_PARENT_DIR, "0_ORIGINAL_compressed.dcm"), True),
    ],
)
def test_check_if_compressed_happy_path(
    mock_engine: DicomImageRedactorEngine,
    dcm_path: Path,
    compression_status: bool,
):
    """Test happy path for DicomImageRedactorEngine._check_if_compressed

    Args:
        mock_engine (DicomImageRedactorEngine): DicomImageRedactorEngine object.
        dcm_path (pathlib.Path): Path to DICOM file.
        compression_status (bool): If the pixel data is compressed.
    """
    # Arrange
    test_instance = pydicom.dcmread(dcm_path)

    # Act
    test_is_compressed = mock_engine._check_if_compressed(test_instance)

    # Assert
    assert test_is_compressed == compression_status


# ------------------------------------------------------
# DicomImageRedactorEngine._compress_pixel_data()
# ------------------------------------------------------
@pytest.mark.parametrize(
    "dcm_path",
    [(Path(TEST_DICOM_PARENT_DIR, "0_ORIGINAL.dcm")), (Path(TEST_DICOM_PARENT_DIR, "RGB_ORIGINAL.dcm"))],
)
def test_compress_pixel_data_happy_path(
    mock_engine: DicomImageRedactorEngine,
    dcm_path: Path,
):
    """Test happy path for DicomImageRedactorEngine._compress_pixel_data

    Args:
        mock_engine (DicomImageRedactorEngine): DicomImageRedactorEngine object.
        dcm_path (pathlib.Path): Path to DICOM file.
    """
    # Arrange
    test_instance = pydicom.dcmread(dcm_path)

    # Act
    test_compressed = mock_engine._compress_pixel_data(test_instance)

    # Assert
    assert mock_engine._check_if_compressed(test_compressed) == True


# ------------------------------------------------------
# DicomImageRedactorEngine._check_if_has_image_icon_sequence()
# ------------------------------------------------------
@pytest.mark.parametrize(
    "dcm_path, has_sequence",
    [
        (Path(TEST_DICOM_PARENT_DIR, "0_ORIGINAL.dcm"), False),
        (Path(TEST_DICOM_PARENT_DIR, "0_ORIGINAL_icon_image_sequence.dcm"), True),
    ],
)
def test_check_if_has_image_icon_sequence_happy_path(
    mock_engine: DicomImageRedactorEngine,
    dcm_path: Path,
    has_sequence: bool,
):
    """Test happy path for DicomImageRedactorEngine._check_if_has_image_icon_sequence
    Args:
        mock_engine (DicomImageRedactorEngine): DicomImageRedactorEngine object.
        dcm_path (pathlib.Path): Path to DICOM file.
        has_sequence (bool): If additional pixel data is available in the instance.
    """
    # Arrange
    test_instance = pydicom.dcmread(dcm_path)

    # Act
    test_has_sequence = mock_engine._check_if_has_image_icon_sequence(test_instance)

    # Assert
    assert test_has_sequence == has_sequence


# ------------------------------------------------------
# DicomImageRedactorEngine._add_redact_box()
# ------------------------------------------------------
@pytest.mark.parametrize(
    "dcm_path, mock_is_compressed, mock_has_image_icon_sequence, mock_is_greyscale, mock_box_color, bounding_boxes_coordinates",
    [
        (
            Path(TEST_DICOM_PARENT_DIR, "0_ORIGINAL.dcm"),
            False,
            False,
            True,
            0,
            [
                {"top": 0, "left": 0, "width": 100, "height": 100},
                {"top": 24, "left": 0, "width": 75, "height": 51},
                {"top": 1, "left": 588, "width": 226, "height": 35},
            ],
        ),
        (
            Path(TEST_DICOM_PARENT_DIR, "0_ORIGINAL_compressed.dcm"),
            True,
            False,
            True,
            0,
            [
                {"top": 0, "left": 0, "width": 100, "height": 100},
                {"top": 24, "left": 0, "width": 75, "height": 51},
                {"top": 1, "left": 588, "width": 226, "height": 35},
            ],
        ),
        (
            Path(TEST_DICOM_PARENT_DIR, "0_ORIGINAL_icon_image_sequence.dcm"),
            False,
            True,
            True,
            0,
            [
                {"top": 0, "left": 0, "width": 100, "height": 100},
                {"top": 24, "left": 0, "width": 75, "height": 51},
                {"top": 1, "left": 588, "width": 226, "height": 35},
            ],
        ),
        (
            Path(TEST_DICOM_PARENT_DIR, "RGB_ORIGINAL.dcm"),
            False,
            False,
            False,
            (0, 0, 0),
            [
                {"top": 0, "left": 0, "width": 500, "height": 500},
                {"top": 24, "left": 0, "width": 75, "height": 51},
                {"top": 1, "left": 588, "width": 100, "height": 100},
            ],
        ),
    ],
)
def test_add_redact_box_happy_path(
    mocker,
    dcm_path: Path,
    mock_is_compressed: bool,
    mock_has_image_icon_sequence: bool,
    mock_is_greyscale: bool,
    mock_box_color: Union[int, Tuple[int, int, int]],
    bounding_boxes_coordinates: dict,
):
    """Test happy path for DicomImageRedactorEngine._add_redact_box

    Args:
        dcm_path (pathlib.Path): Path to DICOM file.
        mock_is_compressed (bool): If the pixel data is compressed.
        mock_has_image_icon_sequence (bool): If there is more than one set of pixel data.
        mock_is_greyscale (bool): Value to use when mocking _check_if_greyscale.
        mock_box_color (int or Tuple of int): Color value to assign to mocker.
        bouding_boxes_coordinates (dict): Formatted bbox coordinates.
    """
    # Arrange
    test_instance = pydicom.dcmread(dcm_path)
    crop_ratio = 0.75
    mock_check_if_compressed = mocker.patch.object(
        DicomImageRedactorEngine, "_check_if_compressed", return_value=mock_is_compressed
    )
    mock_check_if_has_image_icon_sequence = mocker.patch.object(
        DicomImageRedactorEngine, "_check_if_has_image_icon_sequence", return_value=mock_has_image_icon_sequence
    )
    mock_check_if_greyscale = mocker.patch.object(
        DicomImageRedactorEngine,
        "_check_if_greyscale",
        return_value=mock_is_greyscale,
    )
    mock_get_common_pixel = mocker.patch.object(
        DicomImageRedactorEngine,
        "_get_most_common_pixel_value",
        return_value=mock_box_color,
    )
    mock_set_bbox_color = mocker.patch.object(
        DicomImageRedactorEngine,
        "_set_bbox_color",
        return_value=mock_box_color,
    )
    mock_engine = DicomImageRedactorEngine()

    # Act
    test_redacted_instance = mock_engine._add_redact_box(test_instance, bounding_boxes_coordinates, crop_ratio)

    # Assert
    assert mock_check_if_compressed.call_count == 1
    assert mock_check_if_has_image_icon_sequence.call_count == 1
    assert mock_check_if_greyscale.call_count == 1
    if mock_is_greyscale is True:
        original_pixel_values = np.array(test_instance.pixel_array).flatten()
        redacted_pixel_values = np.array(test_redacted_instance.pixel_array).flatten()
        box_color_pixels_original = len(np.where(original_pixel_values == mock_box_color)[0])
        box_color_pixels_redacted = len(np.where(redacted_pixel_values == mock_box_color)[0])
        assert mock_get_common_pixel.call_count == 1
    else:
        list_of_RGB_pixels_original = np.vstack(test_instance.pixel_array).tolist()
        list_of_RGB_pixels_redacted = np.vstack(test_redacted_instance.pixel_array).tolist()
        box_color_pixels_original = len(np.unique(np.where(np.array(list_of_RGB_pixels_original) == mock_box_color)[0]))
        box_color_pixels_redacted = len(np.unique(np.where(np.array(list_of_RGB_pixels_redacted) == mock_box_color)[0]))
        assert mock_set_bbox_color.call_count == 1

    assert box_color_pixels_redacted > box_color_pixels_original


# ------------------------------------------------------
# DicomImageRedactorEngine._get_analyzer_results()
# ------------------------------------------------------
@pytest.mark.parametrize(
    "image, dcm_path, use_metadata, ad_hoc_recognizers",
    [
        (
            Image.fromarray(np.random.randint(255, size=(400, 400), dtype=np.uint8)),
            Path(TEST_DICOM_PARENT_DIR, "0_ORIGINAL.dcm"),
            False,
            None,
        ),
        (
            Image.fromarray(np.random.randint(255, size=(400, 400), dtype=np.uint8)),
            Path(TEST_DICOM_PARENT_DIR, "0_ORIGINAL.dcm"),
            False,
            [PatternRecognizer(supported_entity="PERSON", deny_list=["1"])],
        ),
        (
            Image.fromarray(np.random.randint(255, size=(400, 400), dtype=np.uint8)),
            Path(TEST_DICOM_PARENT_DIR, "0_ORIGINAL.dcm"),
            True,
            None,
        ),
        (
            Image.fromarray(np.random.randint(255, size=(400, 400), dtype=np.uint8)),
            Path(TEST_DICOM_PARENT_DIR, "0_ORIGINAL.dcm"),
            True,
            [PatternRecognizer(supported_entity="PERSON", deny_list=["2"])],
        ),
    ],
)
def test_get_analyzer_results_happy_path(
    mocker,
    mock_engine: DicomImageRedactorEngine,
    image: Image,
    dcm_path: str,
    use_metadata: bool,
    ad_hoc_recognizers: Optional[List[PatternRecognizer]],
):
    """Test happy path for DicomImageRedactorEngine._get_analyzer_results

    Args:
        mock_engine (DicomImageRedactorEngine): DicomImageRedactorEngine object.
        image (PIL.Image): A PIL image.
        dcm_path (pathlib.Path): Path to DICOM file.
        use_metadata (bool): Whether to consider metadata when running analysis.
        ad_hoc_recognizers(None or list): Ad-hoc recognizers to use.
    """
    # Arrange
    mock_analyze = mocker.patch(
        "presidio_image_redactor.dicom_image_redactor_engine.ImageAnalyzerEngine.analyze",
        return_value=None,
    )
    mock_get_text_metadata = mocker.patch(
        "presidio_image_redactor.dicom_image_redactor_engine.DicomImageRedactorEngine._get_text_metadata",
        return_value=[None, None, None],
    )
    mock_make_phi_list = mocker.patch(
        "presidio_image_redactor.dicom_image_redactor_engine.DicomImageRedactorEngine._make_phi_list",
        return_value=None,
    )
    mock_pattern_recognizer = mocker.patch(
        "presidio_image_redactor.dicom_image_redactor_engine.PatternRecognizer",
        return_value=None,
    )
    test_instance = pydicom.dcmread(dcm_path)

    # Act
    _ = mock_engine._get_analyzer_results(
        image=image,
        instance=test_instance,
        use_metadata=use_metadata,
        ocr_kwargs=None,
        ad_hoc_recognizers=ad_hoc_recognizers,
    )

    # Assert
    if use_metadata is False:
        mock_analyze.assert_called_once()
        mock_get_text_metadata.assert_not_called()
        mock_make_phi_list.assert_not_called()
        mock_pattern_recognizer.assert_not_called()
    elif use_metadata is True:
        mock_analyze.assert_called_once()
        mock_get_text_metadata.assert_called_once()
        mock_make_phi_list.assert_called_once()
        mock_pattern_recognizer.assert_called_once()


@pytest.mark.parametrize(
    "ad_hoc_recognizers",
    [("invalidType"), ([]), ([PatternRecognizer(supported_entity="TITLE", deny_list=["Mr", "Ms"]), 2])],
)
def test_get_analyzer_results_exceptions(
    mock_engine: DicomImageRedactorEngine,
    ad_hoc_recognizers: Optional[List[PatternRecognizer]],
):
    """Test error handling of DicomImageRedactorEngine _get_analyzer_results()

    Args:
        mock_engine (DicomImageRedactorEngine): DicomImageRedactorEngine object.
        ad_hoc_recognizers(None or list): Ad-hoc recognizers to use.
    """
    with pytest.raises(TypeError):
        # Arrange
        image = Image.fromarray(np.random.randint(255, size=(400, 400), dtype=np.uint8))
        test_instance = pydicom.dcmread(Path(TEST_DICOM_PARENT_DIR, "0_ORIGINAL.dcm"))

        # Act
        _ = mock_engine._get_analyzer_results(
            image=image,
            instance=test_instance,
            use_metadata=True,
            ocr_kwargs=None,
            ad_hoc_recognizers=ad_hoc_recognizers,
        )


# ------------------------------------------------------
# DicomImageRedactorEngine redact_and_return_bbox()
# ------------------------------------------------------
@pytest.mark.parametrize(
    "dcm_path",
    [
        (Path(TEST_DICOM_PARENT_DIR, "0_ORIGINAL.dcm")),
        (Path(TEST_DICOM_PARENT_DIR, "0_ORIGINAL_compressed.dcm")),
        (Path(TEST_DICOM_PARENT_DIR, "0_ORIGINAL_icon_image_sequence.dcm")),
        (Path(TEST_DICOM_PARENT_DIR, "RGB_ORIGINAL.dcm")),
        (Path(TEST_DICOM_DIR_2, "1_ORIGINAL.DCM")),
        (Path(TEST_DICOM_DIR_2, "2_ORIGINAL.dicom")),
        (Path(TEST_DICOM_DIR_3, "3_ORIGINAL.DICOM")),
    ],
)
def test_DicomImageRedactorEngine_redact_and_return_bbox(
    mocker,
    mock_engine: DicomImageRedactorEngine,
    dcm_path: str,
):
    """Test happy path for DicomImageRedactorEngine redact_and_return_bbox()

    Args:
        mock_engine (DicomImageRedactorEngine): DicomImageRedactorEngine object.
        dcm_path (str): Path to input DICOM file or dir.
    """
    # Arrange
    test_image = pydicom.dcmread(dcm_path)

    mock_check_greyscale = mocker.patch(
        "presidio_image_redactor.dicom_image_redactor_engine.DicomImageRedactorEngine._check_if_greyscale",
        return_value=None,
    )
    mock_rescale_dcm = mocker.patch(
        "presidio_image_redactor.dicom_image_redactor_engine.DicomImageRedactorEngine._rescale_dcm_pixel_array",
        return_value=None,
    )
    mock_image_fromarray = mocker.patch(
        "presidio_image_redactor.dicom_image_redactor_engine.Image.fromarray",
        return_value=None,
    )
    mock_add_padding = mocker.patch(
        "presidio_image_redactor.dicom_image_redactor_engine.DicomImageRedactorEngine._add_padding",
        return_value=None,
    )
    mock_analyze = mocker.patch(
        "presidio_image_redactor.dicom_image_redactor_engine.DicomImageRedactorEngine._get_analyzer_results",
        return_value=None,
    )

    mock_get_analyze_bbox = mocker.patch(
        "presidio_image_redactor.image_redactor_engine.BboxProcessor.get_bboxes_from_analyzer_results",
        return_value=None,
    )

    mock_remove_bbox_padding = mocker.patch(
        "presidio_image_redactor.image_redactor_engine.BboxProcessor.remove_bbox_padding",
        return_value=[{"mock_data": 1}, {"mock_data": 2}, {"mock_data": 3}],
    )

    mock_add_redact_box = mocker.patch(
        "presidio_image_redactor.dicom_image_redactor_engine.DicomImageRedactorEngine._add_redact_box",
        return_value=test_image,
    )

    # Act
    test_redacted_image, _ = mock_engine.redact_and_return_bbox(test_image, use_metadata=True)

    # Assert
    assert type(test_redacted_image) in [pydicom.dataset.FileDataset, pydicom.dataset.Dataset]
    # assertions for test_bboxes type causes silent failures/hangups for Python 3.11
    mock_check_greyscale.assert_called_once()
    mock_rescale_dcm.assert_called_once()
    mock_image_fromarray.assert_called_once()
    mock_add_padding.assert_called_once()
    mock_analyze.assert_called_once()
    mock_get_analyze_bbox.assert_called_once()
    mock_remove_bbox_padding.assert_called_once()
    mock_add_redact_box.assert_called_once()


@pytest.mark.parametrize(
    "image, load_file, expected_error_type",
    [
        (Path(TEST_DICOM_PARENT_DIR), True, ["TypeError", "IsADirectoryError", "PermissionError"]),
        (Path(TEST_DICOM_PARENT_DIR), False, ["TypeError"]),
        ("path_here", False, ["TypeError"]),
        (np.random.randint(255, size=(64, 64)), False, ["TypeError"]),
        (Image.fromarray(np.random.randint(255, size=(400, 400), dtype=np.uint8)), False, ["TypeError"]),
        (Path(TEST_DICOM_PARENT_DIR, "0_ORIGINAL_no_pixels.dcm"), True, ["AttributeError"]),
    ],
)
def test_DicomImageRedactorEngine_redact_and_return_bbox_exceptions(
    mock_engine: DicomImageRedactorEngine,
    image: T,
    load_file: bool,
    expected_error_type: List[str],
):
    """Test error handling of DicomImageRedactorEngine redact_and_return_bbox()

    Args:
        mock_engine (DicomImageRedactorEngine): DicomImageRedactorEngine object.
        image (any): Input "image".
        load_file (bool): Whether to run pydicom.dcmread() on the input image.
        expected_error_type (List(str)): Type of error we expect to be raised.
    """
    with pytest.raises(Exception) as exc_info:
        # Arrange
        if load_file:
            test_image = pydicom.dcmread(image)
        else:
            test_image = image
        # Act
        mock_engine.redact(test_image, fill="contrast", padding_width=25, use_metadata=True)

    # Assert
    assert exc_info.typename in expected_error_type


# ------------------------------------------------------
# DicomImageRedactorEngine redact()
# ------------------------------------------------------
def test_DicomImageRedactorEngine_redact_happy_path(
    mocker,
    mock_engine: DicomImageRedactorEngine,
):
    """Test happy path for DicomImageRedactorEngine redact()"""
    # Arrange
    test_image = pydicom.dcmread(Path(TEST_DICOM_PARENT_DIR, "0_ORIGINAL.dcm"))

    mock_redact_return_bbox = mocker.patch(
        "presidio_image_redactor.dicom_image_redactor_engine.DicomImageRedactorEngine.redact_and_return_bbox",
        return_value=[test_image, [{}, {}, {}]],
    )

    # Act
    test_redacted_image = mock_engine.redact(test_image)

    # Assert
    assert type(test_redacted_image) in [pydicom.dataset.FileDataset, pydicom.dataset.Dataset]
    mock_redact_return_bbox.assert_called_once()


# ------------------------------------------------------
# DicomImageRedactorEngine _save_bbox_json()
# ------------------------------------------------------
@pytest.mark.parametrize(
    "output_path, expected_output_json_path, bboxes",
    [
        (
            "dir1/dir2/output_dicom.dcm",
            "dir1/dir2/output_dicom.json",
            [{"top": 0, "left": 0, "width": 100, "height": 100}, {"top": 35, "left": 72, "width": 50, "height": 14}],
        ),
        (
            "dir1/output_dicom.dcm",
            "dir1/output_dicom.json",
            [{"top": 0, "left": 0, "width": 100, "height": 100}, {"top": 35, "left": 72, "width": 50, "height": 14}],
        ),
        (
            "output_dicom.dcm",
            "output_dicom.json",
            [{"top": 0, "left": 0, "width": 100, "height": 100}, {"top": 35, "left": 72, "width": 50, "height": 14}],
        ),
        (
            "dir1/dir2/output_dicom.DCM",
            "dir1/dir2/output_dicom.json",
            [{"top": 0, "left": 0, "width": 100, "height": 100}, {"top": 35, "left": 72, "width": 50, "height": 14}],
        ),
        (
            "dir1/dir2/output_dicom.dicom",
            "dir1/dir2/output_dicom.json",
            [{"top": 0, "left": 0, "width": 100, "height": 100}, {"top": 35, "left": 72, "width": 50, "height": 14}],
        ),
        (
            "dir1/dir2/output_dicom.DICOM",
            "dir1/dir2/output_dicom.json",
            [{"top": 0, "left": 0, "width": 100, "height": 100}, {"top": 35, "left": 72, "width": 50, "height": 14}],
        ),
    ],
)
def test_DicomImageRedactorEngine_save_bbox_json_happy_path(
    mock_engine: DicomImageRedactorEngine,
    output_path: str,
    expected_output_json_path: str,
    bboxes: List[Dict[str, int]],
):
    """Test happy path for DicomImageRedactorEngine _save_bbox_json()

    Args:
        mock_engine (DicomImageRedactorEngine): DicomImageRedactorEngine object.
        output_path (str): Path to output DICOM file.
        expected_output_json_path (str): Expected path to the output JSON file.
        bboxes (list): Bounding boxes to write out to JSON file.
    """
    with tempfile.TemporaryDirectory() as tmpdirname:
        # Arrange
        temp_output_path = Path(tmpdirname, output_path)
        temp_output_path.mkdir(parents=True, exist_ok=True)
        temp_expected_json_path = Path(tmpdirname, expected_output_json_path)

        # Act
        mock_engine._save_bbox_json(temp_output_path, bboxes)

        # Assert
        with open(temp_expected_json_path, "r") as read_file:
            loaded_json = json.load(read_file)
        assert loaded_json == bboxes


# ------------------------------------------------------
# DicomImageRedactorEngine _redact_single_dicom_image()
# ------------------------------------------------------
@pytest.mark.parametrize(
    "dcm_path, output_dir, overwrite",
    [
        (Path(TEST_DICOM_PARENT_DIR, "0_ORIGINAL.dcm"), "output", False),
        (Path(TEST_DICOM_PARENT_DIR, "0_ORIGINAL.dcm"), "output", True),
        (Path(TEST_DICOM_PARENT_DIR, "RGB_ORIGINAL.dcm"), "output", False),
        (Path(TEST_DICOM_DIR_2, "1_ORIGINAL.DCM"), "output", False),
        (Path(TEST_DICOM_DIR_2, "2_ORIGINAL.dicom"), "output", False),
        (Path(TEST_DICOM_DIR_3, "3_ORIGINAL.DICOM"), "output", False),
    ],
)
def test_DicomImageRedactorEngine_redact_single_dicom_image_happy_path(
    mocker,
    mock_engine: DicomImageRedactorEngine,
    dcm_path: str,
    output_dir: str,
    overwrite: bool,
):
    """Test happy path for DicomImageRedactorEngine _redact_single_dicom_image()

    Args:
        mock_engine (DicomImageRedactorEngine): DicomImageRedactorEngine object.
        dcm_path (str): Path to input DICOM file or dir.
        output_dir (str): Path to parent directory to write output to.
        overwrite (bool): True if overwriting original files.
    """
    # Arrange
    crop_ratio = 0.75
    mock_copy_files = mocker.patch(
        "presidio_image_redactor.dicom_image_redactor_engine.DicomImageRedactorEngine._copy_files_for_processing",
        return_value=dcm_path,
    )
    mock_image_fromarray = mocker.patch(
        "presidio_image_redactor.dicom_image_redactor_engine.Image.fromarray",
        return_value=None,
    )
    mock_add_padding = mocker.patch(
        "presidio_image_redactor.dicom_image_redactor_engine.DicomImageRedactorEngine._add_padding",
        return_value=None,
    )

    mock_analyze = mocker.patch(
        "presidio_image_redactor.dicom_image_redactor_engine.DicomImageRedactorEngine._get_analyzer_results",
        return_value=None,
    )

    mock_get_analyze_bbox = mocker.patch(
        "presidio_image_redactor.image_redactor_engine.BboxProcessor.get_bboxes_from_analyzer_results",
        return_value=None,
    )

    mock_remove_bbox_padding = mocker.patch(
        "presidio_image_redactor.image_redactor_engine.BboxProcessor.remove_bbox_padding",
        return_value=None,
    )

    class MockInstance:
        def save_as(self, dst_path: str):
            return None

    mock_add_redact_box = mocker.patch(
        "presidio_image_redactor.dicom_image_redactor_engine.DicomImageRedactorEngine._add_redact_box",
        return_value=MockInstance(),
    )

    # Act
    mock_engine._redact_single_dicom_image(
        dcm_path=dcm_path,
        crop_ratio=crop_ratio,
        fill="contrast",
        padding_width=25,
        use_metadata=True,
        overwrite=overwrite,
        dst_parent_dir=output_dir,
        save_bboxes=False,
    )

    # Assert
    if overwrite is True:
        assert mock_copy_files.call_count == 0
    else:
        assert mock_copy_files.call_count == 1
    assert mock_image_fromarray.call_count == 1
    assert mock_add_padding.call_count == 1
    assert mock_analyze.call_count == 1
    assert mock_get_analyze_bbox.call_count == 1
    assert mock_remove_bbox_padding.call_count == 1
    assert mock_add_redact_box.call_count == 1


@pytest.mark.parametrize(
    "dcm_path, expected_error_type",
    [
        (Path(TEST_DICOM_PARENT_DIR), "FileNotFoundError"),
        (Path("nonexistentfile.extension"), "FileNotFoundError"),
    ],
)
def test_DicomImageRedactorEngine_redact_single_dicom_image_exceptions(
    mock_engine: DicomImageRedactorEngine,
    dcm_path: str,
    expected_error_type: str,
):
    """Test error handling of DicomImageRedactorEngine _redact_single_dicom_image()

    Args:
        mock_engine (DicomImageRedactorEngine): DicomImageRedactorEngine object.
        dcm_path (str): Path to input DICOM file or dir.
        expected_error_type (str): Type of error we expect to be raised.
    """
    with pytest.raises(Exception) as exc_info:
        # Act
        mock_engine._redact_single_dicom_image(
            dcm_path=dcm_path,
            crop_ratio=0.75,
            fill="contrast",
            padding_width=25,
            use_metadata=True,
            overwrite=False,
            dst_parent_dir=".",
            save_bboxes=False,
        )

    # Assert
    assert expected_error_type == exc_info.typename


# ------------------------------------------------------
# DicomImageRedactorEngine _redact_multiple_dicom_images()
# ------------------------------------------------------
@pytest.mark.parametrize(
    "dcm_path, output_dir, overwrite",
    [
        (Path(TEST_DICOM_PARENT_DIR), "output", False),
        (Path(TEST_DICOM_PARENT_DIR), "output", True),
        (Path(TEST_DICOM_DIR_1), "output", False),
        (Path(TEST_DICOM_DIR_2), "output", False),
        (Path(TEST_DICOM_DIR_3), "output", False),
    ],
)
def test_DicomImageRedactorEngine_redact_multiple_dicom_images_happy_path(
    mocker,
    mock_engine: DicomImageRedactorEngine,
    dcm_path: str,
    output_dir: str,
    overwrite: bool,
):
    """Test happy path for DicomImageRedactorEngine _redact_multiple_dicom_images()

    Args:
        mock_engine (DicomImageRedactorEngine): DicomImageRedactorEngine object.
        dcm_path (str): Path to input DICOM file or dir.
        output_dir (str): Path to parent directory to write output to.
        overwrite (bool): True if overwriting original files.
    """
    # Arrange
    crop_ratio = 0.75
    mock_copy_files = mocker.patch(
        "presidio_image_redactor.dicom_image_redactor_engine.DicomImageRedactorEngine._copy_files_for_processing",
        return_value=dcm_path,
    )
    mock_dcm_files = [
        Path("dir1/dir2/file1.dcm"),
        Path("dir1/dir2/file2.dcm"),
        Path("dir1/dir2/dir3/file3.dcm"),
    ]
    mock_get_all_dcm_files = mocker.patch(
        "presidio_image_redactor.dicom_image_redactor_engine.DicomImageRedactorEngine._get_all_dcm_files",
        return_value=mock_dcm_files,
    )
    mock_redact_single = mocker.patch(
        "presidio_image_redactor.dicom_image_redactor_engine.DicomImageRedactorEngine._redact_single_dicom_image",
        return_value=None,
    )

    # Act
    mock_engine._redact_multiple_dicom_images(
        dcm_dir=dcm_path,
        crop_ratio=crop_ratio,
        fill="contrast",
        padding_width=25,
        use_metadata=True,
        overwrite=overwrite,
        dst_parent_dir=output_dir,
        save_bboxes=False,
    )

    # Assert
    if overwrite is True:
        assert mock_copy_files.call_count == 0
    else:
        assert mock_copy_files.call_count == 1
    assert mock_get_all_dcm_files.call_count == 1
    assert mock_redact_single.call_count == len(mock_dcm_files)


@pytest.mark.parametrize(
    "dcm_path, expected_error_type",
    [
        (Path(TEST_DICOM_PARENT_DIR, "0_ORIGINAL.dcm"), "FileNotFoundError"),
        (Path("nonexistentdir"), "FileNotFoundError"),
    ],
)
def test_DicomImageRedactorEngine_redact_multiple_dicom_images_exceptions(
    mock_engine: DicomImageRedactorEngine,
    dcm_path: str,
    expected_error_type: str,
):
    """Test error handling of DicomImageRedactorEngine _redact_multiple_dicom_images()

    Args:
        mock_engine (DicomImageRedactorEngine): DicomImageRedactorEngine object.
        dcm_path (str): Path to input DICOM file or dir.
        expected_error_type (str): Type of error we expect to be raised.
    """
    with pytest.raises(Exception) as exc_info:
        # Act
        mock_engine._redact_multiple_dicom_images(
            dcm_dir=dcm_path,
            crop_ratio=0.75,
            fill="contrast",
            padding_width=25,
            use_metadata=True,
            overwrite=False,
            dst_parent_dir=".",
            save_bboxes=False,
        )

    # Assert
    assert expected_error_type == exc_info.typename


# ------------------------------------------------------
# DicomImageRedactorEngine redact_from_file()
# ------------------------------------------------------
@pytest.mark.parametrize(
    "dcm_path, mock_dst_path",
    [
        (
            f"{TEST_DICOM_PARENT_DIR}/0_ORIGINAL.dcm",
            Path(TEST_DICOM_PARENT_DIR, "0_ORIGINAL.dcm"),
        ),
        (
            f"{TEST_DICOM_DIR_2}/1_ORIGINAL.DCM",
            Path(TEST_DICOM_DIR_2, "1_ORIGINAL.DCM"),
        ),
        (
            f"{TEST_DICOM_DIR_2}/2_ORIGINAL.dicom",
            Path(TEST_DICOM_DIR_2, "2_ORIGINAL.dicom"),
        ),
        (
            f"{TEST_DICOM_DIR_3}/3_ORIGINAL.DICOM",
            Path(TEST_DICOM_DIR_3, "3_ORIGINAL.DICOM"),
        ),
    ],
)
def test_DicomImageRedactorEngine_redact_from_file_happy_path(
    mocker,
    mock_engine: DicomImageRedactorEngine,
    dcm_path: str,
    mock_dst_path: Path,
):
    """Test happy path for DicomImageRedactorEngine redact_from_file()

    Args:
        mock_engine (DicomImageRedactorEngine): DicomImageRedactorEngine object.
        dcm_path (str): Path to input DICOM file or dir.
        mock_dst_path (pathlib.Path): Path to DICOM dir or file.
    """
    # Arrange
    mock_copy_files = mocker.patch(
        "presidio_image_redactor.dicom_image_redactor_engine.DicomImageRedactorEngine._copy_files_for_processing",
        return_value=mock_dst_path,
    )
    mock_redact_single = mocker.patch(
        "presidio_image_redactor.dicom_image_redactor_engine.DicomImageRedactorEngine._redact_single_dicom_image",
        return_value=None,
    )

    # Act
    mock_engine.redact_from_file(dcm_path, "output", padding_width=25, fill="contrast", use_metadata=True)

    # Assert
    assert mock_copy_files.call_count == 1
    assert mock_redact_single.call_count == 1


@pytest.mark.parametrize(
    "input_path, output_path, expected_error_type",
    [
        (TEST_DICOM_PARENT_DIR, "output", "TypeError"),
        (TEST_DICOM_DIR_1, "output", "TypeError"),
        (TEST_DICOM_DIR_2, "output", "TypeError"),
        (TEST_DICOM_DIR_3, "output", "TypeError"),
        (
            f"{TEST_DICOM_PARENT_DIR}/0_ORIGINAL.dcm",
            f"{TEST_DICOM_PARENT_DIR}/0_ORIGINAL.dcm",
            "TypeError",
        ),
        (
            f"{TEST_DICOM_PARENT_DIR}/0_ORIGINAL.dcm",
            f"{TEST_DICOM_DIR_3}/3_ORIGINAL.DICOM",
            "TypeError",
        ),
    ],
)
def test_DicomImageRedactorEngine_redact_from_file_exceptions(
    mock_engine: DicomImageRedactorEngine,
    input_path: str,
    output_path: Path,
    expected_error_type: str,
):
    """Test error handling of DicomImageRedactorEngine redact_from_file()

    Args:
        mock_engine (DicomImageRedactorEngine): DicomImageRedactorEngine object.
        input_path (str): Path to input DICOM file or dir.
        output_path (pathlib.Path): Path to DICOM dir or file.
        expected_error_type (str): Type of error we expect to be raised.
    """
    with pytest.raises(Exception) as exc_info:
        # Act
        mock_engine.redact_from_file(input_path, output_path, padding_width=25, fill="contrast", use_metadata=True)

    # Assert
    assert expected_error_type == exc_info.typename


# ------------------------------------------------------
# DicomImageRedactorEngine redact_from_directory()
# ------------------------------------------------------
@pytest.mark.parametrize(
    "dcm_path, mock_dst_path",
    [
        (TEST_DICOM_PARENT_DIR, Path(TEST_DICOM_PARENT_DIR)),
        (TEST_DICOM_DIR_2, Path(TEST_DICOM_DIR_1)),
        (TEST_DICOM_DIR_2, Path(TEST_DICOM_DIR_2)),
        (TEST_DICOM_DIR_3, Path(TEST_DICOM_DIR_3)),
    ],
)
def test_DicomImageRedactorEngine_redact_from_directory_happy_path(
    mocker,
    mock_engine: DicomImageRedactorEngine,
    dcm_path: str,
    mock_dst_path: Path,
):
    """Test happy path for DicomImageRedactorEngine redact_from_directory()

    Args:
        mock_engine (DicomImageRedactorEngine): DicomImageRedactorEngine object.
        dcm_path (str): Path to input DICOM file or dir.
        mock_dst_path (pathlib.Path): Path to DICOM dir or file.
    """
    # Arrange
    mock_copy_files = mocker.patch(
        "presidio_image_redactor.dicom_image_redactor_engine.DicomImageRedactorEngine._copy_files_for_processing",
        return_value=mock_dst_path,
    )
    mock_redact_multiple = mocker.patch(
        "presidio_image_redactor.dicom_image_redactor_engine.DicomImageRedactorEngine._redact_multiple_dicom_images",
        return_value=None,
    )

    # Act
    mock_engine.redact_from_directory(dcm_path, "output", padding_width=25, fill="contrast", use_metadata=True)

    # Assert
    assert mock_copy_files.call_count == 1
    assert mock_redact_multiple.call_count == 1


@pytest.mark.parametrize(
    "input_path, output_path, expected_error_type",
    [
        (f"{TEST_DICOM_PARENT_DIR}/0_ORIGINAL.dcm", "output", "TypeError"),
        (TEST_DICOM_DIR_1, f"{TEST_DICOM_PARENT_DIR}/0_ORIGINAL.dcm", "TypeError"),
        ("nonexistentdir", "output", "TypeError"),
    ],
)
def test_DicomImageRedactorEngine_redact_from_directory_exceptions(
    mock_engine: DicomImageRedactorEngine,
    input_path: str,
    output_path: Path,
    expected_error_type: str,
):
    """Test error handling of DicomImageRedactorEngine redact_from_directory()

    Args:
        mock_engine (DicomImageRedactorEngine): DicomImageRedactorEngine object.
        input_path (str): Path to input DICOM file or dir.
        output_path (pathlib.Path): Path to DICOM dir or file.
        expected_error_type (str): Type of error we expect to be raised.
    """
    with pytest.raises(Exception) as exc_info:
        # Act
        mock_engine.redact_from_directory(input_path, output_path, padding_width=25, fill="contrast", use_metadata=True)

    # Assert
    assert expected_error_type == exc_info.typename
