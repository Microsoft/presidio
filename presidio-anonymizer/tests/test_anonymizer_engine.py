from typing import Dict, List

import pytest
import copy

from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import (
    InvalidParamError,
    RecognizerResult,
    OperatorConfig,
    PIIEntity,
    OperatorResult,
    EngineResult,
)
from presidio_anonymizer.operators import OperatorType, AHDS_AVAILABLE


def test_given_request_anonymizers_return_list():
    engine = AnonymizerEngine()
    expected_list = {"hash", "mask", "redact", "replace", "custom", "keep", "encrypt"}
    if AHDS_AVAILABLE:
        expected_list.add("surrogate_ahds")
    anon_list = set(engine.get_anonymizers())

    assert anon_list == expected_list


def test_given_empty_analyzers_list_then_we_get_same_text_back():
    engine = AnonymizerEngine()
    text = "one two three"
    assert engine.anonymize(text, [], {}).text == text


def test_given_empty_anonymziers_list_then_we_fall_to_default():
    engine = AnonymizerEngine()
    text = "please REPLACE ME."
    analyzer_result = RecognizerResult("SSN", 7, 17, 0.8)
    result = engine.anonymize(text, [analyzer_result], {}).text
    assert result == "please <SSN>."


def test_given_custom_anonymizer_then_we_manage_to_anonymize_successfully():
    engine = AnonymizerEngine()
    text = (
        "Fake card number 4151 3217 6243 3448.com that "
        "overlaps with nonexisting URL."
    )
    analyzer_result = RecognizerResult("CREDIT_CARD", 17, 36, 0.8)
    analyzer_result2 = RecognizerResult("URL", 32, 40, 0.8)
    anonymizer_config = OperatorConfig("custom", {"lambda": lambda x: f"<ENTITY: {x}>"})
    result = engine.anonymize(
        text, [analyzer_result, analyzer_result2], {"DEFAULT": anonymizer_config}
    ).text
    resp = (
        "Fake card number <ENTITY: 4151 3217 6243 3448>"
        "<ENTITY: 3448.com> that overlaps with nonexisting URL."
    )
    assert result == resp


def test_given_none_as_anonymziers_list_then_we_fall_to_default():
    engine = AnonymizerEngine()
    text = "please REPLACE ME."
    analyzer_result = RecognizerResult("SSN", 7, 17, 0.8)
    result = engine.anonymize(text, [analyzer_result]).text
    assert result == "please <SSN>."


def test_given_default_anonymizer_then_we_use_it():
    engine = AnonymizerEngine()
    text = "please REPLACE ME."
    analyzer_result = RecognizerResult("SSN", 7, 17, 0.8)
    anonymizer_config = OperatorConfig("replace", {"new_value": "and thank you"})
    result = engine.anonymize(
        text, [analyzer_result], {"DEFAULT": anonymizer_config}
    ).text
    assert result == "please and thank you."


def test_given_specific_anonymizer_then_we_use_it():
    engine = AnonymizerEngine()
    text = "please REPLACE ME."
    analyzer_result = RecognizerResult("SSN", 7, 17, 0.8)
    anonymizer_config = OperatorConfig("replace", {"new_value": "and thank you"})
    ssn_anonymizer_config = OperatorConfig("redact", {})
    result = engine.anonymize(
        text,
        [analyzer_result],
        {"DEFAULT": anonymizer_config, "SSN": ssn_anonymizer_config},
    ).text
    assert result == "please ."


@pytest.mark.parametrize(
    # fmt: off
    "original_text,start,end",
    [
        ("hello world", 5, 12),
        ("hello world", 12, 16),
    ],
    # fmt: on
)
def test_given_analyzer_result_with_an_incorrect_text_positions_then_we_fail(
    original_text, start, end
):
    engine = AnonymizerEngine()
    analyzer_result = RecognizerResult("type", start, end, 0.5)
    err_msg = (
        f"Invalid analyzer result, start: {start} and end: "
        f"{end}, while text length is only 11."
    )
    with pytest.raises(InvalidParamError, match=err_msg):
        engine.anonymize(original_text, [analyzer_result], {})


@pytest.mark.parametrize(
    # fmt: off
    "anonymizers, result_text",
    [
        ({"number": OperatorConfig("fake")}, "Invalid operator class 'fake'."),
    ],
    # fmt: on
)
def test_given_invalid_json_for_anonymizers_then_we_fail(anonymizers, result_text):
    with pytest.raises(InvalidParamError, match=result_text):
        AnonymizerEngine().anonymize(
            "this is my text", [RecognizerResult("number", 0, 4, 0)], anonymizers
        )


def test_given_several_results_then_we_filter_them_and_get_correct_mocked_result():
    analyzer_results = [
        RecognizerResult(start=48, end=57, score=0.55, entity_type="SSN"),
        RecognizerResult(start=24, end=32, score=0.6, entity_type="FULL_NAME"),
        RecognizerResult(start=24, end=28, score=0.9, entity_type="FIRST_NAME"),
        RecognizerResult(start=29, end=32, score=0.6, entity_type="LAST_NAME"),
        RecognizerResult(start=24, end=30, score=0.8, entity_type="NAME"),
        RecognizerResult(start=18, end=32, score=0.8, entity_type="BLA"),
        RecognizerResult(start=23, end=35, score=0.8, entity_type="BLA"),
        RecognizerResult(start=28, end=36, score=0.8, entity_type="BLA"),
        RecognizerResult(start=48, end=57, score=0.95, entity_type="PHONE_NUMBER"),
    ]

    operator_config = OperatorConfig("replace", {})
    operator_config.operator_name = ""
    engine = AnonymizerEngine()
    engine._operate = _operate
    result = engine.anonymize(
        "hello world, my name is Jane Doe. My number is: 034453334",
        analyzer_results,
        {"DEFAULT": operator_config},
    )

    assert result.text == "Number: I am your new text!"
    assert len(result.items) == 1
    assert result.items[0].operator == "hash"
    assert result.items[0].entity_type == "type"
    assert result.items[0].start == 0
    assert result.items[0].end == 35
    assert result.items[0].text == "text"


@pytest.mark.parametrize(
    # fmt: off
    "text, analyzer_results, expected",
    [
        (
            "My name is David Jones",
            [
                RecognizerResult(start=11, end=16, score=0.8, entity_type="PERSON"),
                RecognizerResult(start=17, end=22, score=0.8, entity_type="PERSON"),
            ],
            EngineResult(
                text="My name is BIP",
                items=[
                    OperatorResult(11, 14, "PERSON", "BIP", "replace"),
                ]
            )
        ),
        (
            "My name is David   Jones",
            [
                RecognizerResult(start=11, end=16, score=0.8, entity_type="PERSON"),
                RecognizerResult(start=19, end=24, score=0.8, entity_type="PERSON"),
            ],
            EngineResult(
                text="My name is BIP",
                items=[
                    OperatorResult(11, 14, "PERSON", "BIP", "replace"),
                ]
            )
        ),
        (
            "My name is David \nJones",
            [
                RecognizerResult(start=11, end=16, score=0.8, entity_type="PERSON"),
                RecognizerResult(start=18, end=23, score=0.8, entity_type="PERSON"),
            ],
            EngineResult(
                text="My name is BIP \nBIP",
                items=[
                    OperatorResult(11, 14, "PERSON", "BIP", "replace"),
                    OperatorResult(16, 19, "PERSON", "BIP", "replace"),
                ]
            )
        ),
        (
            "My name is David  \nJones",
            [
                RecognizerResult(start=11, end=16, score=0.8, entity_type="PERSON"),
                RecognizerResult(start=19, end=24, score=0.8, entity_type="PERSON"),
            ],
            EngineResult(
                text="My name is BIP  \nBIP",
                items=[
                    OperatorResult(11, 14, "PERSON", "BIP", "replace"),
                    OperatorResult(17, 20, "PERSON", "BIP", "replace"),
                ]
            )
        ),
        (
            "My name is Jones, David",
            [
                RecognizerResult(start=11, end=16, score=0.8, entity_type="PERSON"),
                RecognizerResult(start=18, end=23, score=0.8, entity_type="PERSON"),
            ],
            EngineResult(
                text="My name is BIP, BIP",
                items=[
                    OperatorResult(11, 14, "PERSON", "BIP", "replace"),
                    OperatorResult(16, 19, "PERSON", "BIP", "replace"),
                ]
            )
        ),
        (
            "The phone book said: Jones 212-555-5555",
            [
                RecognizerResult(start=21, end=26, score=0.8, entity_type="PERSON"),
                RecognizerResult(
                    start=27, end=39, score=0.8, entity_type="PHONE NUMBER"
                ),
            ],
            EngineResult(
                text="The phone book said: BIP BEEP",
                items=[
                    OperatorResult(21, 24, "PERSON", "BIP", "replace"),
                    OperatorResult(25, 29, "PHONE NUMBER", "BEEP", "replace"),
                ]
            )
        ),
    ]
    # fmt: on
)
def test_given_sorted_analyzer_results_merge_entities_separated_by_white_space(
    text, analyzer_results, expected
):
    engine = AnonymizerEngine()
    result = engine.anonymize(
        text,
        analyzer_results,
        operators={
            "PERSON": OperatorConfig("replace", {"new_value": "BIP"}),
            "PHONE NUMBER": OperatorConfig("replace", {"new_value": "BEEP"}),
        },
    )
    assert result.text == expected.text
    assert sorted(result.items) == sorted(expected.items)


def test_given_analyzer_result_input_then_it_is_not_mutated():
    engine = AnonymizerEngine()
    text = "Jane Doe is a person"
    original_analyzer_results = [
        RecognizerResult(start=0, end=4, entity_type="PERSON", score=1.0),
        RecognizerResult(start=5, end=8, entity_type="PERSON", score=1.0),
    ]
    copy_analyzer_results = copy.deepcopy(original_analyzer_results)
    engine.anonymize(
        text,
        original_analyzer_results
    )
    # Compare length of the lists first and then values of contained objects
    assert len(original_analyzer_results) == len(copy_analyzer_results)
    for original_result, copy_result in zip(
        original_analyzer_results, copy_analyzer_results
    ):
        assert original_result == copy_result


def test_given_unsorted_input_then_merged_correctly():
    engine = AnonymizerEngine()
    text = "Jane Doe is a person"
    # Let's say the analyzer has detected 'Jane' and 'Doe' as separate people,
    # and the results are not sorted by start, end.
    original_analyzer_results = [
        RecognizerResult(start=5, end=8, entity_type="PERSON", score=1.0),
        RecognizerResult(start=0, end=4, entity_type="PERSON", score=1.0),
    ]
    # The whitespace merger should correctly merge the separate entities during the
    # anonymization process.
    anonymizer_result = engine.anonymize(
        text,
        original_analyzer_results
    )
    assert anonymizer_result.text == "<PERSON> is a person"


def _operate(
    text: str,
    pii_entities: List[PIIEntity],
    operators_metadata: Dict[str, OperatorConfig],
    operator_type: OperatorType,
    **operator_kwargs,
) -> EngineResult:
    assert text == "hello world, my name is Jane Doe. My number is: 034453334"
    assert len(pii_entities) == 2
    expected = [
        RecognizerResult(start=48, end=57, entity_type="PHONE_NUMBER", score=0.95),
        RecognizerResult(start=18, end=36, entity_type="BLA", score=0.8),
    ]
    assert all(elem in pii_entities for elem in expected)
    assert len(operators_metadata) == 1
    assert operators_metadata["DEFAULT"]
    assert operator_type == OperatorType.Anonymize
    return EngineResult(
        "Number: I am your new text!", [OperatorResult(0, 35, "type", "text", "hash")]
    )

# ---------------------------------------------------------------------------
# Tests for merge_entities_with_spaces parameter (issue #1932)
# ---------------------------------------------------------------------------


def test_when_merge_spaces_is_default_then_adjacent_entities_are_merged():
    """Default (True) still merges adjacent same-type entities separated by spaces."""
    engine = AnonymizerEngine()
    text = "Jane Doe is a person"
    analyzer_results = [
        RecognizerResult(start=0, end=4, entity_type="PERSON", score=1.0),
        RecognizerResult(start=5, end=8, entity_type="PERSON", score=1.0),
    ]
    result = engine.anonymize(text, analyzer_results)
    assert result.text == "<PERSON> is a person"
    assert len(result.items) == 1


def test_when_merge_spaces_is_false_then_each_entity_is_anonymized_separately():
    """With merge_entities_with_spaces=False, each entity is anonymized on its own."""
    engine = AnonymizerEngine()
    text = "Jane Doe is a person"
    analyzer_results = [
        RecognizerResult(start=0, end=4, entity_type="PERSON", score=1.0),
        RecognizerResult(start=5, end=8, entity_type="PERSON", score=1.0),
    ]
    result = engine.anonymize(
        text, analyzer_results, merge_entities_with_spaces=False
    )
    assert result.text == "<PERSON> <PERSON> is a person"
    assert len(result.items) == 2


def test_when_merge_spaces_is_false_then_space_separated_emails_are_all_anonymized():
    """Reproduces issue #1925: space-separated emails must all be anonymized."""
    engine = AnonymizerEngine()
    text = "a@x.com b@y.com c@z.com"
    analyzer_results = [
        RecognizerResult(start=0, end=7, entity_type="EMAIL_ADDRESS", score=1.0),
        RecognizerResult(start=8, end=15, entity_type="EMAIL_ADDRESS", score=1.0),
        RecognizerResult(start=16, end=23, entity_type="EMAIL_ADDRESS", score=1.0),
    ]
    merged_result = engine.anonymize(text, analyzer_results)
    assert merged_result.text == "<EMAIL_ADDRESS>"
    assert len(merged_result.items) == 1

    separate_result = engine.anonymize(
        text, analyzer_results, merge_entities_with_spaces=False
    )
    assert separate_result.text == "<EMAIL_ADDRESS> <EMAIL_ADDRESS> <EMAIL_ADDRESS>"
    assert len(separate_result.items) == 3


def test_when_merge_spaces_is_false_then_different_entity_types_are_unaffected():
    """Disabling merge must not change behavior for different entity types."""
    engine = AnonymizerEngine()

    # Two different entity types separated only by a space should both be anonymized
    text = "5551234567 user@example.com"
    analyzer_results = [
        RecognizerResult(start=0, end=10, entity_type="PHONE_NUMBER", score=1.0),
        RecognizerResult(start=11, end=27, entity_type="EMAIL_ADDRESS", score=1.0),
    ]
    result = engine.anonymize(
        text, analyzer_results, merge_entities_with_spaces=False
    )
    assert result.text == "<PHONE_NUMBER> <EMAIL_ADDRESS>"
    assert len(result.items) == 2


def test_when_merge_spaces_is_true_then_tabs_and_newlines_are_not_merged():
    """Merging only applies to spaces, not tabs or newlines."""
    engine = AnonymizerEngine()
    text = "a@x.com\tb@y.com\nc@z.com"
    analyzer_results = [
        RecognizerResult(start=0, end=7, entity_type="EMAIL_ADDRESS", score=1.0),
        RecognizerResult(start=8, end=15, entity_type="EMAIL_ADDRESS", score=1.0),
        RecognizerResult(start=16, end=23, entity_type="EMAIL_ADDRESS", score=1.0),
    ]
    result = engine.anonymize(text, analyzer_results)
    assert result.text == "<EMAIL_ADDRESS>\t<EMAIL_ADDRESS>\n<EMAIL_ADDRESS>"
    assert len(result.items) == 3
