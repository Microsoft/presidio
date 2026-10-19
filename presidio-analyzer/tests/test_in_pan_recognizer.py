import time

import pytest

from tests import assert_result
from presidio_analyzer.predefined_recognizers import InPanRecognizer


@pytest.fixture(scope="module")
def recognizer():
    return InPanRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["IN_PAN"]


@pytest.mark.parametrize(
    "text, expected_len, expected_position, expected_score",
    [
        # fmt: off
        ("AAASA1111R", 1, (0,10), 0.1) ,
        ("ABCPD1234Z", 1, (0, 10), 0.5),
        ("ABCND1234Z", 1, (0, 10), 0.1),
        ("A1111DFSFS", 1, (0,10),0.01),
        ("ABCD1234",0,(),(),),
        ("My PAN number is ABBPM4567S with a lot of text beyond it", 1, (17,27),.5),
        # fmt: on
    ],
)
def test_when_pan_in_text_then_all_pans_found(
    text,
    expected_len,
    expected_position,
    expected_score,
    recognizer,
    entities,
):
    results = recognizer.analyze(text, entities)
    print(results)

    assert len(results) == expected_len
    if results:
        assert_result(
            results[0],
            entities[0],
            expected_position[0],
            expected_position[1],
            expected_score,
        )


def test_low_confidence_pan_with_embedded_digits_still_detected(recognizer, entities):
    # The low-confidence pattern keeps matching a 10-char token that carries a
    # letter and a four-digit run; scoping the lookaheads to the token class
    # leaves this detection unchanged.
    results = recognizer.analyze("A1111DFSFS", entities)
    assert len(results) == 1
    assert_result(results[0], entities[0], 0, 10, 0.01)


def test_low_confidence_pattern_does_not_backtrack(recognizer, entities):
    # The low-confidence pattern used `.*?` lookaheads that rescanned the whole
    # remaining text at every word boundary, so a long boundary-rich string with
    # no four-digit run cost time quadratic in its length. Matching must now be
    # linear and finish well within the regex timeout.
    text = "a " * 50000
    start = time.perf_counter()
    results = recognizer.analyze(text, entities)
    elapsed = time.perf_counter() - start
    assert results == []
    assert elapsed < 10
