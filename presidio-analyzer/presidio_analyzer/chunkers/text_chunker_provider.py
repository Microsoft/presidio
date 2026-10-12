"""Factory provider for creating text chunkers from configuration."""

import logging
from typing import Any, Dict, Optional

from presidio_analyzer.chunkers.base_chunker import BaseTextChunker
from presidio_analyzer.chunkers.character_based_text_chunker import (
    CharacterBasedTextChunker,
)

logger = logging.getLogger("presidio-analyzer")


class TextChunkerProvider:
    """Create text chunkers from configuration.

    :param chunker_configuration: Dict with chunker_type and optional params.
        Example::

            {"chunker_type": "character", "chunk_size": 300, "chunk_overlap": 75}

    If no configuration provided, uses character-based chunker with default params
    tuned for boundary coverage (chunk_size=250, chunk_overlap=50).
    """

    def __init__(
        self,
        chunker_configuration: Optional[Dict[str, Any]] = None,
    ):
        # Default to a safe overlap to avoid boundary losses for cross-chunk entities.
        self.chunker_configuration = chunker_configuration or {
            "chunker_type": "character",
            "chunk_size": 250,
            "chunk_overlap": 50,
        }

    def create_chunker(self) -> BaseTextChunker:
        """Create a text chunker instance from configuration."""
        config = self.chunker_configuration.copy()
        chunker_type = config.pop("chunker_type", "character")

        if chunker_type == "character":
            chunker_class = CharacterBasedTextChunker
        elif chunker_type == "tokenizer":
            from presidio_analyzer.chunkers.tokenizer_based_text_chunker import (
                TokenizerBasedTextChunker,
            )

            chunker_class = TokenizerBasedTextChunker
        else:
            raise ValueError(
                f"Unknown chunker_type '{chunker_type}'. "
                f"Available: ['character', 'tokenizer']"
            )

        try:
            return chunker_class(**config)
        except TypeError as exc:
            raise ValueError(
                f"Invalid configuration for chunker_type '{chunker_type}': {config}"
            ) from exc
