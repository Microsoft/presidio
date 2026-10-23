"""Abstract base class for text chunking strategies."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

from presidio_analyzer.recognizer_result import RecognizerResult


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

        predictions, at_chunk_edge = self._process_chunks_marking_edges(
            chunks, predict_func
        )
        return self.deduplicate_overlapping_entities(
            predictions, at_chunk_edge=at_chunk_edge
        )

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
        predictions, _ = self._process_chunks_marking_edges(chunks, process_func)
        return predictions

    def _process_chunks_marking_edges(
        self,
        chunks: List[TextChunk],
        process_func: Callable[[str], List["RecognizerResult"]],
    ) -> Tuple[List["RecognizerResult"], List[bool]]:
        """Process text chunks and mark predictions cut by an inner chunk edge.

        A prediction touches an inner edge when it starts at the start of any
        chunk but the first, or ends at the end of any chunk but the last.
        Such a prediction may be a partial entity that the neighbouring
        chunk saw whole.

        :param chunks: List of TextChunk objects with text and position information
        :param process_func: Function that takes chunk text and returns
            RecognizerResult objects
        :return: Tuple of the RecognizerResult list with adjusted offsets and
            a parallel list of inner-edge flags
        """
        all_predictions = []
        at_chunk_edge = []
        last = len(chunks) - 1

        for idx, chunk in enumerate(chunks):
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
                at_chunk_edge.append(
                    (idx > 0 and pred.start == 0)
                    or (idx < last and pred.end == len(chunk.text))
                )

        return all_predictions, at_chunk_edge

    def deduplicate_overlapping_entities(
        self,
        predictions: List["RecognizerResult"],
        overlap_threshold: float = 0.5,
        at_chunk_edge: Optional[List[bool]] = None,
    ) -> List["RecognizerResult"]:
        """Remove duplicate entities from overlapping chunks.

        The highest-scoring prediction is kept, unless it touches an inner
        chunk edge and its only duplicate does not. The overlap guarantees the
        neighbouring chunk saw that entity whole, so its prediction is kept
        instead of the possibly partial one.

        :param predictions: List of RecognizerResult objects
        :param overlap_threshold: Overlap ratio threshold to consider duplicates
            (default: 0.5)
        :param at_chunk_edge: Optional list, parallel to predictions, flagging
            predictions that touch an inner chunk edge (default: none do)
        :return: Deduplicated list of RecognizerResult sorted by position
        """
        if not predictions:
            return predictions
        if at_chunk_edge is None:
            at_chunk_edge = [False] * len(predictions)

        def is_duplicate(pred: "RecognizerResult", kept: "RecognizerResult") -> bool:
            # Check if same entity type and overlapping positions
            if pred.entity_type != kept.entity_type:
                return False
            overlap_start = max(pred.start, kept.start)
            overlap_end = min(pred.end, kept.end)
            if overlap_start >= overlap_end:
                return False

            # Calculate overlap ratio
            overlap_len = overlap_end - overlap_start
            pred_len = pred.end - pred.start
            kept_len = kept.end - kept.start
            if pred_len <= 0 or kept_len <= 0:
                return False

            # Check if overlap exceeds threshold
            return overlap_len / min(pred_len, kept_len) > overlap_threshold

        # Sort by score descending to keep highest scoring entities
        order = sorted(
            range(len(predictions)), key=lambda i: predictions[i].score, reverse=True
        )
        unique = []
        unique_at_edge = []

        for idx in order:
            pred = predictions[idx]
            duplicates = [
                i for i, kept in enumerate(unique) if is_duplicate(pred, kept)
            ]
            if not duplicates:
                unique.append(pred)
                unique_at_edge.append(at_chunk_edge[idx])
            elif (
                len(duplicates) == 1
                and unique_at_edge[duplicates[0]]
                and not at_chunk_edge[idx]
            ):
                # The kept result may be cut by a chunk edge, prefer the
                # prediction from the chunk that saw the entity whole
                unique[duplicates[0]] = pred
                unique_at_edge[duplicates[0]] = False

        # Sort by position for consistent output
        return sorted(unique, key=lambda p: p.start)
