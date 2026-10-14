"""Character-based text chunker with word boundary preservation.

Based on gliner-spacy implementation:
https://github.com/theirstory/gliner-spacy/blob/main/gliner_spacy/pipeline.py#L60-L96
"""
import logging
from typing import Iterable, List, Tuple

from presidio_analyzer.chunkers.base_chunker import BaseTextChunker, TextChunk

logger = logging.getLogger("presidio-analyzer")


WORD_BOUNDARY_CHARS: Tuple[str, ...] = (" ", "\n")


class CharacterBasedTextChunker(BaseTextChunker):
    """Character-based text chunker with word boundary preservation."""

    def __init__(
        self,
        chunk_size: int = 250,
        chunk_overlap: int = 50,
        boundary_chars: Iterable[str] | None = None,
    ):
        """Initialize the character-based text chunker.

        Note: Chunks may slightly exceed chunk_size to preserve complete words.
        When this occurs, the actual overlap may vary from the specified value.

        :param chunk_size: Target maximum characters per chunk (must be > 0)
        :param chunk_overlap: Target characters to overlap between chunks
            (must be >= 0 and < chunk_size)
        :param boundary_chars: Characters that count as word boundaries.
            Defaults to space/newline to keep current behavior.
        """
        if chunk_size <= 0:
            logger.error("Invalid chunk_size: %d. Must be greater than 0.", chunk_size)
            raise ValueError("chunk_size must be greater than 0")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            logger.error(
                "Invalid chunk_overlap. Must be non-negative and less than chunk_size"
            )
            raise ValueError(
                "chunk_overlap must be non-negative and less than chunk_size"
            )

        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        # Allow callers to tune boundaries
        # (e.g., punctuation, tabs) without changing defaults.
        self._boundary_chars: Tuple[str, ...] = (
            tuple(boundary_chars) if boundary_chars is not None else WORD_BOUNDARY_CHARS
        )

    @property
    def chunk_size(self) -> int:
        """Get the chunk size.

        :return: The chunk size
        """
        return self._chunk_size

    @property
    def chunk_overlap(self) -> int:
        """Get the chunk overlap.

        :return: The chunk overlap
        """
        return self._chunk_overlap

    @property
    def boundary_chars(self) -> Tuple[str, ...]:
        """Characters treated as word boundaries when extending chunks."""

        return self._boundary_chars

    def chunk(self, text: str) -> List[TextChunk]:
        """Split text into overlapping chunks at word boundaries.

        Chunks are extended to the nearest word boundary (space or newline)
        to avoid splitting words. This means chunks may slightly exceed
        chunk_size. For texts without spaces (e.g., CJK languages), chunks
        may extend to end of text.

        :param text: The input text to chunk
        :return: List of TextChunk objects with text and position information
        """
        if not text:
            logger.debug("Empty text provided, returning empty chunk list")
            return []

        logger.debug(
            "Chunking text: length=%d, chunk_size=%d, overlap=%d",
            len(text),
            self._chunk_size,
            self._chunk_overlap,
        )

        chunks = []
        start = 0

        while start < len(text):
            # Calculate end position
            end = (
                start + self._chunk_size
                if start + self._chunk_size < len(text)
                else len(text)
            )

            # Extend to complete word boundary (space or newline by default)
            while end < len(text) and text[end] not in self._boundary_chars:
                end += 1

            chunks.append(TextChunk(text=text[start:end], start=start, end=end))

            # Move start position with overlap (stop if we've covered all text)
            if end >= len(text):
                break
            start = end - self._chunk_overlap

            while start < end and text[start] not in self._boundary_chars:
                start += 1

        logger.debug("Created %d chunks from text", len(chunks))
        return chunks
