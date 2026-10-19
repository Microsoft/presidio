"""Check that streamed output does not depend on where the stream was split.

Run from this folder: pytest test_streaming_anonymizer.py
"""

import pytest
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from streaming_anonymizer import SegmentTooLongError, StreamingAnonymizer

TEXTS = [
    "Sure. You can reach Jane Doe at jane.doe@example.com or on 212-555-0147.\n"
    "Anything else?",
    "The card on file is 4111 1111 1111 1111! Logins came from 192.168.10.24 today.",
]
RAW_VALUES = [
    "jane.doe@example.com",
    "212-555-0147",
    "4111 1111 1111 1111",
    "192.168.10.24",
]


@pytest.fixture(scope="module")
def engines():
    """Load the analyzer and anonymizer once for all tests."""
    return AnalyzerEngine(), AnonymizerEngine()


def run(engines, deltas, **kwargs):
    """Stream deltas through a new StreamingAnonymizer and join the output."""
    streaming = StreamingAnonymizer(*engines, **kwargs)
    return "".join(streaming.feed(d) for d in deltas) + streaming.flush()


def two_part_splits(text):
    """Return text split in two at every position."""
    return [[text[:i], text[i:]] for i in range(1, len(text))]


def fixed_size_splits(text):
    """Return text split into equal deltas, for every delta size."""
    return [
        [text[i : i + size] for i in range(0, len(text), size)]
        for size in range(1, len(text))
    ]


@pytest.mark.parametrize("text", TEXTS)
def test_reference_masks_every_value(engines, text):
    """The whole text, sent as one delta, has every value masked."""
    reference = run(engines, [text])
    for value in RAW_VALUES:
        assert value not in reference


@pytest.mark.parametrize("text", TEXTS)
def test_output_is_the_same_at_every_split(engines, text):
    """Every way of splitting the text gives the same output."""
    expected = run(engines, [text])
    for deltas in two_part_splits(text) + fixed_size_splits(text):
        assert run(engines, deltas) == expected, deltas


def test_per_delta_analysis_fails_the_same_check(engines):
    """Analyzing each delta on its own gives different output at some splits."""
    analyzer, anonymizer = engines

    def per_delta(deltas):
        return "".join(
            anonymizer.anonymize(
                text=d, analyzer_results=analyzer.analyze(text=d, language="en")
            ).text
            for d in deltas
        )

    text = TEXTS[0]
    expected = run(engines, [text])
    failures = [d for d in two_part_splits(text) if per_delta(d) != expected]
    assert failures


def test_long_segment_fails_closed(engines):
    """A segment over the limit raises, whether it arrives whole or in parts."""
    text = "x" * 50 + " jane.doe@example.com"
    for deltas in [[text], [text[:30], text[30:]]]:
        with pytest.raises(SegmentTooLongError):
            run(engines, deltas, max_segment_chars=40)


def test_oversized_delta_stays_within_limit(engines):
    """A single delta far over the limit never grows the held text past it."""
    streaming = StreamingAnonymizer(*engines, max_segment_chars=40)
    with pytest.raises(SegmentTooLongError):
        streaming.feed("x" * 10_000)
    assert len(streaming._held) <= 41


def test_oversized_delta_of_short_segments(engines):
    """A delta over the limit made of short segments is anonymized normally."""
    text = TEXTS[0] * 3
    expected = run(engines, [text])
    assert run(engines, [text], max_segment_chars=80) == expected


@pytest.mark.parametrize("limit", [0, -1])
def test_limit_below_one_is_rejected(engines, limit):
    """A limit below 1 is rejected instead of looping forever in feed."""
    with pytest.raises(ValueError):
        StreamingAnonymizer(*engines, max_segment_chars=limit)
