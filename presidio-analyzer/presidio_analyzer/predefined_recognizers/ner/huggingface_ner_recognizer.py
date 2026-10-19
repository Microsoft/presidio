"""HuggingFace NER Recognizer for direct NER model inference.

This recognizer uses HuggingFace Transformers pipeline directly,
bypassing spaCy tokenizer alignment issues that commonly occur
with agglutinative languages (Korean, Japanese, Turkish, etc.).

The spaCy tokenizer tends to include particles/postpositions with nouns,
causing alignment_mode issues:
- NER result: "김태웅" (entity only)
- spaCy token: "김태웅이고" (entity + particle)
- char_span alignment fails

This recognizer solves the problem by using the HuggingFace NER model's
own tokenizer and returning results directly without spaCy alignment.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from presidio_analyzer import (
    AnalysisExplanation,
    LocalRecognizer,
    RecognizerResult,
)
from presidio_analyzer.chunkers import (
    BaseTextChunker,
    CharacterBasedTextChunker,
)
from presidio_analyzer.nlp_engine import NlpArtifacts, device_detector

try:
    from transformers import pipeline as hf_pipeline
except ImportError:
    hf_pipeline = None

try:
    import torch
except ImportError:
    torch = None


logger = logging.getLogger("presidio-analyzer")


class HuggingFaceNerRecognizer(LocalRecognizer):
    """HuggingFace Transformers based NER Recognizer.

    This recognizer uses HuggingFace pipeline directly for NER,
    bypassing spaCy tokenizer alignment issues. It's particularly
    useful for agglutinative languages (Korean, Japanese, Turkish, etc.)
    where particles attach to nouns.

    Unlike the standard TransformersNlpEngine approach, this recognizer:
    - Uses HuggingFace pipeline directly (not through spaCy)
    - Returns NER results without char_span alignment
    - Supports any HuggingFace token-classification model
    - Works with any language that has a HuggingFace NER model

    Example:
        >>> from presidio_analyzer import AnalyzerEngine
        >>> from presidio_analyzer.nlp_engine import NlpEngineProvider
        >>> from presidio_analyzer.predefined_recognizers.ner import (
        ...     HuggingFaceNerRecognizer
        ... )
        >>>
        >>> recognizer = HuggingFaceNerRecognizer(
        ...     model_name="dslim/bert-base-NER",
        ...     supported_language="en"
        ... )
        >>> nlp_engine = NlpEngineProvider(
        ...     nlp_configuration={
        ...         "nlp_engine_name": "no_op",
        ...         "models": [{"lang_code": "en", "model_name": "no_op"}],
        ...     }
        ... ).create_engine()
        >>> analyzer = AnalyzerEngine(
        ...     nlp_engine=nlp_engine, supported_languages=["en"]
        ... )
        >>> analyzer.registry.add_recognizer(recognizer)
    """

    # Default label mapping from common NER models to Presidio entities
    DEFAULT_LABEL_MAPPING = {
        # Standard NER labels (CoNLL format)
        "PER": "PERSON",
        "LOC": "LOCATION",
        "ORG": "ORGANIZATION",
        "MISC": "MISC",
        # Date/Time labels
        "DAT": "DATE_TIME",
        "DATE": "DATE_TIME",
        "TIME": "DATE_TIME",
        # Korean model labels (KoELECTRA, etc.)
        "PS": "PERSON",
        "LC": "LOCATION",
        "OG": "ORGANIZATION",
        "DT": "DATE_TIME",
        "TI": "DATE_TIME",
        # BERT-base-NER style labels (with B-/I- prefix stripped)
        "PERSON": "PERSON",
        "LOCATION": "LOCATION",
        "ORGANIZATION": "ORGANIZATION",
        "DATE_TIME": "DATE_TIME",
    }
    DEFAULT_HF_TASK = "token-classification"

    def __init__(
        self,
        supported_entities: Optional[List[str]] = None,
        name: str = "HuggingFaceNerRecognizer",
        supported_language: str = "en",
        version: str = "0.0.1",
        context: Optional[List[str]] = None,
        model_name: Optional[str] = None,
        label_mapping: Optional[Dict[str, str]] = None,
        threshold: float = 0.3,
        aggregation_strategy: str = "simple",
        chunk_overlap: int = 40,
        chunk_size: int = 400,
        device: Optional[Union[str, int]] = None,
        tokenizer_name: Optional[str] = None,
        text_chunker: Optional[BaseTextChunker] = None,
        label_prefixes: Optional[List[str]] = None,
        **kwargs,
    ):
        """Initialize the HuggingFace NER Recognizer.

        :param supported_entities: List of supported entities.
            If None, uses entities from label_mapping.
        :param name: Name of the recognizer
        :param supported_language: Language code (e.g., "en", "ko", "ja")
        :param version: Version of the recognizer
        :param context: Context words (N/A for this recognizer)
        :param model_name: HuggingFace model name or path.
            If None, must be set before calling load().
        :param label_mapping: Mapping from model labels to Presidio entities.
            If None, uses DEFAULT_LABEL_MAPPING.
        :param threshold: Minimum confidence score threshold (0.0 - 1.0)
        :param aggregation_strategy: Token aggregation strategy
            ("simple", "first", "average", "max").
            Recommendation: Use "simple" or "first" so that entities are pre-aggregated
            by the model, preserving performance and alignment.
        :param device: Device to use. Accepts:
            - "cpu" or -1 for CPU
            - "cuda" or "cuda:N" or int N for GPU
            - None for auto-detection (GPU if available, else CPU)
            Defaults to None.
        :param chunk_overlap: Number of characters to overlap between chunks.
        :param chunk_size: Maximum number of characters per chunk.
        :param tokenizer_name: Name of the tokenizer. Defaults to model_name.
        :param text_chunker: Text chunking strategy. Accepts a BaseTextChunker
            instance. If None, uses CharacterBasedTextChunker with provided
            chunk_size and chunk_overlap. When loaded from YAML, the registry
            loader converts the ``text_chunker`` dict to a chunker instance
            automatically.
        :param label_prefixes: List of label prefixes to strip (e.g., B-, I-).
        :raises ImportError: If transformers or torch libraries are not installed.
        """
        # Early check for required dependencies
        if hf_pipeline is None:
            raise ImportError(
                "transformers is not installed. Please install it "
                "(pip install transformers torch) to use this recognizer."
            )
        if torch is None:
            raise ImportError(
                "torch is not installed. Please install it "
                "(pip install torch) to use this recognizer."
            )

        self.model_name = model_name
        self.tokenizer_name = tokenizer_name or model_name
        self.label_mapping = (
            label_mapping if label_mapping is not None else self.DEFAULT_LABEL_MAPPING
        )
        self.threshold = threshold
        self.aggregation_strategy = aggregation_strategy
        if self.aggregation_strategy == "none":
            logger.warning(
                "aggregation_strategy='none' may result in fragmented entities "
                "(e.g., 'B-PER', 'I-PER'). Recommended: 'simple' or 'first'."
            )
        self.device = self._parse_device(device)
        self.label_prefixes = label_prefixes or ["B-", "I-", "U-", "L-"]
        self.ner_pipeline = None

        if kwargs:
            logger.warning(
                "Ignoring unsupported kwargs in %s: %s",
                name,
                sorted(kwargs.keys()),
            )

        # Derive supported entities from label mapping
        if supported_entities:
            final_supported_entities = supported_entities
        else:
            # Use sorted set for deterministic order
            final_supported_entities = sorted(list(set(self.label_mapping.values())))

        # Initialize text chunker before super().__init__() because
        # super() may call load(), which resolves deferred chunkers.
        if text_chunker is not None:
            self.text_chunker = text_chunker
        else:
            self.text_chunker = CharacterBasedTextChunker(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )

        super().__init__(
            supported_entities=final_supported_entities,
            name=name,
            supported_language=supported_language,
            version=version,
            context=context,
        )

        logger.info(
            f"Initialized {self.name} with model={self.model_name}, "
            f"threshold={self.threshold}, device={self.device}"
        )

    def _parse_device(self, device: Optional[Union[str, int]]) -> int:
        """Parse device string or int into a transformer-compatible int.

        Normalize diverse device inputs (None, "cpu", "cuda", "cuda:1", 0)
        to a standard integer format for the Transformers pipeline.
        If None, it uses Presidio's DeviceDetector for auto-detection.
        """
        if device is None:
            detected = device_detector.get_device()
            return 0 if detected == "cuda" else -1

        if isinstance(device, int):
            return device

        device_str = str(device).strip().lower()
        if device_str == "cpu":
            return -1
        if device_str == "cuda":
            return 0
        if device_str.startswith("cuda:"):
            try:
                return int(device_str.split(":", 1)[1])
            except (ValueError, IndexError):
                pass

        raise ValueError(
            f"Invalid device specified: {device}. "
            "Accepts 'cpu', 'cuda', 'cuda:N', or integer index."
        )

    def load(self) -> None:
        """Load the HuggingFace NER pipeline.

        This method handles:
        1. Hardware acceleration setup (CUDA validation and fallback)
        2. Lazy-loading of the heavyweight ML pipeline.
        """
        if self.ner_pipeline is not None:
            return

        if not self.model_name:
            logger.info("model_name is not set. Deferring HuggingFace model loading.")
            return

        # Device validation and fallback
        device = self.device
        if device >= 0:
            if not torch.cuda.is_available():
                logger.warning("CUDA is not available. Falling back to CPU.")
                device = -1
            elif device >= torch.cuda.device_count():
                logger.warning(
                    "Device index %d out of range (count=%d). Falling back to CPU.",
                    device,
                    torch.cuda.device_count(),
                )
                device = -1

        logger.info(f"Loading HuggingFace model: {self.model_name}, device={device}")

        try:
            self.ner_pipeline = hf_pipeline(
                self.DEFAULT_HF_TASK,
                model=self.model_name,
                tokenizer=self.tokenizer_name,
                aggregation_strategy=self.aggregation_strategy,
                device=device,
            )
            logger.info(f"Successfully loaded {self.model_name}")
        except Exception:
            logger.exception(f"Failed to load model {self.model_name}")
            raise

        # Resolve deferred tokenizer chunker using the pipeline's tokenizer
        from presidio_analyzer.chunkers import TokenizerBasedTextChunker

        if (
            isinstance(self.text_chunker, TokenizerBasedTextChunker)
            and self.text_chunker.is_deferred
        ):
            self.text_chunker.resolve(self.ner_pipeline.tokenizer)

    def _normalize_label(self, label: str) -> str:
        """Normalize label by removing prefixes like B-/I-/U-/L-.

        This method strips the prefix so that label_mapping can correctly
        map to Presidio entities.

        :param label: The raw label from the model.
        :return: Normalized label.
        """
        if isinstance(label, str):
            for prefix in self.label_prefixes:
                if label.startswith(prefix):
                    return label[len(prefix) :]
        return label

    def _predict_chunk(self, chunk_text: str) -> List[RecognizerResult]:
        """Perform NER prediction on a single text chunk.

        This is a callback method used by the CharacterBasedTextChunker.

        :param chunk_text: The chunk of text to analyze.
        :return: List of RecognizerResult objects.
        """
        chunk_results = []
        # Run inference on the chunk
        try:
            preds = self.ner_pipeline(chunk_text)
        except Exception as e:
            logger.warning(f"NER prediction failed for chunk: {e}", exc_info=True)
            return []

        # Helper to process a single prediction dictionary
        def process_pred(pred: Dict[str, Any]) -> None:
            """Convert a single HuggingFace prediction dict to RecognizerResult."""
            raw_label = pred.get("entity_group") or pred.get("entity")
            if not raw_label:
                return

            model_label = self._normalize_label(raw_label)

            presidio_entity = self.label_mapping.get(model_label)
            if not presidio_entity:
                # If label is not mapped, use the model's label as is. This allows
                # discovering entities not explicitly defined in the mapping.
                presidio_entity = model_label

            raw_score = pred.get("score", 0.0)
            try:
                score = float(raw_score)
            except (TypeError, ValueError):
                logger.warning("Failed to convert score to float: %r", raw_score)
                return

            if score < self.threshold:
                return

            start = pred.get("start")
            end = pred.get("end")
            if start is None or end is None:
                return

            if raw_label == model_label:
                textual_explanation = (
                    f"Identified as {presidio_entity} by {self.model_name} "
                    f"(label: {raw_label})"
                )
            else:
                textual_explanation = (
                    f"Identified as {presidio_entity} by {self.model_name} "
                    f"(original label: {raw_label}, normalized: {model_label})"
                )

            explanation = AnalysisExplanation(
                recognizer=self.name,
                original_score=score,
                textual_explanation=textual_explanation,
            )

            chunk_results.append(
                RecognizerResult(
                    entity_type=presidio_entity,
                    start=start,
                    end=end,
                    score=score,
                    analysis_explanation=explanation,
                )
            )

        # Validate preds is a list before iterating
        if not isinstance(preds, list):
            logger.warning("Unexpected pipeline output type: %s", type(preds))
            return []

        for pred in preds:
            if isinstance(pred, dict):
                process_pred(pred)
            else:
                logger.warning("Unexpected prediction item type: %s", type(pred))

        return chunk_results

    def analyze(
        self,
        text: str,
        entities: List[str],
        nlp_artifacts: Optional[NlpArtifacts] = None,
    ) -> List[RecognizerResult]:
        """Analyze text for NER entities using HuggingFace model.

        This method uses the CharacterBasedTextChunker to handle long texts
        and ignores nlp_artifacts (spaCy results) to bypass tokenizer alignment issues.

        :param text: The text to analyze
        :param entities: List of entity types to detect
        :param nlp_artifacts: Ignored (spaCy artifacts not used)
        :return: List of RecognizerResult with detected entities
        """
        if not text or not text.strip():
            return []

        # Defensive guard for entities input
        entities = entities or []

        if not self.model_name:
            raise ValueError(
                "model_name must be specified to analyze text using "
                "HuggingFaceNerRecognizer. Specify model_name when instantiating "
                "HuggingFaceNerRecognizer or in default_recognizers.yaml."
            )

        if not self.ner_pipeline:
            self.load()

        # Use the standard predict_with_chunking method from BaseTextChunker
        # This handles chunking, processing, and duplicating/merging results
        results = self.text_chunker.predict_with_chunking(
            text=text,
            predict_func=self._predict_chunk,
        )

        # Filter policy:
        # 1. If an entity is requested, it is always kept.
        # 2. If it's a known 'supported' entity but NOT requested, it is filtered out.
        # 3. If it's an unmapped/unexpected entity, it is kept for Discovery.
        if entities:
            requested = set(entities)
            supported = set(self.supported_entities)
            results = [
                r
                for r in results
                if (r.entity_type in requested) or (r.entity_type not in supported)
            ]

        return results
