"""Tests for BaseTextChunker methods."""
import pytest

from presidio_analyzer import RecognizerResult
from presidio_analyzer.chunkers import CharacterBasedTextChunker


class TestPredictWithChunking:
    """Test predict_with_chunking orchestration."""

    def test_short_text_not_chunked(self):
        """Short text bypasses chunking."""
        chunker = CharacterBasedTextChunker(chunk_size=100, chunk_overlap=20)
        predict_func = lambda t: [
            RecognizerResult(entity_type="PERSON", start=0, end=5, score=0.9)
        ]

        result = chunker.predict_with_chunking("Short text", predict_func)

        assert len(result) == 1
        assert result[0].start == 0

    def test_long_text_offsets_adjusted(self):
        """Entity offsets are adjusted to original text positions."""
        chunker = CharacterBasedTextChunker(chunk_size=20, chunk_overlap=5)
        text = "John Smith lives in New York City with Jane Doe"

        def predict_func(chunk):
            if "Jane" in chunk:
                idx = chunk.index("Jane")
                return [
                    RecognizerResult(entity_type="PERSON", start=idx, end=idx + 4, score=0.9)
                ]
            return []

        result = chunker.predict_with_chunking(text, predict_func)

        # Jane appears at position 39 in original text
        assert len(result) == 1
        assert result[0].start == text.index("Jane")


class TestDeduplicateOverlappingEntities:
    """Test deduplication of overlapping entities from chunk boundaries."""

    def test_exact_duplicates_keeps_highest_score(self):
        """Same entity from overlapping chunks keeps higher score."""
        chunker = CharacterBasedTextChunker()
        predictions = [
            RecognizerResult(entity_type="PERSON", start=0, end=10, score=0.9),
            RecognizerResult(entity_type="PERSON", start=0, end=10, score=0.7),
        ]

        result = chunker.deduplicate_overlapping_entities(predictions)

        assert len(result) == 1
        assert result[0].score == 0.9

    def test_overlapping_same_type_deduplicated(self):
        """Overlapping entities of same type are deduplicated."""
        chunker = CharacterBasedTextChunker()
        predictions = [
            RecognizerResult(entity_type="PERSON", start=0, end=10, score=0.9),
            RecognizerResult(entity_type="PERSON", start=3, end=13, score=0.8),
        ]

        result = chunker.deduplicate_overlapping_entities(predictions)

        assert len(result) == 1

    def test_duplicate_keeps_full_span_of_partial_higher_score(self):
        """A higher-scoring partial match must not cut away the rest of the entity."""
        chunker = CharacterBasedTextChunker(chunk_size=38, chunk_overlap=10)
        text = "The contact person for this case is John Smith from accounting."

        def predict_func(chunk):
            # The first chunk ends after "John", so it only sees the first name
            if chunk.endswith("John"):
                idx = chunk.index("John")
                return [
                    RecognizerResult(entity_type="PERSON", start=idx, end=idx + 4, score=0.92)
                ]
            if "John Smith" in chunk:
                idx = chunk.index("John Smith")
                return [
                    RecognizerResult(entity_type="PERSON", start=idx, end=idx + 10, score=0.88)
                ]
            return []

        result = chunker.predict_with_chunking(text, predict_func)

        assert len(result) == 1
        assert text[result[0].start : result[0].end] == "John Smith"
        assert result[0].score == 0.92

    def test_different_types_not_deduplicated(self):
        """Overlapping entities of different types are kept."""
        chunker = CharacterBasedTextChunker()
        predictions = [
            RecognizerResult(entity_type="PERSON", start=0, end=10, score=0.9),
            RecognizerResult(entity_type="LOCATION", start=5, end=15, score=0.8),
        ]

        result = chunker.deduplicate_overlapping_entities(predictions)

        assert len(result) == 2

    def test_results_sorted_by_position(self):
        """Results are sorted by start position."""
        chunker = CharacterBasedTextChunker()
        predictions = [
            RecognizerResult(entity_type="PERSON", start=20, end=30, score=0.9),
            RecognizerResult(entity_type="PERSON", start=0, end=10, score=0.8),
        ]

        result = chunker.deduplicate_overlapping_entities(predictions)

        assert result[0].start == 0
        assert result[1].start == 20

    def test_zero_length_span_does_not_raise(self):
        """Zero-length spans should not cause ZeroDivisionError."""
        chunker = CharacterBasedTextChunker()
        predictions = [
            RecognizerResult(entity_type="PERSON", start=5, end=5, score=0.9),
            RecognizerResult(entity_type="PERSON", start=0, end=10, score=0.8),
        ]

        # Should not raise ZeroDivisionError
        result = chunker.deduplicate_overlapping_entities(predictions)
        assert len(result) == 2


class TestPredictWithChunkingEdgeCases:
    """Test edge cases in predict_with_chunking."""

    def test_empty_text_returns_empty_without_calling_predict(self):
        """Empty text should return [] without invoking predict_func."""
        chunker = CharacterBasedTextChunker(chunk_size=100)
        call_count = 0

        def predict_func(t):
            nonlocal call_count
            call_count += 1
            return []

        result = chunker.predict_with_chunking("", predict_func)

        assert result == []
        assert call_count == 0, "predict_func should not be called for empty text"
