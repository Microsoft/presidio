import pytest
from presidio_analyzer import RecognizerResult, BatchAnalyzerEngine, DictAnalyzerResult


@pytest.fixture(scope="module")
def batch_analyzer_engine_simple(analyzer_engine_simple):
    return BatchAnalyzerEngine(analyzer_engine=analyzer_engine_simple)


# fmt: off
@pytest.mark.parametrize(
    ["texts", "expected_output"],
    [
        (
            ["My name is David", "Call me at 2352351232", "I was born at 1/5/1922"],
            [[], [RecognizerResult(entity_type="PHONE_NUMBER", start=11, end=21, score= 0.4)], []],
        ),
        (
            [1, 2, 3],
            [[], [], []]
        ),
        (
            [1, 2121551234],
            [[], [RecognizerResult(entity_type="PHONE_NUMBER",start=0, end=10, score=0.4)]]
        ),
        (
            ("Hi", "Call me at 2121551234"),
            [[], [RecognizerResult(entity_type="PHONE_NUMBER", start=11, end=21, score= 0.4)]]
        ),
        ([], [])
    ],
)
def test_analyze_iterator_returns_list_of_recognizer_results(
    texts, expected_output, batch_analyzer_engine_simple
):

    results = batch_analyzer_engine_simple.analyze_iterator(texts=texts, language="en", batch_size=2)

    assert len(results) == len(expected_output)
    for result, expected_result in zip(results, expected_output):
        assert result == expected_result
# fmt: on

@pytest.mark.parametrize("n_process, batch_size", [(1,1), (4,2), (2,1)])
def test_analyze_dict_one_value_per_key(batch_analyzer_engine_simple,
                                        n_process,
                                        batch_size):

    d = {
        "url": "https://microsoft.com",
        "emp_id": "XXX",
        "phone": "202-555-1234",
        "misc": "microsoft.com or (202)-555-1234",
    }

    results = batch_analyzer_engine_simple.analyze_dict(input_dict=d, 
                                                        language="en",
                                                        n_process=n_process,
                                                        batch_size=batch_size)
    results = list(results)

    # url
    assert results[0].key == "url"
    assert results[0].value == d["url"]
    assert results[0].recognizer_results[0].entity_type == "URL"
    assert results[0].recognizer_results[0].start == 0
    assert results[0].recognizer_results[0].end == len(d["url"])

    # emp_id
    assert results[1].key == "emp_id"
    assert results[1].value == d["emp_id"]
    assert not results[1].recognizer_results

    # phone
    assert results[2].key == "phone"
    assert results[2].value == d["phone"]
    assert results[2].recognizer_results[0].entity_type == "PHONE_NUMBER"
    assert results[2].recognizer_results[0].start == 0
    assert results[2].recognizer_results[0].end == len(d["phone"])

    # misc
    assert len(results[3].recognizer_results) == 2


def test_analyze_dict_on_simple_dict_with_skipping(batch_analyzer_engine_simple):
    batch = {
        "PHONE_NUMBER": [
            "Call me at 212-124-1244",
            "Phone: 5124421234",
            "Fax number is 5125125125",
        ],
        "URL": ["microsoft.com", "bob.com", "jane.com"],
    }

    results = batch_analyzer_engine_simple.analyze_dict(
        input_dict=batch, keys_to_skip=["URL"], language="en"
    )
    results = list(results)
    phone_results = [result for result in results if result.key == "PHONE_NUMBER"]
    url_results = [result for result in results if result.key == "URL"]
    assert len(phone_results[0].recognizer_results) == 3
    assert url_results[0].key == "URL"  # skipping analysis but returning key, value
    assert url_results[0].value == batch["URL"]
    assert not url_results[0].recognizer_results


def test_analyze_dict_on_simple_dict(batch_analyzer_engine_simple):
    batch = {
        "PHONE_NUMBER": [
            "Call me at 212-124-1244",
            "Phone: 5124421234",
            "Fax number is 5125125125",
        ],
        "URL": ["microsoft.com", "bob.com", "jane.com"],
    }

    results = batch_analyzer_engine_simple.analyze_dict(input_dict=batch, language="en")

    for result in results:
        assert result.key in batch.keys()
        assert len(result.recognizer_results) == 3
        for val, reco_res in zip(result.value, result.recognizer_results):
            assert val in batch[result.key]
            assert isinstance(reco_res, list)
            assert len(reco_res) == 1  # one entity per sentence


def test_analyzer_dict_on_both_scalars_and_list(batch_analyzer_engine_simple):
    input_dict = {
        "a": "My phone is 054-3332111",
        "b": ["My phone is 054-3332111", "My phone is 054-3332111"],
        "c": "A",
    }

    results = list(batch_analyzer_engine_simple.analyze_dict(input_dict, language="en"))

    results_a = [result for result in results if result.key == "a"]
    results_b = [result for result in results if result.key == "b"]
    results_c = [result for result in results if result.key == "c"]

    results_list = [results_a, results_b, results_c]

    for result, key in zip(results_list, input_dict.keys()):
        assert len(result) == 1

    assert len(results_a[0].recognizer_results) == 1
    assert len(results_b[0].recognizer_results) == 2
    assert len(results_c[0].recognizer_results) == 0


def test_analyze_dict_on_nested_dict(batch_analyzer_engine_simple):
    nested_dict = {
        "key_a": {"key_a1": "My phone number is 212-121-1424"},
        "key_b": {"www.abc.com"},
    }

    expected_return = [
        DictAnalyzerResult(
            key="key_a",
            value=nested_dict["key_a"],
            recognizer_results=[
                DictAnalyzerResult(
                    key="key_a1",
                    value=nested_dict["key_a"]["key_a1"],
                    recognizer_results=[
                        RecognizerResult("PHONE_NUMBER", start=19, end=31, score=0.4)
                    ],
                )
            ],
        ),
        DictAnalyzerResult(
            key="key_b",
            value="www.abc.com",
            recognizer_results=[RecognizerResult("URL", start=0, end=11, score=0.5)],
        ),
    ]

    results = batch_analyzer_engine_simple.analyze_dict(
        input_dict=nested_dict, language="en"
    )
    results = list(results)
    for result in results:
        result.recognizer_results = list(result.recognizer_results)

    assert results[0].key == expected_return[0].key
    assert results[0].value == expected_return[0].value

    inner_recognizer_results_actual = (
        results[0].recognizer_results[0].recognizer_results
    )
    inner_recognizer_results_expected = (
        expected_return[0].recognizer_results[0].recognizer_results
    )

    assert (
        inner_recognizer_results_actual[0].start
        == inner_recognizer_results_expected[0].start
    )
    assert (
        inner_recognizer_results_actual[0].end
        == inner_recognizer_results_expected[0].end
    )
    assert (
        inner_recognizer_results_actual[0].entity_type
        == inner_recognizer_results_expected[0].entity_type
    )
    assert (
        inner_recognizer_results_actual[0].score
        == inner_recognizer_results_expected[0].score
    )


def test_analyze_dict_passes_context_to_scalar_values(batch_analyzer_engine_simple):
    input_dict = {
        "scalar": "www.abc.com",
        "list": ["www.abc.com"],
        "nested": {"scalar": "www.abc.com"},
    }

    results = {
        result.key: result.recognizer_results
        for result in batch_analyzer_engine_simple.analyze_dict(
            input_dict=input_dict, language="en", context=["website"]
        )
    }

    # "website" is a UrlRecognizer context word: 0.5 base score + 0.35 boost
    assert results["scalar"][0].score == pytest.approx(0.85)
    assert results["list"][0][0].score == pytest.approx(0.85)
    [nested] = results["nested"]
    assert nested.recognizer_results[0].score == pytest.approx(0.85)


def test_analyze_dict_uses_parent_key_as_context_for_nested_scalar_values(
    batch_analyzer_engine_simple,
):
    input_dict = {"website": {"home": "www.abc.com", "mirrors": ["www.abc.com"]}}

    [website] = batch_analyzer_engine_simple.analyze_dict(
        input_dict=input_dict, language="en"
    )
    nested = {
        result.key: result.recognizer_results for result in website.recognizer_results
    }

    # The parent key "website" is a UrlRecognizer context word
    assert nested["home"][0].score == pytest.approx(0.85)
    assert nested["mirrors"][0][0].score == pytest.approx(0.85)


@pytest.mark.parametrize(
    ["keys", "results_length"],
    ((None, 2), (["key_a"], 1), (["key_a.key_a1"], 1), (["key_c"], 2)),
)
def test_analyze_dict_nested_with_skipping(
    keys, results_length, batch_analyzer_engine_simple
):
    nested_dict = {
        "key_a": {"key_a1": "My phone number is 212-121-1424"},
        "key_b": "www.abc.com",
        "key_c": [3, 4],
    }

    results = batch_analyzer_engine_simple.analyze_dict(
        input_dict=nested_dict, language="en", keys_to_skip=keys
    )
    results = list(results)
    num_results = 0
    for result in results:
        result.recognizer_results = list(result.recognizer_results)
        if result.recognizer_results:
            if isinstance(result.recognizer_results[0], RecognizerResult):
                num_results += len(result.recognizer_results)
            elif isinstance(result.recognizer_results[0], DictAnalyzerResult):
                for res in result.recognizer_results:
                    num_results += len(res.recognizer_results)

    assert num_results == results_length


def test_analyze_list_non_primitive_type_raises_error(batch_analyzer_engine_simple):
    input_dict = {"key": ["1", "2", {"inner_key": "inner_value"}]}

    with pytest.raises(ValueError):
        list(
            batch_analyzer_engine_simple.analyze_dict(
                input_dict=input_dict, language="en"
            )
        )


def test_analyze_dict_with_unknown_object_raises_error(batch_analyzer_engine_simple):
    class J:
        pass

    input_dict = {"key": J()}
    with pytest.raises(ValueError):
        list(
            batch_analyzer_engine_simple.analyze_dict(
                input_dict=input_dict, language="en"
            )
        )


def test_analyze_dict_with_nones_returns_empty_result(batch_analyzer_engine_simple):
    input_list = ["", "2", None, "c"]

    res = batch_analyzer_engine_simple.analyze_iterator(texts=input_list, language="en")
    assert len(res) == len(input_list)
    for r in res:
        assert not r


@pytest.mark.parametrize("n_process, batch_size", [(1,1), (4,2), (2,1)])
def test_batch_analyze_iterator_returns_list_of_recognizer_results(
    batch_analyzer_engine_simple, n_process, batch_size
):
    texts = ["My name is David", "Call me at 2352351232", "I was born at 1/5/1922"]
    expected_output = [[], [RecognizerResult(entity_type="PHONE_NUMBER", start=11, end=21, score= 0.4)], []]

    results = batch_analyzer_engine_simple.analyze_iterator(texts=texts, 
                                                            language="en", 
                                                            batch_size=batch_size,
                                                            n_process=n_process)

    assert len(results) == len(expected_output)
    for result, expected_result in zip(results, expected_output):
        assert result == expected_result
