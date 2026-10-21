import json
import logging
from typing import Dict, List, Optional

from presidio_analyzer import (
    AnalysisExplanation,
    LocalRecognizer,
    RecognizerResult,
)
from presidio_analyzer.chunkers import BaseTextChunker
from presidio_analyzer.nlp_engine import (
    NerModelConfiguration,
    NlpArtifacts,
    device_detector,
)

try:
    from gliner import GLiNER, GLiNERConfig
except ImportError:
    GLiNER = None
    GLiNERConfig = None

logger = logging.getLogger("presidio-analyzer")


class GLiNERRecognizer(LocalRecognizer):
    """GLiNER model based entity recognizer."""

    def __init__(
        self,
        supported_entities: Optional[List[str]] = None,
        name: str = "GLiNERRecognizer",
        supported_language: str = "en",
        version: str = "0.0.1",
        context: Optional[List[str]] = None,
        entity_mapping: Optional[Dict[str, str]] = None,
        model_name: str = "urchade/gliner_multi_pii-v1",
        flat_ner: bool = True,
        multi_label: bool = False,
        threshold: float = 0.30,
        map_location: Optional[str] = None,
        text_chunker: Optional[BaseTextChunker] = None,
        chunk_size: int = 250,
        chunk_overlap: int = 50,
        load_onnx_model: bool = False,
        onnx_model_file: str = "model.onnx",
        inference_batch_size: int = 8,
        **model_kwargs,
    ):
        """GLiNER model based entity recognizer.

        The model is based on the GLiNER library.

        :param supported_entities: List of supported entities for this recognizer.
        If None, all entities in Presidio's default configuration will be used.
        see `NerModelConfiguration`
        :param name: Name of the recognizer
        :param supported_language: Language code to use for the recognizer
        :param version: Version of the recognizer
        :param context: N/A for this recognizer
        :param model_name: The name of the GLiNER model to load
        :param flat_ner: Whether to use flat NER or not (see GLiNER's documentation)
        :param multi_label: Whether to use multi-label classification or not
        (see GLiNER's documentation)
        :param threshold: The threshold for the model's output
        (see GLiNER's documentation)
        :param map_location: The device to use for the model.
            If None, will auto-detect GPU or use CPU.
        :param text_chunker: Text chunking strategy. Accepts a BaseTextChunker
            instance. If None, uses CharacterBasedTextChunker with provided
            chunk_size and chunk_overlap. When loaded from YAML, the registry
            loader converts the ``text_chunker`` dict to a chunker instance
            automatically.
        :param chunk_size: Maximum number of characters per chunk.
        :param chunk_overlap: Number of characters to overlap between chunks.
        :param load_onnx_model: Whether to load the model using ONNX Runtime.
            If True, uses ONNX Runtime backend which supports CPUs without AVX2.
            Requires onnxruntime to be installed. Default is False.
        :param onnx_model_file: The name of the ONNX model file to load.
            Only used when load_onnx_model is True. This is passed directly to
            GLiNER.from_pretrained(). GLiNER looks for this file in the model
            directory (downloaded or cached model path). Default is "model.onnx".
        :param inference_batch_size: Batch size for GLiNER's inference method
            when using batch_analyze(). Controls the internal DataLoader batch
            size in GLiNER. Default is 8.
        :param model_kwargs: Additional keyword arguments to pass to
            GLiNER.from_pretrained(). This allows passing future parameters
            to the GLiNER model without explicit support in this recognizer.


        """

        if entity_mapping:
            if supported_entities:
                raise ValueError(
                    "entity_mapping and supported_entities cannot be used together"
                )

            self.model_to_presidio_entity_mapping = entity_mapping
        else:
            if not supported_entities:
                logger.info(
                    "No supported entities provided, "
                    "using default entities from NerModelConfiguration"
                )
                self.model_to_presidio_entity_mapping = (
                    NerModelConfiguration().model_to_presidio_entity_mapping
                )
            else:
                self.model_to_presidio_entity_mapping = {
                    entity: entity for entity in supported_entities
                }

        logger.info(f"Using entity mapping {json.dumps(entity_mapping, indent=2)}")
        supported_entities = list(set(self.model_to_presidio_entity_mapping.values()))
        self.model_name = model_name

        self.map_location = (
            map_location if map_location is not None else device_detector.get_device()
        )

        self.flat_ner = flat_ner
        self.multi_label = multi_label
        self.threshold = threshold
        self.load_onnx_model = load_onnx_model
        self.onnx_model_file = onnx_model_file
        self.inference_batch_size = inference_batch_size
        self.model_kwargs = model_kwargs

        # Initialize text chunker (instance or default)
        if text_chunker is not None:
            self.text_chunker = text_chunker
        else:
            from presidio_analyzer.chunkers import CharacterBasedTextChunker

            self.text_chunker = CharacterBasedTextChunker(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )

        self.gliner = None

        super().__init__(
            supported_entities=supported_entities,
            name=name,
            supported_language=supported_language,
            version=version,
            context=context,
        )

        self.gliner_labels = list(self.model_to_presidio_entity_mapping.keys())

    def load(self) -> None:
        """Load the GLiNER model."""
        if not GLiNER:
            raise ImportError("GLiNER is not installed. Please install it.")

        self.gliner = GLiNER.from_pretrained(
            self.model_name,
            map_location=self.map_location,
            load_onnx_model=self.load_onnx_model,
            onnx_model_file=self.onnx_model_file,
            **self.model_kwargs,
        )

        # Resolve deferred tokenizer chunker using the model's own tokenizer
        from presidio_analyzer.chunkers import TokenizerBasedTextChunker

        if (
            isinstance(self.text_chunker, TokenizerBasedTextChunker)
            and self.text_chunker.is_deferred
        ):
            tokenizer = self.gliner.data_processor.transformer_tokenizer
            self.text_chunker.resolve(tokenizer)

    def analyze(
        self,
        text: str,
        entities: List[str],
        nlp_artifacts: Optional[NlpArtifacts] = None,
    ) -> List[RecognizerResult]:
        """Analyze text to identify entities using a GLiNER model.

        :param text: The text to be analyzed
        :param entities: The list of entities this recognizer is requested to return
        :param nlp_artifacts: N/A for this recognizer
        """

        # combine the input labels as this model allows for ad-hoc labels
        labels = self.__create_input_labels(entities)

        # Process text with automatic chunking
        def predict_func(text: str) -> List[RecognizerResult]:
            # Get predictions from GLiNER (returns dicts)
            gliner_predictions = self.gliner.predict_entities(
                text=text,
                labels=labels,
                flat_ner=self.flat_ner,
                threshold=self.threshold,
                multi_label=self.multi_label,
            )

            # Convert dicts to RecognizerResult objects
            results = []
            for pred in gliner_predictions:
                presidio_entity = self.model_to_presidio_entity_mapping.get(
                    pred["label"], pred["label"]
                )

                # Filter by requested entities
                if entities and presidio_entity not in entities:
                    continue

                analysis_explanation = AnalysisExplanation(
                    recognizer=self.name,
                    original_score=pred["score"],
                    textual_explanation=f"Identified as {presidio_entity} by GLiNER",
                )

                results.append(
                    RecognizerResult(
                        entity_type=presidio_entity,
                        start=pred["start"],
                        end=pred["end"],
                        score=pred["score"],
                        analysis_explanation=analysis_explanation,
                    )
                )
            return results

        predictions = self.text_chunker.predict_with_chunking(
            text=text,
            predict_func=predict_func,
        )

        return predictions

    def _predict_batch_chunks(
        self,
        chunk_texts: List[str],
        labels: List[str],
        entities: List[str],
    ) -> List[List[RecognizerResult]]:
        """Perform GLiNER prediction on multiple text chunks in a single batch.

        Uses GLiNER's inference method for efficiency.

        :param chunk_texts: List of text chunks to analyze.
        :param labels: Labels to pass to GLiNER.
        :param entities: Requested entity types for filtering.
        :return: List of lists of RecognizerResult objects, one list per chunk.
        """
        try:
            batch_preds = self.gliner.inference(
                texts=chunk_texts,
                labels=labels,
                flat_ner=self.flat_ner,
                threshold=self.threshold,
                multi_label=self.multi_label,
                batch_size=self.inference_batch_size,
            )
        except Exception as e:
            logger.warning(
                f"Batch GLiNER prediction failed, falling back to sequential: {e}",
                exc_info=True,
            )
            # Fall back to sequential processing
            all_results = []
            for text in chunk_texts:
                gliner_predictions = self.gliner.predict_entities(
                    text=text,
                    labels=labels,
                    flat_ner=self.flat_ner,
                    threshold=self.threshold,
                    multi_label=self.multi_label,
                )
                results = self._convert_gliner_preds(gliner_predictions, entities)
                all_results.append(results)
            return all_results

        all_results = []
        for preds in batch_preds:
            results = self._convert_gliner_preds(preds, entities)
            all_results.append(results)

        return all_results

    def _convert_gliner_preds(
        self,
        gliner_predictions: List[Dict],
        entities: List[str],
    ) -> List[RecognizerResult]:
        """Convert GLiNER prediction dicts to RecognizerResult objects.

        :param gliner_predictions: List of prediction dicts from GLiNER.
        :param entities: Requested entity types for filtering.
        :return: List of RecognizerResult objects.
        """
        results = []
        for pred in gliner_predictions:
            presidio_entity = self.model_to_presidio_entity_mapping.get(
                pred["label"], pred["label"]
            )

            # Filter by requested entities
            if entities and presidio_entity not in entities:
                continue

            analysis_explanation = AnalysisExplanation(
                recognizer=self.name,
                original_score=pred["score"],
                textual_explanation=f"Identified as {presidio_entity} by GLiNER",
            )

            results.append(
                RecognizerResult(
                    entity_type=presidio_entity,
                    start=pred["start"],
                    end=pred["end"],
                    score=pred["score"],
                    analysis_explanation=analysis_explanation,
                )
            )
        return results

    def batch_analyze(
        self,
        texts: List[str],
        entities: List[str],
        nlp_artifacts_list: List[Optional[NlpArtifacts]],
    ) -> List[List[RecognizerResult]]:
        """Analyze multiple texts for entities using batch inference.

        Overrides the default sequential implementation to leverage
        GLiNER's inference method for efficiency.

        :param texts: List of texts to analyze
        :param entities: Entity types to detect
        :param nlp_artifacts_list: Parallel list of NLP artifacts (ignored)
        :return: List of results per text, aligned with input texts
        """
        if not texts:
            return []

        labels = self.__create_input_labels(entities)

        def predict_batch_func(chunk_texts):
            return self._predict_batch_chunks(chunk_texts, labels, entities)

        return self.text_chunker.predict_batch_with_chunking(
            texts=texts,
            predict_batch_func=predict_batch_func,
        )

    def __create_input_labels(self, entities):
        """Append the entities requested by the user to the list of labels if it's not there."""  # noqa: E501
        labels = list(self.gliner_labels)
        for entity in entities:
            if (
                entity not in self.model_to_presidio_entity_mapping.values()
                and entity not in self.gliner_labels
            ):
                labels.append(entity)
        return labels
