"""Abstract base class for text chunking strategies."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, List

if TYPE_CHECKING:
    from presidio_analyzer import RecognizerResult


@dataclass
class TextChunk:
    """Represents a chunk of text with its position in the original text.

    :param text: The chunk content
    :param start: Start position in the original text (inclusive)
    :param end: End position in the original text (exclusive)
    """

    text: str
    start: int
    end: int


class BaseTextChunker(ABC):
    """Abstract base class for text chunking strategies.

    Subclasses must implement the chunk() method to split text into
    TextChunk objects that include both content and position information.

    Provides methods for processing predictions across chunks and
    deduplicating overlapping entities.
    """

    @abstractmethod
    def chunk(self, text: str) -> List[TextChunk]:
        """Split text into chunks with position information.

        :param text: The input text to split
        :return: List of TextChunk objects with text and position data
        """
        pass

    def predict_with_chunking(
        self,
        text: str,
        predict_func: Callable[[str], List["RecognizerResult"]],
    ) -> List["RecognizerResult"]:
        """Process text with automatic chunking for long texts.

        For short text, calls predict_func directly.
        For long text, chunks it and merges predictions with deduplication.

        :param text: Input text to process
        :param predict_func: Function that takes text and returns
            RecognizerResult objects
        :return: List of RecognizerResult with correct offsets
        """
        chunks = self.chunk(text)
        if not chunks:
            return []
        if len(chunks) == 1:
            return predict_func(text)

        predictions = self._process_chunks(chunks, predict_func)
        return self.deduplicate_overlapping_entities(predictions)

    def _process_chunks(
        self,
        chunks: List[TextChunk],
        process_func: Callable[[str], List["RecognizerResult"]],
    ) -> List["RecognizerResult"]:
        """Process text chunks and adjust entity offsets.

        :param chunks: List of TextChunk objects with text and position information
        :param process_func: Function that takes chunk text and returns
            RecognizerResult objects
        :return: List of RecognizerResult with adjusted offsets
        """
        from presidio_analyzer import RecognizerResult

        all_predictions = []

        for chunk in chunks:
            chunk_predictions = process_func(chunk.text)

            # Create new RecognizerResult objects with adjusted offsets
            # to avoid mutating the original predictions
            for pred in chunk_predictions:
                adjusted_pred = RecognizerResult(
                    entity_type=pred.entity_type,
                    start=pred.start + chunk.start,
                    end=pred.end + chunk.start,
                    score=pred.score,
                    analysis_explanation=pred.analysis_explanation,
                    recognition_metadata=pred.recognition_metadata,
                )
                all_predictions.append(adjusted_pred)

        return all_predictions

    def deduplicate_overlapping_entities(
        self,
        predictions: List["RecognizerResult"],
        overlap_threshold: float = 0.5,
    ) -> List["RecognizerResult"]:
        """Remove duplicate entities from overlapping chunks.

        :param predictions: List of RecognizerResult objects
        :param overlap_threshold: Overlap ratio threshold to consider duplicates
            (default: 0.5)
        :return: Deduplicated list of RecognizerResult sorted by position
        """
        if not predictions:
            return predictions

        # Sort by score descending to keep highest scoring entities
        sorted_preds = sorted(predictions, key=lambda p: p.score, reverse=True)
        unique = []

        for pred in sorted_preds:
            is_duplicate = False
            for kept in unique:
                # Check if same entity type and overlapping positions
                if pred.entity_type == kept.entity_type:
                    overlap_start = max(pred.start, kept.start)
                    overlap_end = min(pred.end, kept.end)

                    if overlap_start < overlap_end:
                        # Calculate overlap ratio
                        overlap_len = overlap_end - overlap_start
                        pred_len = pred.end - pred.start
                        kept_len = kept.end - kept.start

                        if pred_len <= 0 or kept_len <= 0:
                            continue

                        # Check if overlap exceeds threshold
                        if overlap_len / min(pred_len, kept_len) > overlap_threshold:
                            is_duplicate = True
                            break

            if not is_duplicate:
                unique.append(pred)

        # Sort by position for consistent output
        return sorted(unique, key=lambda p: p.start)
