"""spaCy component for Hugging Face token-classification pipelines."""

import logging
from collections.abc import Iterable, Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any, Optional

from spacy import util
from spacy.language import Language
from spacy.pipeline import Pipe
from spacy.tokens import Doc, SpanGroup
from thinc.api import get_torch_default_device

try:
    from transformers import pipeline as hf_pipeline
except ImportError:
    hf_pipeline = None

logger = logging.getLogger("presidio-analyzer")

FACTORY_NAME = "presidio_hf_token_pipe"


def is_available() -> bool:
    """Return whether the optional Transformers dependency is installed."""
    return hf_pipeline is not None


def _pipeline_device() -> int:
    """Return a Transformers-compatible CPU or CUDA device index."""
    device = get_torch_default_device()
    if device.type != "cuda":
        return -1
    return device.index if device.index is not None else 0


@Language.factory(
    FACTORY_NAME,
    assigns=[],
    default_config={
        "model": "",
        "revision": "main",
        "stride": 14,
        "aggregation_strategy": "max",
        "alignment_mode": "expand",
        "spans_key": "bert-base-ner",
        "pipeline_kwargs": {},
    },
    default_score_weights={},
)
def create_huggingface_token_pipe(
    nlp: Language,
    name: str,
    model: str,
    revision: str,
    stride: Optional[int],
    aggregation_strategy: str,
    alignment_mode: str,
    spans_key: str,
    pipeline_kwargs: dict[str, Any],
) -> "HuggingFaceTokenPipe":
    """Create a spaCy component backed by a Hugging Face pipeline."""
    if hf_pipeline is None:
        raise ImportError(
            "transformers is not installed. Install presidio-analyzer[transformers] "
            "to use TransformersNlpEngine."
        )
    if not model:
        raise ValueError("A Hugging Face token-classification model is required")

    kwargs = {
        "task": "token-classification",
        "model": model,
        "revision": revision,
        "aggregation_strategy": aggregation_strategy,
        "device": _pipeline_device(),
    }
    if stride is not None:
        kwargs["stride"] = stride

    pipeline = hf_pipeline(**kwargs, **pipeline_kwargs)
    return HuggingFaceTokenPipe(
        name=name,
        pipeline=pipeline,
        alignment_mode=alignment_mode,
        spans_key=spans_key,
    )


class HuggingFaceTokenPipe(Pipe):
    """Store token-classification predictions as scored spaCy spans."""

    def __init__(
        self,
        name: str,
        pipeline: Any,
        alignment_mode: str,
        spans_key: str,
    ) -> None:
        self.name = name
        self.pipeline = pipeline
        self.alignment_mode = alignment_mode
        self.spans_key = spans_key

    def __call__(self, doc: Doc) -> Doc:
        """Annotate one document."""
        return self._add_predictions(doc, self._predict_one(doc))

    def pipe(self, stream: Iterable[Doc], *, batch_size: int = 128) -> Iterator[Doc]:
        """Annotate documents in batches, retrying batch failures individually."""
        for batch in util.minibatch(stream, size=batch_size):
            docs = list(batch)
            predictions = self._predict_batch(docs)
            for doc, doc_predictions in zip(docs, predictions, strict=True):
                yield self._add_predictions(doc, doc_predictions)

    def _predict_batch(self, docs: Sequence[Doc]) -> list[Sequence[Mapping[str, Any]]]:
        texts = [doc.text for doc in docs]
        try:
            output = self.pipeline(texts)
        except Exception as error:
            logger.warning(
                "Hugging Face batch inference failed with %s; retrying each document",
                type(error).__name__,
            )
            return [self._predict_one(doc) for doc in docs]

        if not isinstance(output, list) or len(output) != len(docs):
            raise ValueError(
                "Hugging Face batch output count does not match the document count"
            )
        return [self._validate_predictions(item) for item in output]

    def _predict_one(self, doc: Doc) -> Sequence[Mapping[str, Any]]:
        try:
            output = self.pipeline(doc.text)
        except Exception as error:
            logger.warning(
                "Hugging Face inference failed with %s; skipping document",
                type(error).__name__,
            )
            return []
        return self._validate_predictions(output)

    @staticmethod
    def _validate_predictions(output: Any) -> Sequence[Mapping[str, Any]]:
        if not isinstance(output, list) or any(
            not isinstance(item, Mapping) for item in output
        ):
            raise TypeError(
                "Hugging Face token-classification output must be a list of mappings"
            )
        return output

    def _add_predictions(
        self, doc: Doc, predictions: Sequence[Mapping[str, Any]]
    ) -> Doc:
        spans = SpanGroup(doc, attrs={"scores": []})
        previous_end = 0

        for prediction in predictions:
            label = prediction.get("entity_group") or prediction.get("entity")
            start = prediction.get("start")
            end = prediction.get("end")
            if (
                not isinstance(label, str)
                or not isinstance(start, int)
                or not isinstance(end, int)
            ):
                raise ValueError(
                    "Hugging Face prediction is missing a string label or integer "
                    f"offsets; keys={sorted(prediction.keys())}"
                )
            try:
                score = float(prediction["score"])
            except (KeyError, TypeError, ValueError):
                raise ValueError(
                    "Hugging Face prediction is missing a numeric score"
                ) from None

            span = None
            if start >= previous_end:
                span = doc.char_span(
                    start,
                    end,
                    label=label,
                    alignment_mode=self.alignment_mode,
                )
            if span is None or span.start_char < previous_end:
                logger.warning(
                    "Skipping unaligned or overlapping prediction "
                    "label=%s start=%d end=%d",
                    label,
                    start,
                    end,
                )
                continue

            spans.append(span)
            spans.attrs["scores"].append(score)
            previous_end = end

        doc.spans[self.spans_key] = spans
        return doc

    def to_bytes(self, **kwargs: Any) -> bytes:
        """Return no model data because the pipeline is rebuilt from config."""
        return b""

    def from_bytes(self, bytes_data: bytes, **kwargs: Any) -> "HuggingFaceTokenPipe":
        """Keep the pipeline created from the current configuration."""
        return self

    def to_disk(self, path: Path, **kwargs: Any) -> None:
        """Persist no model data because the pipeline is rebuilt from config."""
        return None

    def from_disk(self, path: Path, **kwargs: Any) -> "HuggingFaceTokenPipe":
        """Keep the pipeline created from the current configuration."""
        return self
