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

    def predict_batch_with_chunking(
        self,
        texts: List[str],
        predict_batch_func: Callable[[List[str]], List[List["RecognizerResult"]]],
    ) -> List[List["RecognizerResult"]]:
        """Process multiple texts with automatic chunking for batch inference.

        Chunks all texts, batches them into a single call to predict_batch_func,
        then unflattens and adjusts offsets.

        Note on memory: all chunk strings are collected into one Python list
        before being passed to predict_batch_func. The list itself is small
        (just string references). The GPU/CPU memory bound for the actual
        model forward pass is the responsibility of predict_batch_func — for
        the in-tree recognizers, that is enforced via `inference_batch_size`
        which caps the per-forward-pass batch.

        :param texts: List of input texts to process
        :param predict_batch_func: Function that takes a list of texts and returns
            a list of lists of RecognizerResult objects. Must return exactly
            one result list per input chunk.
        :return: List of RecognizerResult lists, one per input text
        :raises ValueError: If predict_batch_func returns a list of a length
            different from its input list.
        """
        from presidio_analyzer import RecognizerResult

        if not texts:
            return []

        # Build flat list of all chunk texts with tracking metadata
        # Each entry: (text_index, chunk, is_single_chunk)
        all_chunks = []
        flat_chunk_texts = []
        multi_chunk_texts = set()

        for text_idx, text in enumerate(texts):
            chunks = self.chunk(text)
            if not chunks:
                # No chunks produced; record a sentinel
                all_chunks.append((text_idx, None, True))
            elif len(chunks) == 1:
                # Single chunk - use original text for consistency
                all_chunks.append((text_idx, chunks[0], True))
                flat_chunk_texts.append(text)
            else:
                multi_chunk_texts.add(text_idx)
                for chunk in chunks:
                    all_chunks.append((text_idx, chunk, False))
                    flat_chunk_texts.append(chunk.text)

        # Call predict_batch_func once with all chunk texts, sorted by
        # length. Batched pipelines pad each batch to its longest member,
        # so grouping similar-length chunks minimizes wasted compute on
        # padding tokens. Results are restored to original order after.
        if flat_chunk_texts:
            order = sorted(
                range(len(flat_chunk_texts)),
                key=lambda i: len(flat_chunk_texts[i]),
            )
            sorted_results = predict_batch_func(
                [flat_chunk_texts[i] for i in order]
            )
            if len(sorted_results) != len(flat_chunk_texts):
                raise ValueError(
                    f"predict_batch_func returned {len(sorted_results)} results "
                    f"for {len(flat_chunk_texts)} input chunks. The function "
                    "must return one result list per input chunk."
                )
            flat_results = [None] * len(flat_chunk_texts)
            for sorted_pos, orig_idx in enumerate(order):
                flat_results[orig_idx] = sorted_results[sorted_pos]
        else:
            flat_results = []

        # Unflatten results back to per-text structure
        num_texts = len(texts)
        per_text_results: List[List["RecognizerResult"]] = [
            [] for _ in range(num_texts)
        ]

        flat_idx = 0
        for text_idx, chunk, is_single in all_chunks:
            if chunk is None:
                # No chunks for this text, skip
                continue

            chunk_results = flat_results[flat_idx]
            flat_idx += 1

            if is_single:
                # Single chunk covering entire text - no offset adjustment
                per_text_results[text_idx].extend(chunk_results)
            else:
                # Adjust offsets using chunk.start
                for pred in chunk_results:
                    adjusted_pred = RecognizerResult(
                        entity_type=pred.entity_type,
                        start=pred.start + chunk.start,
                        end=pred.end + chunk.start,
                        score=pred.score,
                        analysis_explanation=pred.analysis_explanation,
                        recognition_metadata=pred.recognition_metadata,
                    )
                    per_text_results[text_idx].append(adjusted_pred)

        # Deduplicate overlapping entities for texts that had multiple chunks
        for text_idx in multi_chunk_texts:
            per_text_results[text_idx] = self.deduplicate_overlapping_entities(
                per_text_results[text_idx]
            )

        return per_text_results

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
