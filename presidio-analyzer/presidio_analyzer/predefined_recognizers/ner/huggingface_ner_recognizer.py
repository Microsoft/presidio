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

try:
    from optimum.pipelines import pipeline as optimum_pipeline
except ImportError:
    optimum_pipeline = None


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
    # Keys that transformers.pipeline() accepts as top-level arguments and also
    # forwards itself to from_pretrained(); they must not be inside model_kwargs.
    TORCH_PIPELINE_HUB_KWARGS = ("revision", "token", "trust_remote_code")
    # Keys the ort path must also hand to optimum's pipeline() so the tokenizer
    # is fetched from the same revision / with the same credentials as the
    # model. These are top-level pipeline() arguments ...
    ORT_TOKENIZER_HUB_KWARGS = ("revision", "token", "trust_remote_code")
    # ... and these go through the pipeline's model_kwargs, which transformers
    # copies into the tokenizer load (the model is already an instance here).
    ORT_TOKENIZER_LOAD_KWARGS = ("cache_dir", "local_files_only")

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
        backend: str = "torch",
        **model_kwargs,
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
        :param device: Device to use ("torch" backend only). Accepts:
            - "cpu" or -1 for CPU
            - "cuda" or "cuda:N" or int N for GPU
            - None for auto-detection (GPU if available, else CPU)
            Defaults to None. Ignored by the "ort" backend — select
            hardware there via the `provider` model kwarg.
        :param chunk_overlap: Number of characters to overlap between chunks.
        :param chunk_size: Maximum number of characters per chunk.
        :param tokenizer_name: Name of the tokenizer. Defaults to model_name.
        :param text_chunker: Text chunking strategy. Accepts a BaseTextChunker
            instance. If None, uses CharacterBasedTextChunker with provided
            chunk_size and chunk_overlap. When loaded from YAML, the registry
            loader converts the ``text_chunker`` dict to a chunker instance
            automatically.
        :param label_prefixes: List of label prefixes to strip (e.g., B-, I-).
        :param backend: Inference backend to use.
            - "torch" (default): PyTorch via transformers pipeline.
              Requires: torch, transformers.
            - "ort": ONNX Runtime via optimum.
              Requires: optimum, optimum-onnx[onnxruntime]. optimum itself
              depends on torch, so torch is installed either way.
              For NVIDIA GPU, install `onnxruntime-gpu` and pass
              `provider="CUDAExecutionProvider"` via model_kwargs.
        :param model_kwargs: Additional keyword arguments forwarded to the
            underlying model loader. Which keys are valid depends on the
            backend:
            - Both backends: `revision`, `token`, `trust_remote_code`,
              `cache_dir`, `subfolder`, `local_files_only`.
            - "ort" only: `file_name`, `provider`, `provider_options`,
              `session_options`, `export`.
            For "torch", `revision`, `token` and `trust_remote_code` are
            passed to `transformers.pipeline` as top-level arguments and the
            rest as `model_kwargs=`. For "ort", everything is passed to
            `ORTModel.from_pretrained` directly, so the keys scope to the
            model loader only. This matters for mixed-layout repos where
            ONNX files live under `onnx/` while tokenizer and config live at
            the repo root.
        :raises ValueError: If `backend` is not one of "torch" or "ort".
        :raises ImportError: If required libraries for the chosen backend
            are not installed.
        """
        if backend not in ("torch", "ort"):
            raise ValueError(
                f"Unsupported backend: {backend!r}. Expected 'torch' or 'ort'."
            )
        self.backend = backend

        # Early check for required dependencies
        if hf_pipeline is None:
            raise ImportError(
                "transformers is not installed. Please install it "
                "(pip install 'presidio-analyzer[transformers]') "
                "to use this recognizer."
            )
        if self.backend == "torch":
            if torch is None:
                raise ImportError(
                    "torch is not installed. Please install it "
                    "(pip install 'presidio-analyzer[transformers]') "
                    "to use the 'torch' backend."
                )
        elif self.backend == "ort":
            if optimum_pipeline is None:
                raise ImportError(
                    "optimum is not installed. Please install it "
                    "(pip install 'presidio-analyzer[onnxruntime]') "
                    "to use the 'ort' backend."
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
        if self.backend == "ort":
            if device not in (None, "cpu", -1):
                logger.warning(
                    "The 'device' parameter is ignored by the 'ort' backend. "
                    "Select hardware via the 'provider' model kwarg instead, "
                    "e.g. provider='CUDAExecutionProvider'."
                )
            # ort selects hardware via the execution provider, not device.
            # Skip parsing/auto-detection and keep self.device consistent
            # with actual behavior.
            self.device = -1
        else:
            self.device = self._parse_device(device)
        self.label_prefixes = label_prefixes or ["B-", "I-", "U-", "L-"]
        self.ner_pipeline = None
        self.model_kwargs = model_kwargs

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
        1. Backend selection (torch or ort)
        2. Hardware acceleration setup (CUDA validation and fallback for
           the torch backend; provider selection for ort via model_kwargs)
        3. Lazy-loading of the heavyweight ML pipeline.

        :raises ValueError: If model_name is not set
        """
        if self.ner_pipeline is not None:
            return

        if not self.model_name:
            raise ValueError(
                "model_name must be set before calling load(). "
                "Pass it to __init__() or set it directly."
            )

        if self.backend == "torch":
            self._load_torch_pipeline()
        else:
            self._load_ort_pipeline()

        # Resolve deferred tokenizer chunker using the pipeline's tokenizer
        from presidio_analyzer.chunkers import TokenizerBasedTextChunker

        if (
            isinstance(self.text_chunker, TokenizerBasedTextChunker)
            and self.text_chunker.is_deferred
        ):
            self.text_chunker.resolve(self.ner_pipeline.tokenizer)

    def _load_torch_pipeline(self) -> None:
        """Load the NER pipeline using PyTorch backend."""
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

        logger.info(
            f"Loading HuggingFace model: {self.model_name}, "
            f"backend=torch, device={device}"
        )

        # transformers.pipeline() spreads its own hub kwargs (revision, token,
        # trust_remote_code) next to model_kwargs when loading config and
        # model, so passing them inside model_kwargs raises "multiple values
        # for keyword argument". Lift them to top-level pipeline() arguments.
        model_kwargs = dict(self.model_kwargs)
        hub_kwargs = {
            key: model_kwargs.pop(key)
            for key in self.TORCH_PIPELINE_HUB_KWARGS
            if key in model_kwargs
        }

        try:
            self.ner_pipeline = hf_pipeline(
                self.DEFAULT_HF_TASK,
                model=self.model_name,
                tokenizer=self.tokenizer_name,
                aggregation_strategy=self.aggregation_strategy,
                device=device,
                model_kwargs=model_kwargs or None,
                **hub_kwargs,
            )
            logger.info(f"Successfully loaded {self.model_name}")
        except Exception:
            logger.exception(f"Failed to load model {self.model_name}")
            raise

    def _load_ort_pipeline(self) -> None:
        """Load the NER pipeline using optimum's ONNX Runtime backend.

        Pre-loads ``ORTModelForTokenClassification`` explicitly so that
        model_kwargs like ``subfolder`` and ``file_name`` are scoped to the
        model loader only. Passing them at the pipeline level leaks them
        into transformers' config/tokenizer loading, which breaks
        mixed-layout repos (e.g. onnx-community/*, Xenova/*) where the ONNX
        file lives under ``onnx/`` but config/tokenizer live at the repo
        root.
        """
        try:
            from optimum.onnxruntime import ORTModelForTokenClassification
        except ImportError as e:
            raise ImportError(
                "optimum-onnx is not installed. Please install it "
                "(pip install 'presidio-analyzer[onnxruntime]') "
                "to use the 'ort' backend."
            ) from e

        logger.info(f"Loading HuggingFace model: {self.model_name}, backend=ort")

        # The tokenizer is loaded by name inside the pipeline, so hub kwargs
        # that select a revision, authenticate, or force offline/cached loading
        # must reach it as well, or a pinned/private/offline repo loads the
        # model and then fails (or drifts) on the tokenizer fetch.
        tokenizer_hub_kwargs = {
            key: self.model_kwargs[key]
            for key in self.ORT_TOKENIZER_HUB_KWARGS
            if key in self.model_kwargs
        }
        tokenizer_load_kwargs = {
            key: self.model_kwargs[key]
            for key in self.ORT_TOKENIZER_LOAD_KWARGS
            if key in self.model_kwargs
        }

        try:
            model = ORTModelForTokenClassification.from_pretrained(
                self.model_name, **self.model_kwargs
            )
            self.ner_pipeline = optimum_pipeline(
                self.DEFAULT_HF_TASK,
                model=model,
                tokenizer=self.tokenizer_name,
                aggregation_strategy=self.aggregation_strategy,
                accelerator="ort",
                model_kwargs=tokenizer_load_kwargs or None,
                **tokenizer_hub_kwargs,
            )
            logger.info(f"Successfully loaded {self.model_name} with ort backend")
        except Exception:
            logger.exception(f"Failed to load model {self.model_name} with ort backend")
            raise

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
