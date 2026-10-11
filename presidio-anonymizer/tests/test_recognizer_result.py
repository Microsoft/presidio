import pytest

from presidio_anonymizer.entities import InvalidParamError, RecognizerResult


@pytest.mark.parametrize(
    # fmt: off
    "start, end",
    [
        (0, 10),
        (2, 8),
        (0, 8),
        (0, 10),
    ],
    # fmt: on
)
def test_given_recognizer_results_then_one_contains_another(start, end):
    first = create_recognizer_result("entity", 0, 0, 10)
    second = create_recognizer_result("entity", 0, start, end)

    assert first.contains(second)


@pytest.mark.parametrize(
    # fmt: off
    "start, end",
    [
        (4, 10),
        (5, 11),
        (0, 5),
        (0, 6),
    ],
    # fmt: on
)
def test_given_recognizer_result_then_they_do_not_contain_one_another(start, end):
    first = create_recognizer_result("entity", 0, 5, 10)
    second = create_recognizer_result("entity", 0, start, end)

    assert not first.contains(second)


def test_given_recognizer_results_with_same_indices_then_indices_are_equal():
    first = create_recognizer_result("entity", 0, 0, 10)
    second = create_recognizer_result("entity", 0, 0, 10)

    assert first.equal_indices(second)


@pytest.mark.parametrize(
    # fmt: off
    "start, end",
    [
        (4, 10),
        (5, 11),
        (0, 5),
        (0, 6),
    ],
    # fmt: on
)
def test_given_recognizer_results_with_different_indices_then_indices_are_not_equal(
    start, end
):
    first = create_recognizer_result("entity", 0, 5, 10)
    second = create_recognizer_result("entity", 0, start, end)

    assert not first.equal_indices(second)


@pytest.mark.parametrize(
    # fmt: off
    "start, end, err",
    [
        ("0", 10,
         "Invalid parameter value for start. Expecting 'number', but got 'string'."),
        (0, "10",
         "Invalid parameter value for end. Expecting 'number', but got 'string'."),
    ],
    # fmt: on
)
def test_given_invalid_string_start_instead_of_int_then_we_fail(start, end, err):
    with pytest.raises(InvalidParamError, match=err):
        create_recognizer_result("bla", 0.2, start, end)


def test_given_identical_recognizer_results_then_they_are_equal():
    first = create_recognizer_result("bla", 0.2, 0, 10)
    second = create_recognizer_result("bla", 0.2, 0, 10)

    assert first == second


@pytest.mark.parametrize(
    # fmt: off
    "entity_type, score, start, end",
    [
        ("bla", 0.2, 4, 10),
        ("changed", 0.2, 0, 10),
        ("bla", 0.2, 0, 11),
        ("bla", 0.3, 0, 10),
    ],
    # fmt: on
)
def test_given_different_recognizer_result_then_they_are_not_equal(
    entity_type, score, start, end
):
    first = create_recognizer_result("bla", 0.2, 0, 10)
    second = create_recognizer_result(entity_type, score, start, end)

    assert first != second


def test_given_recognizer_result_then_their_hash_is_equal():
    first = create_recognizer_result("entity", 0, 0, 10)
    second = create_recognizer_result("entity", 0, 0, 10)

    assert first.__hash__() == second.__hash__()


@pytest.mark.parametrize(
    # fmt: off
    "entity_type, score, start, end",
    [
        ("bla", 0.2, 4, 10),
        ("changed", 0.2, 0, 10),
        ("bla", 0.2, 0, 11),
        ("bla", 0.3, 0, 10),
    ],
    # fmt: on
)
def test_given_different_recognizer_results_then_hash_is_not_equal(
    entity_type, score, start, end
):
    first = create_recognizer_result("bla", 0.2, 0, 10)
    second = create_recognizer_result(entity_type, score, start, end)

    assert first.__hash__() != second.__hash__()


@pytest.mark.parametrize(
    # fmt: off
    "entity_type, score, start, end",
    [
        ("bla", 0.2, 0, 10),
        ("changed", 0.2, 2, 10),
        ("bla", 0.3, 0, 11),
        ("bla", 0.1, 0, 10),
    ],
    # fmt: on
)
def test_given_recognizer_results_with_conflicting_indices_then_there_is_a_conflict(
    entity_type, score, start, end
):
    first = create_recognizer_result("bla", 0.2, 2, 10)
    second = create_recognizer_result(entity_type, score, start, end)

    assert first.has_conflict(second)


@pytest.mark.parametrize(
    # fmt: off
    "entity_type, score, start, end",
    [
        ("bla", 0.2, 3, 10),
        ("changed", 0.1, 2, 10),
        ("bla", 0.3, 0, 9),
    ],
    # fmt: on
)
def test_given_recognizer_results_with_no_conflicting_indices_then_there_is_no_conflict(
    entity_type, score, start, end
):
    first = create_recognizer_result("bla", 0.2, 2, 10)
    second = create_recognizer_result(entity_type, score, start, end)

    assert not first.has_conflict(second)


@pytest.mark.parametrize(
    # fmt: off
    "score, expected_conflict",
    [
        (0.1, True),
        (0.2, True),
        (0.3, False),
    ],
    # fmt: on
)
def test_given_contained_result_then_conflict_depends_on_score(
    score, expected_conflict
):
    contained = create_recognizer_result("bla", score, 2, 10)
    containing = create_recognizer_result("changed", 0.2, 0, 12)

    assert contained.has_conflict(containing, True) == expected_conflict
    # The default keeps dropping the contained result whatever its score.
    assert contained.has_conflict(containing)


@pytest.mark.parametrize(
    # fmt: off
    "entity_type, score, start, end",
    [
        ("bla", 0.2, 0, 10),
        ("changed", 0.2, 2, 10),
        ("bla", 0.3, 0, 11),
    ],
    # fmt: on
)
def test_given_equal_or_higher_scored_container_then_there_is_still_a_conflict(
    entity_type, score, start, end
):
    first = create_recognizer_result("bla", 0.2, 2, 10)
    second = create_recognizer_result(entity_type, score, start, end)

    assert first.has_conflict(second, True)


@pytest.mark.parametrize(
    # fmt: off
    "request_json, result_text",
    [
        ({}, "Invalid input, result must contain start",),
        ({
             "end": 32,
             "score": 0.8,
             "entity_type": "NUMBER"
         }, "Invalid input, result must contain start",),
        ({
             "start": 28,
             "score": 0.8,
             "entity_type": "NUMBER"
         }, "Invalid input, result must contain end",),
        ({
             "start": 28,
             "end": 32,
             "entity_type": "NUMBER"
         }, "Invalid input, analyzer result must contain score",),
        ({
             "start": 28,
             "end": 32,
             "score": 0.8,
         }, "Invalid input, result must contain entity_type",),
    ],
    # fmt: on
)
def test_given_json_for_creating_recognizer_result_without_text_then_creation_fails(
    request_json, result_text
):
    with pytest.raises(InvalidParamError) as e:
        RecognizerResult.from_json(request_json)
    assert result_text == e.value.err_msg


def test_given_valid_json_for_creating_recognizer_result_then_creation_is_successful():
    data = create_recognizer_result("NUMBER", 0.8, 0, 32)
    assert data.start == 0
    assert data.end == 32
    assert data.score == 0.8
    assert data.entity_type == "NUMBER"


@pytest.mark.parametrize(
    # fmt: off
    "start, end",
    [
        (4, 10),
        (4, 9),
        (0, 2),
        (5, 9),
    ],
    # fmt: on
)
def test_given_recognizer_results_then_one_is_greater_then_another(start, end):
    first = create_recognizer_result("entity", 0, 5, 10)
    second = create_recognizer_result("entity", 0, start, end)

    assert first.__gt__(second)


@pytest.mark.parametrize(
    # fmt: off
    "start, end",
    [
        (5, 10),
        (6, 12),
        (6, 7),
    ],
    # fmt: on
)
def test_given_recognizer_result_then_one_is_not_greater_then_another(start, end):
    first = create_recognizer_result("entity", 0, 5, 10)
    second = create_recognizer_result("entity", 0, start, end)

    assert not first.__gt__(second)


def test_given_endpoint_larger_then_start_point_then_we_fail():
    with pytest.raises(InvalidParamError) as e:
        create_recognizer_result("entity", 0, 10, 0)
    assert (
        e.value.err_msg == "Invalid input, start index '10' "
        "must be smaller than end index '0'"
    )


def test_given_endpoint_equal_to_start_point_then_we_succeed():
    assert create_recognizer_result("entity", 0, 0, 0)


@pytest.mark.parametrize(
    # fmt: off
    "start, end",
    [
        (-1, 10),
        (6, -12),
        (-2, -2),
    ],
    # fmt: on
)
def test_given_negative_start_or_endpoint_then_we_fail(start, end):
    with pytest.raises(
        InvalidParamError,
        match="Invalid input, result start and end must be positive",
    ):
        create_recognizer_result("entity", 0, start, end)


def create_recognizer_result(entity_type: str, score: float, start: int, end: int):
    data = {"entity_type": entity_type, "score": score, "start": start, "end": end}
    return RecognizerResult.from_json(data)
