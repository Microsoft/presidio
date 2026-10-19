import io
from copy import deepcopy
from typing import Dict, List, Optional, Tuple, Union

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageChops
from presidio_analyzer import AnalyzerEngine, RecognizerResult

from presidio_image_redactor import OCR, ImagePreprocessor, TesseractOCR
from presidio_image_redactor.entities import ImageRecognizerResult


class ImageAnalyzerEngine:
    """ImageAnalyzerEngine class.

    :param analyzer_engine: The Presidio AnalyzerEngine instance
        to be used to detect PII in text
    :param ocr: the OCR object to be used to detect text in images.
    :param image_preprocessor: The ImagePreprocessor object to be
        used to preprocess the image
    """

    def __init__(
        self,
        analyzer_engine: Optional[AnalyzerEngine] = None,
        ocr: Optional[OCR] = None,
        image_preprocessor: Optional[ImagePreprocessor] = None,
    ):
        if not analyzer_engine:
            analyzer_engine = AnalyzerEngine()
        self.analyzer_engine = analyzer_engine

        if not ocr:
            ocr = TesseractOCR()
        self.ocr = ocr

        if not image_preprocessor:
            image_preprocessor = ImagePreprocessor()
        self.image_preprocessor = image_preprocessor

    def analyze(
        self, image: object, ocr_kwargs: Optional[dict] = None, **text_analyzer_kwargs
    ) -> List[ImageRecognizerResult]:
        """Analyse method to analyse the given image.

        :param image: PIL Image/numpy array or file path(str) to be processed.
        :param ocr_kwargs: Additional params for OCR methods.
        :param text_analyzer_kwargs: Additional values for the analyze method
        in AnalyzerEngine.

        :return: List of the extract entities with image bounding boxes.
        """
        # Perform OCR
        perform_ocr_kwargs, ocr_threshold = self._parse_ocr_kwargs(ocr_kwargs)
        image, preprocessing_metadata = self.image_preprocessor.preprocess_image(image)
        ocr_result = self.ocr.perform_ocr(image, **perform_ocr_kwargs)
        ocr_result = self.remove_space_boxes(ocr_result)

        if preprocessing_metadata and ("scale_factor" in preprocessing_metadata):
            ocr_result = self._scale_bbox_results(
                ocr_result, preprocessing_metadata["scale_factor"]
            )

        # Apply OCR confidence threshold if it is passed in
        if ocr_threshold:
            ocr_result = self.threshold_ocr_result(ocr_result, ocr_threshold)

        # Analyze text
        text = self.ocr.get_text_from_ocr_dict(ocr_result)

        # Difines English as default language, if not specified
        if "language" not in text_analyzer_kwargs:
            text_analyzer_kwargs["language"] = "en"
        analyzer_result = self.analyzer_engine.analyze(
            text=text, **text_analyzer_kwargs
        )
        allow_list = self._check_for_allow_list(text_analyzer_kwargs)
        bboxes = self.map_analyzer_results_to_bounding_boxes(
            analyzer_result, ocr_result, text, allow_list
        )

        return bboxes

    @staticmethod
    def threshold_ocr_result(ocr_result: dict, ocr_threshold: float) -> dict:
        """Filter out OCR results below confidence threshold.

        :param ocr_result: OCR results (raw).
        :param ocr_threshold: Threshold value between -1 and 100.

        :return: OCR results with low confidence items removed.
        """
        if ocr_threshold < -1 or ocr_threshold > 100:
            raise ValueError("ocr_threshold must be between -1 and 100")

        # Get indices of items above threshold
        idx = list()
        for i, val in enumerate(ocr_result["conf"]):
            if float(val) >= ocr_threshold:
                idx.append(i)

        # Only retain high confidence items
        filtered_ocr_result = {}
        for key in list(ocr_result.keys()):
            filtered_ocr_result[key] = [ocr_result[key][i] for i in idx]

        return filtered_ocr_result

    @staticmethod
    def remove_space_boxes(ocr_result: dict) -> dict:
        """Remove OCR bboxes that are for spaces.

        :param ocr_result: OCR results (raw or thresholded).
        :return: OCR results with empty words removed.
        """
        # Get indices of items with no text
        idx = list()
        for i, text in enumerate(ocr_result["text"]):
            is_not_space = text.isspace() is False
            if text != "" and is_not_space:
                idx.append(i)

        # Only retain items with text
        filtered_ocr_result = {}
        for key in list(ocr_result.keys()):
            filtered_ocr_result[key] = [ocr_result[key][i] for i in idx]

        return filtered_ocr_result

    @staticmethod
    def map_analyzer_results_to_bounding_boxes(
        text_analyzer_results: List[RecognizerResult],
        ocr_result: dict,
        text: str,
        allow_list: List[str],
    ) -> List[ImageRecognizerResult]:
        """Map extracted PII entities to image bounding boxes.

        Matching is based on the position of the recognized entity from analyzer
        and word (in ocr dict) in the text.

        :param text_analyzer_results: PII entities recognized by presidio analyzer
        :param ocr_result: dict results with words and bboxes from OCR
        :param text: text the results are based on
        :param allow_list: List of words to not redact

        return: list of extracted entities with image bounding boxes
        """
        if (not ocr_result) or (not text_analyzer_results):
            return []

        bboxes = []
        proc_indexes = 0
        indexes = len(text_analyzer_results)

        pos = 0
        iter_ocr = enumerate(ocr_result["text"])
        for index, word in iter_ocr:
            if not word:
                pos += 1
            else:
                for element in text_analyzer_results:
                    text_element = text[element.start : element.end]
                    # check position and text of ocr word matches recognized entity
                    if (
                        max(pos, element.start) < min(element.end, pos + len(word))
                    ) and ((text_element in word) or (word in text_element)):
                        yes_make_bbox_for_word = (
                            (word is not None)
                            and (word != "")
                            and (word.isspace() is False)
                            and (word not in allow_list)
                        )
                        # Do not add bbox for standalone spaces / empty strings
                        if yes_make_bbox_for_word:
                            bboxes.append(
                                ImageRecognizerResult(
                                    element.entity_type,
                                    element.start,
                                    element.end,
                                    element.score,
                                    ocr_result["left"][index],
                                    ocr_result["top"][index],
                                    ocr_result["width"][index],
                                    ocr_result["height"][index],
                                )
                            )

                            # add bounding boxes for all words in ocr dict
                            # contained within the text of recognized entity
                            # based on relative position in the full text
                            while pos + len(word) < element.end:
                                prev_word = word
                                index, word = next(iter_ocr)
                                yes_make_bbox_for_word = (
                                    (word is not None)
                                    and (word != "")
                                    and (word.isspace() is False)
                                    and (word not in allow_list)
                                )
                                if yes_make_bbox_for_word:
                                    bboxes.append(
                                        ImageRecognizerResult(
                                            element.entity_type,
                                            element.start,
                                            element.end,
                                            element.score,
                                            ocr_result["left"][index],
                                            ocr_result["top"][index],
                                            ocr_result["width"][index],
                                            ocr_result["height"][index],
                                        )
                                    )
                                pos += len(prev_word) + 1
                            proc_indexes += 1

                if proc_indexes == indexes:
                    break
                pos += len(word) + 1

        return bboxes

    @staticmethod
    def _scale_bbox_results(
        ocr_result: Dict[str, List[Union[int, str]]], scale_factor: float
    ) -> Dict[str, float]:
        """Scale down the bounding box results based on a scale percentage.

        :param ocr_result: OCR results (raw).
        :param scale_percent: Scale percentage for resizing the bounding box.

        :return: OCR results (scaled).
        """
        scaled_results = deepcopy(ocr_result)
        coordinate_keys = ["left", "top"]
        dimension_keys = ["width", "height"]

        for coord_key in coordinate_keys:
            scaled_results[coord_key] = [
                int(np.ceil((x) / (scale_factor))) for x in scaled_results[coord_key]
            ]

        for dim_key in dimension_keys:
            scaled_results[dim_key] = [
                max(1, int(np.ceil(x / (scale_factor))))
                for x in scaled_results[dim_key]
            ]
        return scaled_results

    @staticmethod
    def _remove_bbox_padding(
        analyzer_bboxes: List[Dict[str, Union[str, float, int]]],
        padding_width: int,
    ) -> List[Dict[str, int]]:
        """Remove added padding in bounding box coordinates.

        :param analyzer_bboxes: The bounding boxes from analyzer results.
        :param padding_width: Pixel width used for padding (0 if no padding).

        :return: Bounding box information per word.
        """

        unpadded_results = deepcopy(analyzer_bboxes)
        if padding_width < 0:
            raise ValueError("Padding width must be a non-negative integer.")

        coordinate_keys = ["left", "top"]
        for coord_key in coordinate_keys:
            unpadded_results[coord_key] = [
                max(0, x - padding_width) for x in unpadded_results[coord_key]
            ]

        return unpadded_results

    @staticmethod
    def _parse_ocr_kwargs(ocr_kwargs: dict) -> Tuple[dict, float]:
        """Parse the OCR-related kwargs.

        :param ocr_kwargs: Parameters for OCR operations.

        :return: Params for ocr.perform_ocr and ocr_threshold
        """
        ocr_threshold = None
        if ocr_kwargs is not None:
            if "ocr_threshold" in ocr_kwargs:
                ocr_threshold = ocr_kwargs["ocr_threshold"]
                ocr_kwargs = {
                    key: value
                    for key, value in ocr_kwargs.items()
                    if key != "ocr_threshold"
                }
        else:
            ocr_kwargs = {}

        return ocr_kwargs, ocr_threshold

    @staticmethod
    def _check_for_allow_list(text_analyzer_kwargs: dict) -> List[str]:
        """Check the text_analyzer_kwargs for an allow_list.

        :param text_analyzer_kwargs: Text analyzer kwargs.
        :return: The allow list if it exists.
        """
        allow_list = []
        if text_analyzer_kwargs is not None:
            if "allow_list" in text_analyzer_kwargs:
                allow_list = text_analyzer_kwargs["allow_list"]

        return allow_list

    @staticmethod
    def fig2img(fig: matplotlib.figure.Figure) -> Image:
        """Convert a Matplotlib figure to a PIL Image and return it.

        :param fig: Matplotlib figure.

        :return: Image of figure.
        """
        buf = io.BytesIO()
        fig.savefig(buf)
        buf.seek(0)
        img = Image.open(buf)

        return img

    @staticmethod
    def get_pii_bboxes(
        ocr_bboxes: List[dict], analyzer_bboxes: List[dict]
    ) -> List[dict]:
        """Get a list of bboxes with is_PII property.

        :param ocr_bboxes: Bboxes from OCR results.
        :param analyzer_bboxes: Bboxes from analyzer results.

        :return: All bboxes with appropriate label for whether it is PHI or not.
        """
        # Index analyzer bboxes by position/dimension once, instead of
        # rescanning the full analyzer_bboxes list for every ocr_bbox
        # (this turns an O(ocr_bboxes x analyzer_bboxes) scan into O(n + m)).
        analyzer_bbox_by_position = {}
        for analyzer_bbox in analyzer_bboxes:
            key = (
                analyzer_bbox["left"],
                analyzer_bbox["top"],
                analyzer_bbox["width"],
                analyzer_bbox["height"],
            )
            # Keep the first match for a given position, matching the
            # original loop's break-on-first-match behavior.
            analyzer_bbox_by_position.setdefault(key, analyzer_bbox)

        bboxes = []
        for ocr_bbox in ocr_bboxes:
            key = (
                ocr_bbox["left"],
                ocr_bbox["top"],
                ocr_bbox["width"],
                ocr_bbox["height"],
            )
            matched_bbox = analyzer_bbox_by_position.get(key)

            if matched_bbox is not None:
                current_bbox = matched_bbox
                current_bbox["is_PII"] = True
            else:
                current_bbox = ocr_bbox
                current_bbox["is_PII"] = False

            bboxes.append(current_bbox)

        return bboxes

    @classmethod
    def add_custom_bboxes(
        cls,
        image: Image,
        bboxes: List[dict],
        show_text_annotation: bool = True,
        use_greyscale_cmap: bool = False,
    ) -> Image:
        """Add custom bounding boxes to image.

        :param image: Standard image of DICOM pixels.
        :param bboxes: List of bounding boxes to display (with is_PII field).
        :param show_text_annotation: True if you want text annotation for
        PHI status to display.
        :param use_greyscale_cmap: Use greyscale color map.
        :return: Image with bounding boxes drawn on.
        """
        image_custom = ImageChops.duplicate(image)
        image_x, image_y = image_custom.size

        fig, ax = plt.subplots()
        image_r = 70
        fig.set_size_inches(image_x / image_r, image_y / image_r)

        for box in bboxes:
            try:
                entity_type = box["entity_type"]
            except KeyError:
                entity_type = "UNKNOWN"

            try:
                if box["is_PII"]:
                    bbox_color = "r"
                else:
                    bbox_color = "b"
            except KeyError:
                bbox_color = "b"

            # Get coordinates and dimensions
            x0 = box["left"]
            y0 = box["top"]
            x1 = x0 + box["width"]
            y1 = y0 + box["height"]
            rect = matplotlib.patches.Rectangle(
                (x0, y0), x1 - x0, y1 - y0, edgecolor=bbox_color, facecolor="none"
            )
            ax.add_patch(rect)
            if show_text_annotation:
                ax.annotate(
                    entity_type,
                    xy=(x0 - 3, y0 - 3),
                    xycoords="data",
                    bbox=dict(boxstyle="round4,pad=.5", fc="0.9"),
                )

        # When there are no bboxes and no greyscale colormap is needed, return the
        # image directly to avoid unnecessary matplotlib rendering overhead and to
        # preserve the original image fidelity (e.g. for RGB verification images).
        if not bboxes and not use_greyscale_cmap:
            plt.close(fig)
            return image_custom

        if use_greyscale_cmap:
            ax.imshow(image_custom, cmap="gray")
        else:
            ax.imshow(image_custom)
        im_from_fig = cls.fig2img(fig)
        im_resized = im_from_fig.resize((image_x, image_y))
        plt.close(fig)

        return im_resized
