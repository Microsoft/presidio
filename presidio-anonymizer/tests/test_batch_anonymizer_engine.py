import pytest

from presidio_anonymizer import BatchAnonymizerEngine
from presidio_anonymizer.entities import (
    DictRecognizerResult,
    InvalidParamError,
    OperatorConfig,
    RecognizerResult,
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


def test_given_custom_anonymizer_we_anonymize_dict_correctly(engine, analyzer_results):
    anonymizer_config = OperatorConfig("custom", {"lambda": lambda x: f"<ENTITY: {x}>"})
    anonymize_results = engine.anonymize_dict(
        analyzer_results, operators={"DEFAULT": anonymizer_config}
    )
    assert anonymize_results == {
        "name": ["<ENTITY: John>", "<ENTITY: Jill>", "<ENTITY: Jack>"]
    }


def test_given_fewer_recognizer_results_anonymize_list_raises_invalid_param_error(engine):
    texts = ["John", "Jill"]
    recognizer_results_list = [[RecognizerResult("PERSON", 0, 4, 0.85)]]
    with pytest.raises(
        InvalidParamError,
        match=r"Invalid input, the number of texts \(2\) must match the number of recognizer results \(1\)\.",
    ):
        engine.anonymize_list(
            texts=texts, recognizer_results_list=recognizer_results_list
        )


def test_given_more_recognizer_results_anonymize_list_raises_invalid_param_error(engine):
    texts = ["John"]
    recognizer_results_list = [
        [RecognizerResult("PERSON", 0, 4, 0.85)],
        [RecognizerResult("PERSON", 0, 4, 0.85)],
    ]
    with pytest.raises(
        InvalidParamError,
        match=r"Invalid input, the number of texts \(1\) must match the number of recognizer results \(2\)\.",
    ):
        engine.anonymize_list(
            texts=texts, recognizer_results_list=recognizer_results_list
        )


def test_given_mismatched_lengths_in_dict_raises_invalid_param_error(engine):
    analyzer_results = [
        DictRecognizerResult(
            key="name",
            value=["John", "Jill", "Jack"],
            recognizer_results=[[RecognizerResult("PERSON", 0, 4, 0.85)]],
        )
    ]
    with pytest.raises(
        InvalidParamError,
        match=r"Invalid input, the number of texts \(3\) must match the number of recognizer results \(1\)\.",
    ):
        engine.anonymize_dict(analyzer_results)
