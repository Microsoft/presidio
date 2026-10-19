"""Anonymize streamed LLM output with Presidio.

A streamed response arrives as text deltas whose boundaries are set by the model
and the network, not by the text. Analyzing each delta on its own misses any
entity split across two deltas, and the first part has already been sent.

StreamingAnonymizer holds text back until a segment boundary, then analyzes and
anonymizes each complete segment. Segment boundaries depend only on the text,
so the output is the same however the stream was split.
"""

import re
from typing import Dict, Iterable, Iterator, List, Optional

from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

# A segment ends after a newline, or after whitespace that follows ".", "!" or "?".
# Both characters of a boundary are known once they arrive, so a boundary never
# moves when more text comes in.
DEFAULT_BOUNDARY = re.compile(r"\n|(?<=[.!?])\s")


class SegmentTooLongError(ValueError):
    """Raised when a segment grows past max_segment_chars without a boundary."""


class StreamingAnonymizer:
    """Anonymize a text stream one complete segment at a time.

    :param analyzer: AnalyzerEngine used on each segment.
    :param anonymizer: AnonymizerEngine used on each segment.
    :param language: Language passed to the analyzer.
    :param entities: Entities to detect. None detects all supported entities.
    :param operators: Anonymizer operators, as in AnonymizerEngine.anonymize.
    :param boundary: Compiled pattern whose match end marks a segment end. Each
        match must be decided by characters up to its end, never by later text.
    :param max_segment_chars: Longest segment held back. A longer one raises
        SegmentTooLongError instead of being released unanalyzed. Must be at
        least 1.
    """

    def __init__(
        self,
        analyzer: AnalyzerEngine,
        anonymizer: AnonymizerEngine,
        language: str = "en",
        entities: Optional[List[str]] = None,
        operators: Optional[Dict[str, OperatorConfig]] = None,
        boundary: re.Pattern = DEFAULT_BOUNDARY,
        max_segment_chars: int = 2000,
    ):
        if max_segment_chars < 1:
            raise ValueError(
                f"max_segment_chars must be at least 1, got {max_segment_chars}"
            )
        self.analyzer = analyzer
        self.anonymizer = anonymizer
        self.language = language
        self.entities = entities
        self.operators = operators
        self.boundary = boundary
        self.max_segment_chars = max_segment_chars
        self._held = ""

    def feed(self, delta: str) -> str:
        """Add a delta and return the anonymized text that is now safe to send."""
        # Take the delta in pieces that fit the limit, so the held text never
        # grows past max_segment_chars + 1, however large a single delta is.
        output = []
        pos = 0
        while pos < len(delta):
            room = self.max_segment_chars + 1 - len(self._held)
            output.append(self._feed_piece(delta[pos : pos + room]))
            pos += room
        return "".join(output)

    def _feed_piece(self, piece: str) -> str:
        self._held += piece
        output = []
        start = 0
        for match in self.boundary.finditer(self._held):
            output.append(self._anonymize_segment(self._held[start : match.end()]))
            start = match.end()
        self._held = self._held[start:]
        if len(self._held) > self.max_segment_chars:
            raise SegmentTooLongError(
                f"No segment boundary in {len(self._held)} characters"
            )
        return "".join(output)

    def flush(self) -> str:
        """Anonymize and return the held text. Call once, when the stream ends."""
        held, self._held = self._held, ""
        return self._anonymize_segment(held) if held else ""

    def _anonymize_segment(self, segment: str) -> str:
        if len(segment) > self.max_segment_chars:
            raise SegmentTooLongError(
                f"Segment of {len(segment)} characters exceeds the limit"
            )
        results = self.analyzer.analyze(
            text=segment, language=self.language, entities=self.entities
        )
        return self.anonymizer.anonymize(
            text=segment, analyzer_results=results, operators=self.operators
        ).text


def anonymize_stream(
    deltas: Iterable[str], streaming_anonymizer: StreamingAnonymizer
) -> Iterator[str]:
    """Wrap a stream of text deltas, yielding anonymized text."""
    for delta in deltas:
        out = streaming_anonymizer.feed(delta)
        if out:
            yield out
    tail = streaming_anonymizer.flush()
    if tail:
        yield tail


if __name__ == "__main__":
    analyzer = AnalyzerEngine()
    anonymizer = AnonymizerEngine()

    # Deltas as a model might stream them. The email and the phone number are
    # both split across deltas.
    deltas = [
        "Sure. You can reach Jane at jane.d",
        "oe@example.com or on 212-55",
        "5-0147.\nAnything else?",
    ]

    streamed = "".join(
        anonymize_stream(deltas, StreamingAnonymizer(analyzer, anonymizer))
    )
    print(f"StreamingAnonymizer: {streamed!r}")

    # Per-delta output contains raw values, so only report whether it differs.
    naive = "".join(
        anonymizer.anonymize(
            text=d, analyzer_results=analyzer.analyze(text=d, language="en")
        ).text
        for d in deltas
    )
    print(f"Each delta on its own gives the same output: {naive == streamed}")
