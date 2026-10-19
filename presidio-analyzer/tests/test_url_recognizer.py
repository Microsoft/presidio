import time

import pytest

from tests import assert_result
from presidio_analyzer.predefined_recognizers import UrlRecognizer


@pytest.fixture(scope="module")
def recognizer():
    return UrlRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["URL"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score",
    [
        # fmt: off
        # Valid URLs
        ("https://www.microsoft.com/", 1, ((0, 26),), 0.6,),
        ("http://www.microsoft.com/", 1, ((0, 25),), 0.6,),
        ("http://www.microsoft.com", 1, ((0, 24),), 0.6,),
        ("http://microsoft.com", 1, ((0, 20),), 0.6,),
        ("http://microsoft.site", 1, ((0, 21),), 0.6,),
        ("http://microsoft.webcam", 1, ((0, 23),), 0.6,),
        ("http://microsoft.vlaanderen", 1, ((0, 27),), 0.6,),
        ("https://webhook.site/a8eedfd6-9d8a-44e0-b0fc-cc7d517db5dc?q=1&b=2", 1, ((0, 65),), 0.6,),
        ("https://www.microsoft.com/store/abc/", 1, ((0, 36),), 0.6,),
        ("microsoft.com", 1, ((0, 13),), 0.5,),
        ("my domains: microsoft.com google.co.il", 2, ((12, 25), (26, 38),), 0.5),
        # Quoted URLs: the surrounding quotes are not part of the URL
        ('"https://presidio.dataprivacystack.org/"', 1, ((1, 39),), 0.6),
        ("'https://presidio.dataprivacystack.org/'", 1, ((1, 39),), 0.6),
        ('"www.example.com"', 1, ((1, 16),), 0.5),
        ('{"website": "https://example.com/profile/42"}', 1, ((13, 43),), 0.6),
        ("<a href='https://example.com/profile/42'>profile</a>", 1, ((9, 39),), 0.6),

        # Invalid URLs
        ("www.microsoft", 0, (), 0),
        ("http://microsoft", 0, (), 0),
        ("'www.microsoft'", 0, (), 0),
        # fmt: on
    ],
)
def test_when_all_urls_then_succeed(
        text, expected_len, expected_positions, expected_score, recognizer, entities
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos) in zip(results, expected_positions):
        assert_result(res, entities[0], st_pos, fn_pos, expected_score)


def test_long_valid_hostname_still_detected(recognizer, entities):
    # The host length bound is the DNS maximum, so a long but well-formed
    # hostname is matched exactly as before.
    host = "a." * 60 + "example"  # 127 chars, far below the 253 limit
    text = f"http://{host}.com/path"
    results = recognizer.analyze(text, entities)
    assert len(results) == 1
    assert_result(results[0], entities[0], 0, len(text), 0.6)


def test_repeated_dot_input_does_not_backtrack(recognizer, entities):
    # The host portion previously used an unbounded run that overlapped the
    # following dot separator, so a long run of dots backtracked quadratically
    # against the TLD alternation. It must now finish in time linear in length.
    text = "." * 3000
    start = time.time()
    results = recognizer.analyze(text, entities)
    elapsed = time.time() - start
    assert results == []
    assert elapsed < 15
