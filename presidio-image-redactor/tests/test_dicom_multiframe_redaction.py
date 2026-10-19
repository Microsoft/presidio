"""Tests for multi-frame DICOM redaction support.

Covers issue #1737 (every frame of a multi-frame instance must be scanned and
redacted) and the related #1731 crash ("Too many dimensions: 3 > 2" on
multi-frame XA grayscale instances).
"""

import numpy as np
import pydicom
import pytest
from presidio_image_redactor.dicom_image_redactor_engine import (
    DicomImageRedactorEngine,
)
from presidio_image_redactor.entities import ImageRecognizerResult
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid


def _build_dicom(
    *,
    frames: int,
    rows: int = 16,
    cols: int = 16,
    samples_per_pixel: int = 1,
    photometric: str = "MONOCHROME2",
    bits_allocated: int = 16,
) -> FileDataset:
    """Build a minimal synthetic (optionally multi-frame) DICOM instance.

    Pixel values are distinct and non-flat so that per-frame rescaling and
    redaction can be observed.
    """
    file_meta = FileMetaDataset()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.MediaStorageSOPClassUID = pydicom.uid.SecondaryCaptureImageStorage
    file_meta.MediaStorageSOPInstanceUID = generate_uid()

    instance = FileDataset(
        "synthetic.dcm", {}, file_meta=file_meta, preamble=b"\x00" * 128
    )
    instance.Rows = rows
    instance.Columns = cols
    instance.NumberOfFrames = frames
    instance.SamplesPerPixel = samples_per_pixel
    instance.PhotometricInterpretation = photometric
    instance.BitsAllocated = bits_allocated
    instance.BitsStored = bits_allocated
    instance.HighBit = bits_allocated - 1
    instance.PixelRepresentation = 0
    if samples_per_pixel == 3:
        instance.PlanarConfiguration = 0

    dtype = np.uint16 if bits_allocated == 16 else np.uint8
    if samples_per_pixel == 1:
        shape = (frames, rows, cols)
    else:
        shape = (frames, rows, cols, samples_per_pixel)
    pixels = (np.arange(int(np.prod(shape))) % 200).astype(dtype).reshape(shape)
    instance.PixelData = pixels.tobytes()
    return instance


class _StubAnalyzer:
    """Minimal stand-in for ImageAnalyzerEngine (avoids OCR/NLP dependencies)."""

    def __init__(self, results=None):
        self._results = results or []

    def analyze(self, image, **kwargs):  # noqa: ANN001, ANN003
        return list(self._results)


# ------------------------------------------------------
# DicomImageRedactorEngine._get_number_of_frames()
# ------------------------------------------------------
@pytest.mark.parametrize("frames, expected", [(1, 1), (3, 3), (12, 12)])
def test_get_number_of_frames_happy_path(frames: int, expected: int):
    """Number of Frames (0028,0008) is read for multi- and single-frame data."""
    instance = _build_dicom(frames=frames)
    assert DicomImageRedactorEngine._get_number_of_frames(instance) == expected


def test_get_number_of_frames_defaults_to_one_when_absent():
    """A missing Number of Frames element defaults to a single frame."""
    instance = _build_dicom(frames=1)
    del instance.NumberOfFrames
    assert DicomImageRedactorEngine._get_number_of_frames(instance) == 1


# ------------------------------------------------------
# DicomImageRedactorEngine._rescale_dcm_pixel_array() (multi-frame)
# ------------------------------------------------------
def test_rescale_dcm_pixel_array_multiframe_returns_stacked_uint8():
    """Multi-frame rescaling returns a uint8 stack with the frame dimension."""
    instance = _build_dicom(frames=4, rows=8, cols=8)
    rescaled = DicomImageRedactorEngine._rescale_dcm_pixel_array(
        instance, is_greyscale=True
    )
    assert rescaled.shape == (4, 8, 8)
    assert rescaled.dtype == np.uint8


def test_rescale_dcm_pixel_array_single_frame_returns_2d():
    """Single-frame rescaling still returns a 2D uint8 array."""
    instance = _build_dicom(frames=1, rows=8, cols=8)
    rescaled = DicomImageRedactorEngine._rescale_dcm_pixel_array(
        instance, is_greyscale=True
    )
    assert rescaled.shape == (8, 8)
    assert rescaled.dtype == np.uint8


def test_rescale_array_flat_frame_returns_zeros():
    """A flat (single-intensity) greyscale frame rescales to zeros, no error."""
    flat = np.full((6, 6), 7, dtype=np.uint16)
    rescaled = DicomImageRedactorEngine._rescale_array(flat, is_greyscale=True)
    assert rescaled.shape == (6, 6)
    assert np.all(rescaled == 0)


# ------------------------------------------------------
# DicomImageRedactorEngine._add_redact_box() (multi-frame) -- core fix
# ------------------------------------------------------
def test_add_redact_box_multiframe_greyscale_redacts_every_frame(mocker):
    """Per-frame bboxes redact the same region on every greyscale frame."""
    frames = 3
    instance = _build_dicom(frames=frames, rows=20, cols=20)
    box_color = 0
    mocker.patch.object(
        DicomImageRedactorEngine,
        "_get_most_common_pixel_value",
        return_value=box_color,
    )
    bbox = {"top": 5, "left": 5, "width": 6, "height": 6}
    per_frame_bboxes = [[bbox] for _ in range(frames)]

    redacted = DicomImageRedactorEngine._add_redact_box(
        instance, per_frame_bboxes, crop_ratio=0.75, fill="contrast"
    )

    redacted_pa = redacted.pixel_array
    assert redacted_pa.shape == (frames, 20, 20)
    assert int(redacted.NumberOfFrames) == frames
    for i in range(frames):
        region = redacted_pa[i, 5:11, 5:11]
        assert np.all(region == box_color), f"frame {i} region not redacted"
        # A pixel outside the box is unchanged from the original.
        assert redacted_pa[i, 0, 0] == instance.pixel_array[i, 0, 0]


def test_add_redact_box_multiframe_color_redacts_every_frame(mocker):
    """Per-frame bboxes redact the same region on every color frame."""
    frames = 2
    instance = _build_dicom(
        frames=frames,
        rows=12,
        cols=12,
        samples_per_pixel=3,
        photometric="RGB",
        bits_allocated=8,
    )
    mocker.patch.object(
        DicomImageRedactorEngine, "_set_bbox_color", return_value=(0, 0, 0)
    )
    bbox = {"top": 2, "left": 2, "width": 5, "height": 5}
    per_frame_bboxes = [[bbox] for _ in range(frames)]

    redacted = DicomImageRedactorEngine._add_redact_box(
        instance, per_frame_bboxes, crop_ratio=0.75, fill="contrast"
    )

    redacted_pa = redacted.pixel_array
    assert redacted_pa.shape == (frames, 12, 12, 3)
    for i in range(frames):
        assert np.all(redacted_pa[i, 2:7, 2:7, :] == 0), f"frame {i} not redacted"


def test_add_redact_box_flat_list_applies_to_all_frames(mocker):
    """A flat bbox list passed for a multi-frame instance redacts all frames."""
    frames = 3
    instance = _build_dicom(frames=frames, rows=16, cols=16)
    mocker.patch.object(
        DicomImageRedactorEngine, "_get_most_common_pixel_value", return_value=0
    )
    flat_bboxes = [{"top": 4, "left": 4, "width": 4, "height": 4}]

    redacted = DicomImageRedactorEngine._add_redact_box(
        instance, flat_bboxes, crop_ratio=0.75, fill="contrast"
    )

    redacted_pa = redacted.pixel_array
    for i in range(frames):
        assert np.all(redacted_pa[i, 4:8, 4:8] == 0), f"frame {i} not redacted"


def test_add_redact_box_per_frame_shorter_than_frames(mocker):
    """Fewer per-frame bbox lists than frames leaves trailing frames untouched."""
    frames = 3
    instance = _build_dicom(frames=frames, rows=16, cols=16)
    mocker.patch.object(
        DicomImageRedactorEngine, "_get_most_common_pixel_value", return_value=0
    )
    # Only the first frame has a bbox list provided.
    per_frame_bboxes = [[{"top": 2, "left": 2, "width": 4, "height": 4}]]

    redacted = DicomImageRedactorEngine._add_redact_box(
        instance, per_frame_bboxes, crop_ratio=0.75, fill="contrast"
    )

    redacted_pa = redacted.pixel_array
    assert np.all(redacted_pa[0, 2:6, 2:6] == 0)
    # Frames 1 and 2 received no bbox list and are unchanged.
    for i in range(1, frames):
        assert np.array_equal(redacted_pa[i], instance.pixel_array[i])


def test_add_redact_box_single_frame_unchanged_behavior(mocker):
    """Single-frame redaction still operates on the lone 2D frame."""
    instance = _build_dicom(frames=1, rows=16, cols=16)
    mocker.patch.object(
        DicomImageRedactorEngine, "_get_most_common_pixel_value", return_value=0
    )
    bboxes = [{"top": 3, "left": 3, "width": 5, "height": 5}]

    redacted = DicomImageRedactorEngine._add_redact_box(
        instance, bboxes, crop_ratio=0.75, fill="contrast"
    )

    redacted_pa = redacted.pixel_array
    assert redacted_pa.shape == (16, 16)
    assert np.all(redacted_pa[3:8, 3:8] == 0)


def test_add_redact_box_single_frame_accepts_per_frame_format(mocker):
    """A single-frame instance accepts the per-frame ([[...]]) bbox format."""
    instance = _build_dicom(frames=1, rows=16, cols=16)
    mocker.patch.object(
        DicomImageRedactorEngine, "_get_most_common_pixel_value", return_value=0
    )
    per_frame_bboxes = [[{"top": 3, "left": 3, "width": 5, "height": 5}]]

    redacted = DicomImageRedactorEngine._add_redact_box(
        instance, per_frame_bboxes, crop_ratio=0.75, fill="contrast"
    )

    assert redacted.pixel_array.shape == (16, 16)
    assert np.all(redacted.pixel_array[3:8, 3:8] == 0)


# ------------------------------------------------------
# DicomImageRedactorEngine.redact() end-to-end (multi-frame)
# ------------------------------------------------------
def test_redact_multiframe_does_not_raise_and_preserves_shape():
    """XA-style multi-frame greyscale no longer raises 'Too many dimensions'.

    Regression test for #1731.
    """
    instance = _build_dicom(frames=3, rows=24, cols=24)
    engine = DicomImageRedactorEngine(image_analyzer_engine=_StubAnalyzer([]))

    redacted = engine.redact(instance, use_metadata=False)

    assert isinstance(redacted, (pydicom.dataset.FileDataset, pydicom.dataset.Dataset))
    assert int(redacted.NumberOfFrames) == 3
    assert redacted.pixel_array.shape == (3, 24, 24)


def test_redact_multiframe_redacts_all_frames_end_to_end(mocker):
    """The full redact pipeline applies redaction to every frame (#1737)."""
    frames = 3
    instance = _build_dicom(frames=frames, rows=40, cols=40)
    # Detection coordinates chosen so they remain inside the frame after the
    # OCR padding is removed (padding_width defaults to 25).
    detection = ImageRecognizerResult("PERSON", 0, 6, 0.99, 30, 30, 8, 8)
    engine = DicomImageRedactorEngine(image_analyzer_engine=_StubAnalyzer([detection]))
    mocker.patch.object(
        DicomImageRedactorEngine, "_get_most_common_pixel_value", return_value=0
    )

    redacted, _ = engine.redact_and_return_bbox(instance, use_metadata=False)

    redacted_pa = redacted.pixel_array
    original_pa = instance.pixel_array
    assert int(redacted.NumberOfFrames) == frames
    # Every frame must differ from the original (PHI redacted on each frame).
    for i in range(frames):
        assert not np.array_equal(
            redacted_pa[i], original_pa[i]
        ), f"frame {i} was not redacted"
    # Identical detection per frame => identical redaction across frames.
    for i in range(1, frames):
        assert np.array_equal(redacted_pa[0], redacted_pa[i])


# ------------------------------------------------------
# Frame deduplication (identical frames analyzed once)
# ------------------------------------------------------
def test_identical_frames_are_analyzed_once(mocker):
    """Byte-identical frames are analyzed once while every frame is redacted.

    Static lead-in or padding frames in cine loops are the typical case.
    """
    frames = 4
    instance = _build_dicom(frames=frames, rows=40, cols=40)
    identical = np.tile(instance.pixel_array[0], (frames, 1, 1))
    instance.PixelData = identical.tobytes()

    detection = ImageRecognizerResult("PERSON", 0, 6, 0.99, 30, 30, 8, 8)
    engine = DicomImageRedactorEngine(image_analyzer_engine=_StubAnalyzer([detection]))
    mocker.patch.object(
        DicomImageRedactorEngine, "_get_most_common_pixel_value", return_value=0
    )
    spy = mocker.spy(DicomImageRedactorEngine, "_get_analyzer_results")

    redacted, bboxes = engine.redact_and_return_bbox(instance, use_metadata=False)

    assert spy.call_count == 1, "identical frames must be analyzed only once"
    # Every frame is still redacted, with identical results.
    redacted_pa = redacted.pixel_array
    original_pa = instance.pixel_array
    for i in range(frames):
        assert not np.array_equal(
            redacted_pa[i], original_pa[i]
        ), f"frame {i} was not redacted"
        assert np.array_equal(redacted_pa[0], redacted_pa[i])
    # The aggregated bbox return still reports one detection per frame.
    assert len(bboxes) == frames


def test_duplicate_frames_reuse_results_distinct_frames_do_not(mocker):
    """Only byte-identical frames reuse analysis results.

    Distinct frames are each analyzed.
    """
    frames = 3
    instance = _build_dicom(frames=frames, rows=40, cols=40)
    pixels = instance.pixel_array.copy()
    pixels[1, 0:5, 0:5] = 500  # make frame 1 distinct
    pixels[2] = pixels[0]  # frame 2 duplicates frame 0
    instance.PixelData = pixels.tobytes()

    engine = DicomImageRedactorEngine(image_analyzer_engine=_StubAnalyzer([]))
    spy = mocker.spy(DicomImageRedactorEngine, "_get_analyzer_results")

    engine.redact_and_return_bbox(instance, use_metadata=False)

    assert spy.call_count == 2, "two distinct frames -> two analysis runs"
