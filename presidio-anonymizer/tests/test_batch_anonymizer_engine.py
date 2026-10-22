import pytest

from presidio_anonymizer import BatchAnonymizerEngine
from presidio_anonymizer.entities import (
    RecognizerResult,
    DictRecognizerResult,
    OperatorConfig,
)


@pytest.fixture(scope="module")
def engine():
    return BatchAnonymizerEngine()


@pytest.fixture(scope="module")
def texts():
    return ["John", "Jill", "Jack"]


@pytest.fixture(scope="module")
def recognizer_results_list(texts):
    return [[RecognizerResult("PERSON", 0, 4, 0.85)] for _ in range(len(texts))]


@pytest.fixture(scope="module")
def analyzer_results(texts, recognizer_results_list):
    return [
        DictRecognizerResult(
            key="name", value=texts, recognizer_results=recognizer_results_list
        )
    ]


def test_given_analyzer_result_we_anonymize_dict_correctly(engine, analyzer_results):
    anonymize_results = engine.anonymize_dict(analyzer_results)
    assert anonymize_results == {"name": ["<PERSON>", "<PERSON>", "<PERSON>"]}


def test_given_analyzer_result_we_anonymize_list_correctly(
    engine, texts, recognizer_results_list
):
    # new list that will reuse texts  and another inner list with random value
    # should be ['John', 'Jill', 'Jack', ['random', 123, True]]
    new_texts = texts + [["random", 123, True]]
    new_recognizer_results_list = recognizer_results_list + [[]]
    anonymize_results = engine.anonymize_list(
        texts=new_texts, recognizer_results_list=new_recognizer_results_list
    )
    assert anonymize_results == [
        "<PERSON>",
        "<PERSON>",
        "<PERSON>",
        ["random", 123, True],
    ]


def test_given_empty_recognizers_than_we_return_text_unchanged(engine, texts):
    empty_analyzer_results = [
        DictRecognizerResult(key="name", value=texts, recognizer_results=[])
    ]
    anonymize_results = engine.anonymize_dict(empty_analyzer_results)
    assert anonymize_results == {"name": ["John", "Jill", "Jack"]}


def test_given_complex_analyzer_result_we_anonymize_dict_correctly(
    engine, texts, recognizer_results_list
):
    analyzer_results = [
        DictRecognizerResult(
            key="name", value=texts, recognizer_results=recognizer_results_list
        ),
        DictRecognizerResult(
            key="comments",
            value=[
                "called him yesterday to confirm he requested to call back in 2 days",
                "accepted the offer license number AC432223",
                "need to call him at phone number 212-555-5555",
            ],
            recognizer_results=[
                [
                    RecognizerResult("DATE_TIME", 11, 20, 0.85),
                    RecognizerResult("DATE_TIME", 61, 67, 0.85),
                ],
                [RecognizerResult("US_DRIVER_LICENSE", 34, 42, 0.6499999999999999)],
                [RecognizerResult("PHONE_NUMBER", 33, 45, 0.75)],
            ],
        ),
    ]

    anonymize_results = engine.anonymize_dict(analyzer_results)
    assert anonymize_results == {
        "name": ["<PERSON>", "<PERSON>", "<PERSON>"],
        "comments": [
            "called him <DATE_TIME> to confirm he requested to call back in "
            "<DATE_TIME>",
            "accepted the offer license number <US_DRIVER_LICENSE>",
            "need to call him at phone number <PHONE_NUMBER>",
        ],
    }


def test_anonymize_dict_with_dict_value(engine):
    analyzer_results = [
        DictRecognizerResult(
            key="customer",
            value={"name": "John"},
            recognizer_results=[
                DictRecognizerResult(
                    key="name",
                    value="John",
                    recognizer_results=[RecognizerResult("PERSON", 0, 4, 0.85)],
                )
            ],
        )
    ]
    anonymize_results = engine.anonymize_dict(analyzer_results)
    assert anonymize_results == {"customer": {"name": "<PERSON>"}}


def test_anonymize_dict_with_other_value(engine):
    analyzer_results = [
        DictRecognizerResult(key="id", value=123, recognizer_results=[])
    ]
    anonymize_results = engine.anonymize_dict(analyzer_results)
    assert anonymize_results == {"id": 123}


@pytest.mark.parametrize(
    "value, result, expected",
    [
        (
            4111111111111111,
            RecognizerResult("CREDIT_CARD", 0, 16, 1.0),
            "<CREDIT_CARD>",
        ),
        (
            2125551234.0,
            RecognizerResult("PHONE_NUMBER", 0, 10, 0.75),
            "<PHONE_NUMBER>.0",
        ),
        (True, RecognizerResult("FLAG", 0, 4, 0.5), "<FLAG>"),
        (0, RecognizerResult("ID", 0, 1, 0.5), "<ID>"),
    ],
)
def test_when_scalar_dict_value_has_results_then_it_is_anonymized(
    engine, value, result, expected
):
    analyzer_results = [
        DictRecognizerResult(key="field", value=value, recognizer_results=[result])
    ]
    anonymize_results = engine.anonymize_dict(analyzer_results)
    assert anonymize_results == {"field": expected}


@pytest.mark.parametrize("value", [1.5, True, False, 0])
def test_when_scalar_dict_value_has_no_results_then_its_type_is_kept(engine, value):
    analyzer_results = [
        DictRecognizerResult(key="field", value=value, recognizer_results=[])
    ]
    anonymize_results = engine.anonymize_dict(analyzer_results)
    assert type(anonymize_results["field"]) is type(value)
    assert anonymize_results["field"] == value


def test_when_scalar_and_list_hold_same_card_then_both_are_anonymized(engine):
    card = RecognizerResult("CREDIT_CARD", 0, 16, 1.0)
    analyzer_results = [
        DictRecognizerResult(
            key="customer",
            value={"card": 4111111111111111},
            recognizer_results=[
                DictRecognizerResult(
                    key="card", value=4111111111111111, recognizer_results=[card]
                )
            ],
        ),
        DictRecognizerResult(
            key="cards", value=[4111111111111111], recognizer_results=[[card]]
        ),
    ]
    anonymize_results = engine.anonymize_dict(analyzer_results)
    assert anonymize_results == {
        "customer": {"card": "<CREDIT_CARD>"},
        "cards": ["<CREDIT_CARD>"],
    }


def test_when_scalar_dict_value_uses_custom_operator_then_it_gets_the_digits(engine):
    analyzer_results = [
        DictRecognizerResult(
            key="card",
            value=4111111111111111,
            recognizer_results=[RecognizerResult("CREDIT_CARD", 12, 16, 1.0)],
        )
    ]
    anonymize_results = engine.anonymize_dict(
        analyzer_results,
        operators={"DEFAULT": OperatorConfig("custom", {"lambda": lambda x: f"*{x}"})},
    )
    assert anonymize_results == {"card": "411111111111*1111"}


def test_given_custom_anonymizer_we_anonymize_dict_correctly(engine, analyzer_results):
    anonymizer_config = OperatorConfig("custom", {"lambda": lambda x: f"<ENTITY: {x}>"})
    anonymize_results = engine.anonymize_dict(
        analyzer_results, operators={"DEFAULT": anonymizer_config}
    )
    assert anonymize_results == {
        "name": ["<ENTITY: John>", "<ENTITY: Jill>", "<ENTITY: Jack>"]
    }
