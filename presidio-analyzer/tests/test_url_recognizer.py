import time

import pytest
import regex as re

from tests import assert_result
from presidio_analyzer.predefined_recognizers import UrlRecognizer
from presidio_analyzer.predefined_recognizers.generic.url_recognizer import (
    load_tlds,
    tlds_to_regex,
)


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
        ('"https://presidio.dataprivacystack.org/"', 1, ((0, 40),), 0.6),
        ("'https://presidio.dataprivacystack.org/'", 1, ((0, 40),), 0.6),

        # Brand TLDs, incl. ones that share a prefix with a shorter TLD
        # (.bank/.ba, .barclays/.bar, .americanexpress/.am)
        ("https://www.chase.bank/login", 1, ((0, 28),), 0.6,),
        ("chase.bank", 1, ((0, 10),), 0.5,),
        ("https://home.barclays", 1, ((0, 21),), 0.6,),
        ("www.americanexpress", 1, ((0, 19),), 0.5,),
        ("wellsfargo.insurance", 1, ((0, 20),), 0.5,),
        ("navy.creditunion", 1, ((0, 16),), 0.5,),
        ("www.microsoft", 1, ((0, 13),), 0.5,),
        ("'www.microsoft'", 1, ((0, 15),), 0.5,),

        # A TLD must end the host, so a trailing non-TLD label is excluded
        ("Visit www.example.com.Then call", 1, ((6, 21),), 0.5,),

        # Invalid URLs
        ("http://microsoft", 0, (), 0),
        ("archive.tar.gz", 0, (), 0),
        ("nosuch.invalidtld", 0, (), 0),
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

def test_when_trie_regex_then_matches_exactly_the_tld_list():
    tlds = load_tlds()
    anchored = re.compile("^(?:" + tlds_to_regex(tlds) + ")$")
    tld_set = set(tlds)

    assert all(anchored.match(tld) for tld in tlds)
    # Every proper prefix and one-character extension of a real TLD must only
    # match if it is itself a TLD - this is the .bank/.ba failure mode.
    for tld in tlds:
        for candidate in [tld[:i] for i in range(1, len(tld))] + [
            tld + char for char in "abz0-"
        ]:
            assert (anchored.match(candidate) is not None) == (candidate in tld_set), (
                candidate
            )
