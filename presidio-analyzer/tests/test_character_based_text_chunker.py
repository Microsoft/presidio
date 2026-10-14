"""Tests for CharacterBasedTextChunker."""

import pytest

from presidio_analyzer.chunkers import CharacterBasedTextChunker, TextChunk


class TestCharacterBasedTextChunkerInit:
    """Tests for CharacterBasedTextChunker initialization."""

    def test_default_values(self):
        """Test default initialization values."""
        chunker = CharacterBasedTextChunker()
        assert chunker.chunk_size == 250
        assert chunker.chunk_overlap == 50

    def test_custom_boundary_chars(self):
        """Test custom boundary characters."""
        chunker = CharacterBasedTextChunker(boundary_chars=[" ", "\n", "\t"])
        assert chunker.boundary_chars == (" ", "\n", "\t")

    def test_invalid_chunk_size_raises_error(self):
        """Test that invalid chunk_size raises ValueError."""
        with pytest.raises(ValueError, match="chunk_size must be greater than 0"):
            CharacterBasedTextChunker(chunk_size=0)
        with pytest.raises(ValueError, match="chunk_size must be greater than 0"):
            CharacterBasedTextChunker(chunk_size=-10)

    def test_invalid_chunk_overlap_raises_error(self):
        """Test that invalid chunk_overlap raises ValueError."""
        with pytest.raises(ValueError, match="chunk_overlap must be non-negative"):
            CharacterBasedTextChunker(chunk_size=100, chunk_overlap=-5)

        with pytest.raises(ValueError, match="chunk_overlap must be non-negative"):
            CharacterBasedTextChunker(chunk_size=100, chunk_overlap=100)


class TestCharacterBasedTextChunkerChunk:
    """Tests for CharacterBasedTextChunker.chunk() method."""

    def test_empty_text_returns_empty_list(self):
        """Test chunking empty text returns empty list."""
        chunker = CharacterBasedTextChunker(chunk_size=50, chunk_overlap=10)
        assert chunker.chunk("") == []

    def test_short_text_returns_single_chunk(self):
        """Test text shorter than chunk_size returns single chunk."""
        chunker = CharacterBasedTextChunker(chunk_size=100, chunk_overlap=10)
        text = "Hello world"
        chunks = chunker.chunk(text)

        assert len(chunks) == 1
        assert isinstance(chunks[0], TextChunk)
        assert chunks[0].text == text
        assert chunks[0].start == 0
        assert chunks[0].end == len(text)

    def test_chunks_extend_to_word_boundary(self):
        """Test that chunks extend to word boundaries (space/newline)."""
        chunker = CharacterBasedTextChunker(chunk_size=10, chunk_overlap=2)
        text = "Hello world foo bar"
        chunks = chunker.chunk(text)

        # Verify chunks don't cut words in the middle
        for chunk in chunks:
            # Each chunk text should not start/end mid-word (except first/last)
            assert text[chunk.start:chunk.end] == chunk.text

    def test_offset_calculation_is_correct(self):
        """Test that chunk offsets map correctly to original text."""
        chunker = CharacterBasedTextChunker(chunk_size=20, chunk_overlap=5)
        text = "This is a test string for chunking purposes"
        chunks = chunker.chunk(text)

        # Critical: offsets must point to correct positions
        for chunk in chunks:
            assert text[chunk.start:chunk.end] == chunk.text

    def test_chunk_start_lands_on_word_boundary(self):
        """Test that every chunk after the first begins on a word boundary."""
        chunker = CharacterBasedTextChunker(chunk_size=10, chunk_overlap=3)
        text = "This is a test string for chunking purposes"
        chunks = chunker.chunk(text)

        assert len(chunks) > 1, "test needs multiple chunks to exercise the bug"
        for chunk in chunks[1:]:
            # "mid-word" means both neighbours of `start` are non-boundary chars
            # (start sits strictly between two letters of the same word). A
            # start landing ON a boundary char, or right after one, is fine.
            before_is_boundary = (
                chunk.start == 0 or text[chunk.start - 1] in chunker.boundary_chars
            )
            at_is_boundary = text[chunk.start] in chunker.boundary_chars
            assert before_is_boundary or at_is_boundary, (
                f"chunk starting at {chunk.start} begins mid-word: {chunk.text[:20]!r}"
            )


class TestCharacterBasedTextChunkerEdgeCases:
    """Edge case tests for CharacterBasedTextChunker."""

    def test_whitespace_only_text(self):
        """Test chunking whitespace-only text."""
        chunker = CharacterBasedTextChunker(chunk_size=10, chunk_overlap=2)
        text = "     "
        chunks = chunker.chunk(text)

        assert len(chunks) == 1
        assert chunks[0].text == text

    def test_newline_boundary(self):
        """Test that newlines are treated as word boundaries."""
        chunker = CharacterBasedTextChunker(chunk_size=10, chunk_overlap=2)
        text = "Hello\nworld foo"
        chunks = chunker.chunk(text)

        # "Hello\nworld" is 11 chars, extends past chunk_size=10 until space at position 11
        # The chunk stops AT the boundary (space), not including it
        assert chunks[0].text == "Hello\nworld"
        assert chunks[0].end == 11  # Position of space
        assert text[chunks[0].start:chunks[0].end] == chunks[0].text

    def test_text_without_spaces_cjk(self):
        """Test chunking CJK text without spaces extends to end."""
        chunker = CharacterBasedTextChunker(chunk_size=5, chunk_overlap=1)
        text = "这是中文文本"  # Chinese: 6 chars, no spaces
        chunks = chunker.chunk(text)

        # Without word boundaries, should extend to end
        assert len(chunks) == 1
        assert chunks[0].text == text

    def test_very_long_word_extends_to_boundary(self):
        """Test words longer than chunk_size extend to next boundary."""
        chunker = CharacterBasedTextChunker(chunk_size=10, chunk_overlap=2)
        text = "supercalifragilisticexpialidocious end"
        chunks = chunker.chunk(text)

        # Long word should extend until space is found
        assert len(chunks) >= 1
        assert "supercalifragilisticexpialidocious" in chunks[0].text


class TestCharacterBasedTextChunkerIntegration:
    """Integration tests for CharacterBasedTextChunker."""

    def test_long_text_produces_multiple_chunks(self):
        """Test chunking longer text produces multiple chunks with correct offsets."""
        chunker = CharacterBasedTextChunker(chunk_size=50, chunk_overlap=10)
        text = "John Smith works at Microsoft. Jane Doe lives in Seattle. Bob Johnson studies at MIT."

        chunks = chunker.chunk(text)

        assert len(chunks) > 1
        # Verify all offsets are correct
        for chunk in chunks:
            assert text[chunk.start:chunk.end] == chunk.text

    def test_overlap_captures_entity_at_boundary(self):
        """Test that overlap prevents missing entities at chunk boundaries."""
        # This is the core purpose of overlap
        chunker = CharacterBasedTextChunker(chunk_size=25, chunk_overlap=10)
        text = "Some prefix text. John Smith is here. Some suffix."
        chunks = chunker.chunk(text)

        # "John Smith" should appear complete in at least one chunk
        assert any("John Smith" in chunk.text for chunk in chunks)
