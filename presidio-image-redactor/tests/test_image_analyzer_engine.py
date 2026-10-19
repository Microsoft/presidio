import pytest
from presidio_analyzer import RecognizerResult, AnalyzerEngine, PatternRecognizer, Pattern
from presidio_analyzer.recognizer_registry import RecognizerRegistry

from presidio_image_redactor import ImageAnalyzerEngine
from presidio_image_redactor.entities import ImageRecognizerResult

import PIL
import matplotlib
import matplotlib.pyplot as plt
import numpy as np

from typing import List


def test_given_valid_ocr_and_entities_then_map_analyzer_returns_correct_len_and_output(
    get_ocr_analyzer_results, get_image_recognizerresult
):
    ocr_result, text, recognizer_result = get_ocr_analyzer_results

    expected_result = get_image_recognizerresult
    mapped_entities = ImageAnalyzerEngine.map_analyzer_results_to_bounding_boxes(
        recognizer_result, ocr_result, text, []
    )

    assert len(expected_result) == len(mapped_entities)
    assert expected_result == mapped_entities


def test_given_allow_list_then_map_analyzer_results_contain_allowed_words(get_ocr_analyzer_results):
    ocr_result, text, recognizer_result = get_ocr_analyzer_results
    mapped_entities = ImageAnalyzerEngine.map_analyzer_results_to_bounding_boxes(
        recognizer_result, ocr_result, text, allow_list=["Katie", "Cromley."]
    )

    assert len(mapped_entities) == 0


def test_given_empty_ocr_entities_lists_then_map_analyzer_results_returns_empty_list(
    get_ocr_analyzer_results,
):
    ocr_result, text, recognizer_result = get_ocr_analyzer_results
    assert ImageAnalyzerEngine.map_analyzer_results_to_bounding_boxes([], {}, "", []) == []
    assert ImageAnalyzerEngine.map_analyzer_results_to_bounding_boxes([], ocr_result, text, []) == []
    assert ImageAnalyzerEngine.map_analyzer_results_to_bounding_boxes(recognizer_result, {}, "", []) == []


def test_given_wrong_keys_in_ocr_dict_then_map_analyzer_results_returns_exception(
    get_ocr_analyzer_results,
):
    ocr_result, text, recognizer_result = get_ocr_analyzer_results
    ocr_result = {"words": ["John"], "level": [0]}
    with pytest.raises(KeyError):
        ImageAnalyzerEngine.map_analyzer_results_to_bounding_boxes(recognizer_result, ocr_result, "", [])


def test_given_repeat_entities_then_map_analyzer_results_returns_correct_no_of_bboxes(
    get_ocr_analyzer_results,
):
    ocr_result, text, recognizer_result = get_ocr_analyzer_results

    ocr_result["text"][1] = "Katie"
    recognizer_result.append(RecognizerResult("PERSON", 1, 6, 0.85))
    text = " Katie Interiors was created by Katie  Cromley."

    assert len(ImageAnalyzerEngine.map_analyzer_results_to_bounding_boxes(recognizer_result, ocr_result, text, [])) == 3


def test_given_word_has_entity_but_not_entity_then_map_entity_correct_bboxes_and_len(
    get_ocr_analyzer_results, get_image_recognizerresult
):
    ocr_result, text, recognizer_result = get_ocr_analyzer_results
    ocr_result["text"][2] = "Katieiors"
    text = " Homey Katieiors was created by Katie  Cromley."
    expected_result = get_image_recognizerresult
    mapped_entities = ImageAnalyzerEngine.map_analyzer_results_to_bounding_boxes(
        recognizer_result, ocr_result, text, []
    )

    assert len(expected_result) == len(mapped_entities)
    assert expected_result == mapped_entities


def test_given_multiword_entity_then_map_analyzer_returns_correct_bboxes_and_len(
    get_ocr_analyzer_results,
):
    ocr_result, text, recognizer_result = get_ocr_analyzer_results

    # create new object for multiple words entities
    recognizer_result = [RecognizerResult("PERSON", 32, 46, 0.85)]
    expected_result = [
        ImageRecognizerResult("PERSON", 32, 46, 0.85, 896, 64, 183, 40),
        ImageRecognizerResult("PERSON", 32, 46, 0.85, 141, 134, 190, 50),
    ]
    mapped_entities = ImageAnalyzerEngine.map_analyzer_results_to_bounding_boxes(
        recognizer_result, ocr_result, text, []
    )

    assert len(expected_result) == len(mapped_entities)
    assert expected_result == mapped_entities


def test_given_dif_len_entities_then_map_analyzer_returns_correct_outputand_len(
    get_ocr_analyzer_results, get_image_recognizerresult
):
    ocr_result, text, recognizer_result = get_ocr_analyzer_results
    recognizer_result[1].start += 1
    expected_result = get_image_recognizerresult
    expected_result[1].start += 1
    mapped_entities = ImageAnalyzerEngine.map_analyzer_results_to_bounding_boxes(
        recognizer_result, ocr_result, text, []
    )

    assert len(expected_result) == len(mapped_entities)
    assert expected_result == mapped_entities


@pytest.mark.parametrize(
    "ocr_threshold, expected_length",
    [(-1, 9), (50, 7), (80, 2), (100, 0)],
)
def test_threshold_ocr_result_returns_expected_results(image_analyzer_engine, ocr_threshold, expected_length):
    # Assign
    ocr_result = {}
    ocr_result["text"] = [
        "",
        "Homey",
        "Interiors",
        "was",
        "created",
        "by",
        "Katie",
        "",
        "Cromley.",
    ]
    ocr_result["left"] = [143, 143, 322, 530, 634, 827, 896, 141, 141]
    ocr_result["top"] = [64, 67, 67, 76, 64, 64, 64, 134, 134]
    ocr_result["width"] = [936, 160, 191, 87, 172, 51, 183, 801, 190]
    ocr_result["height"] = [50, 47, 37, 28, 40, 50, 40, 50, 50]
    ocr_result["conf"] = [-1, 99.5, 92.3, 42.7, 66.1, 51.2, 79.7, 64.0, 70.3]

    # Act
    test_filtered = image_analyzer_engine.threshold_ocr_result(ocr_result, ocr_threshold)

    # Assert
    assert len(test_filtered["conf"]) == expected_length


def test_remove_space_boxes_happy_path(image_analyzer_engine):
    # Arrange
    ocr_result = {"text": ["John", " ", "Doe", "", "  "], "left": [100, 0, 275, 415, 999], "top": [5, 315, 900, 0, 17]}

    # Act
    test_results = image_analyzer_engine.remove_space_boxes(ocr_result)

    # Assert
    assert len(test_results["text"]) == 2
    assert test_results["text"] == ["John", "Doe"]
    assert test_results["left"] == [100, 275]
    assert test_results["top"] == [5, 900]


@pytest.mark.parametrize(
    "text_analyzer_kwargs, expected_allow_list",
    [
        (None, []),
        ({"arg1": 1, "arg2": 2, "allow_list": ["a", "b", "c"]}, ["a", "b", "c"]),
        ({"arg1": 1, "arg2": 2, "allow_list": []}, []),
    ],
)
def test_check_for_allow_list_happy_path(
    image_analyzer_engine: ImageAnalyzerEngine, text_analyzer_kwargs: dict, expected_allow_list: list
):
    # Act
    test_allow_list = image_analyzer_engine._check_for_allow_list(text_analyzer_kwargs)

    # Assert
    assert test_allow_list == expected_allow_list


def test_fig2img_happy_path(image_analyzer_engine: ImageAnalyzerEngine):
    # Assign
    img = (np.random.standard_normal([10, 10, 3]) * 255).astype(np.uint8)
    test_fig = plt.figure()
    _ = plt.imshow(img, interpolation="none")

    # Act
    test_img = image_analyzer_engine.fig2img(test_fig)

    # Assert
    assert type(test_img) == PIL.PngImagePlugin.PngImageFile


@pytest.mark.parametrize(
    "ocr_bboxes, analyzer_bboxes, expected_output",
    [
        (
            [
                {"left": 50, "top": 0, "width": 30, "height": 10},
                {"left": 3, "top": 17, "width": 14, "height": 8},
                {"left": 100, "top": 70, "width": 40, "height": 40},
            ],
            [{"left": 50, "top": 0, "width": 30, "height": 10}, {"left": 3, "top": 17, "width": 14, "height": 8}],
            [
                {"left": 50, "top": 0, "width": 30, "height": 10, "is_PII": True},
                {"left": 3, "top": 17, "width": 14, "height": 8, "is_PII": True},
                {"left": 100, "top": 70, "width": 40, "height": 40, "is_PII": False},
            ],
        ),
        (
            [
                {"left": 50, "top": 0, "width": 30, "height": 10},
                {"left": 3, "top": 17, "width": 14, "height": 8},
                {"left": 100, "top": 70, "width": 40, "height": 40},
            ],
            [],
            [
                {"left": 50, "top": 0, "width": 30, "height": 10, "is_PII": False},
                {"left": 3, "top": 17, "width": 14, "height": 8, "is_PII": False},
                {"left": 100, "top": 70, "width": 40, "height": 40, "is_PII": False},
            ],
        ),
        (
            [
                {"left": 50, "top": 0, "width": 30, "height": 10},
                {"left": 3, "top": 17, "width": 14, "height": 8},
                {"left": 100, "top": 70, "width": 40, "height": 40},
            ],
            [{"left": 49, "top": 0, "width": 30, "height": 10}, {"left": 13, "top": 17, "width": 14, "height": 8}],
            [
                {"left": 50, "top": 0, "width": 30, "height": 10, "is_PII": False},
                {"left": 3, "top": 17, "width": 14, "height": 8, "is_PII": False},
                {"left": 100, "top": 70, "width": 40, "height": 40, "is_PII": False},
            ],
        ),
    ],
)
def test_get_pii_bboxes_happy_path(
    image_analyzer_engine: ImageAnalyzerEngine,
    ocr_bboxes: List[dict],
    analyzer_bboxes: List[dict],
    expected_output: List[dict],
):
    # Act
    test_pii_bboxes = image_analyzer_engine.get_pii_bboxes(ocr_bboxes, analyzer_bboxes)

    # Assert
    assert test_pii_bboxes == expected_output


def test_get_pii_bboxes_keeps_first_match_on_duplicate_positions(
    image_analyzer_engine: ImageAnalyzerEngine,
):
    """Test that the first analyzer bbox at a given position wins on duplicates."""
    # Assign
    ocr_bboxes = [{"left": 50, "top": 0, "width": 30, "height": 10}]
    analyzer_bboxes = [
        {"left": 50, "top": 0, "width": 30, "height": 10, "entity_type": "FIRST"},
        {"left": 50, "top": 0, "width": 30, "height": 10, "entity_type": "SECOND"},
    ]

    # Act
    test_pii_bboxes = image_analyzer_engine.get_pii_bboxes(ocr_bboxes, analyzer_bboxes)

    # Assert
    assert test_pii_bboxes == [
        {
            "left": 50,
            "top": 0,
            "width": 30,
            "height": 10,
            "entity_type": "FIRST",
            "is_PII": True,
        }
    ]


def _get_pii_bboxes_naive(ocr_bboxes, analyzer_bboxes):
    """Compute the O(n*m) reference result to check equivalence against."""
    bboxes = []
    for ocr_bbox in ocr_bboxes:
        has_match = False
        for analyzer_bbox in analyzer_bboxes:
            is_same = (
                ocr_bbox["left"] == analyzer_bbox["left"]
                and ocr_bbox["top"] == analyzer_bbox["top"]
                and ocr_bbox["width"] == analyzer_bbox["width"]
                and ocr_bbox["height"] == analyzer_bbox["height"]
            )
            if is_same:
                current_bbox = dict(analyzer_bbox)
                current_bbox["is_PII"] = True
                has_match = True
                break
        if not has_match:
            current_bbox = dict(ocr_bbox)
            current_bbox["is_PII"] = False
        bboxes.append(current_bbox)
    return bboxes


def test_get_pii_bboxes_matches_naive_implementation_at_scale(
    image_analyzer_engine: ImageAnalyzerEngine,
):
    """Test that the indexed lookup matches the naive O(n*m) scan at scale."""
    # Assign: build a large set of ocr bboxes, half of which overlap
    # positionally with analyzer bboxes.
    ocr_bboxes = [
        {"left": i, "top": i, "width": 10, "height": 10} for i in range(500)
    ]
    analyzer_bboxes = [
        {"left": i, "top": i, "width": 10, "height": 10, "entity_type": "PERSON"}
        for i in range(0, 500, 2)
    ]

    # Act
    expected = _get_pii_bboxes_naive(ocr_bboxes, analyzer_bboxes)
    actual = image_analyzer_engine.get_pii_bboxes(ocr_bboxes, analyzer_bboxes)

    # Assert
    assert actual == expected


@pytest.mark.parametrize(
    "bboxes, show_text_annotation, use_greyscale_cmap",
    [
        (
            [],
            False,
            False,
        ),
        (
            [],
            False,
            True,
        ),
        (
            [
                {"left": 50, "top": 0, "width": 30, "height": 10, "is_PII": True},
                {"left": 3, "top": 17, "width": 14, "height": 8, "is_PII": False},
            ],
            False,
            False,
        ),
        (
            [
                {"left": 50, "top": 0, "width": 30, "height": 10, "is_PII": True},
                {"left": 3, "top": 17, "width": 14, "height": 8, "is_PII": False},
            ],
            False,
            True,
        ),
        (
            [
                {"left": 50, "top": 0, "width": 30, "height": 10, "is_PII": True},
                {"left": 3, "top": 17, "width": 14, "height": 8, "is_PII": False},
            ],
            True,
            False,
        ),
        (
            [
                {"left": 50, "top": 0, "width": 30, "height": 10, "is_PII": True},
                {"left": 3, "top": 17, "width": 14, "height": 8, "is_PII": False},
            ],
            True,
            True,
        ),
        (
            [
                {"left": 50, "top": 0, "width": 30, "height": 10, "is_PII": False},
                {"left": 3, "top": 17, "width": 14, "height": 8, "is_PII": False},
            ],
            False,
            False,
        ),
    ],
)
def test_add_custom_bboxes_happy_path(
    image_analyzer_engine: ImageAnalyzerEngine, bboxes: List[dict], show_text_annotation: bool, use_greyscale_cmap: bool
):
    """Ideal version of this test would check for pixel color
    at the bbox positions, but the returned image includes
    the axes and padding which offset everything, making it
    difficult to check for color at exact positions.
    """
    # Assign
    imarray = np.random.rand(100, 100) * 255
    img = PIL.Image.fromarray(imarray.astype("uint8")).convert("L")
    color_red = [255, 0, 0, 255]
    color_blue = [0, 0, 255, 255]
    red_pixels = 0
    blue_pixels = 0
    is_any_PII = True in [bbox["is_PII"] for bbox in bboxes]

    # Act
    test_img = image_analyzer_engine.add_custom_bboxes(img, bboxes, show_text_annotation, use_greyscale_cmap)
    test_img_arr = np.array(test_img)

    def compare_color(actual_pixels, expected_color, threshold=10):
        """Compare single pixel from image to expected bbox color.

        Note this allows for some variation due to color distortion
        from image scaling. Thin bbox edge color does not come all
        the way through when at small scale.
        """
        C = [abs(a - b) for a, b in zip(actual_pixels, expected_color)]
        amount_match = sum(C)
        if amount_match >= threshold:
            color_match = True
        else:
            color_match = False
        return color_match

    if bboxes:
        for dim in test_img_arr:
            for pixel in dim:
                if compare_color(list(pixel), color_red):
                    red_pixels += 1
                if compare_color(list(pixel), color_blue):
                    blue_pixels += 1

    # Assert
    if not bboxes:
        assert test_img is not None
        assert isinstance(test_img, PIL.Image.Image)
        assert test_img.size == (100, 100)
    elif is_any_PII:
        assert red_pixels > 0
    else:
        assert blue_pixels > 0


def test_check_analyze_supports_language_param(get_mock_png):
    """Test that the method analyze from class ImageAnalyzerEngine
    supports the language parameter.
    Before there where a bug:
        "TypeError: presidio_analyzer.analyzer_engine.AnalyzerEngine.analyze() got multiple values for keyword argument 'language'"

    :param get_mock_png: The mock PNG image
    """
    redacted = ImageAnalyzerEngine().analyze(get_mock_png, language="en")
    assert len(redacted) > 0


def test_use_other_language_in_analyze(get_dummy_nlp_engine, get_mock_png):
    """Verify if the method analyze from class ImageAnalyzerEngine
    supports a language parameter other tham en.

    :get_dummy_nlp_engine: The mock of a NLP engine
    :param get_mock_png: The mock PNG image
    """
    # Create a dummy recognizer. It's necessary at least one recognizer to use the AnalyzerEngine
    pattern = Pattern(name="character_a_pattern", regex=r"####-DUMMY-####", score=1.0)
    dummy_recognizer = PatternRecognizer("DUMMY", patterns=[pattern], supported_language="pt")
    registry = RecognizerRegistry(recognizers=[dummy_recognizer], supported_languages=["pt"])

    # Create an AnalyzerEngine to suport another language
    analyzer_engine = AnalyzerEngine(nlp_engine=get_dummy_nlp_engine, registry=registry, supported_languages=["pt"])
    # Analyze the image using other language
    redacted = ImageAnalyzerEngine(analyzer_engine=analyzer_engine).analyze(
        get_mock_png, language="pt", entities=["DUMMY"]
    )
    # There aren't the dummy pattern in the image, so the redacted should be empty
    assert len(redacted) == 0
