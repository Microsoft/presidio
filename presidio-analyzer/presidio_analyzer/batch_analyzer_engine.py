import logging
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple, Union

from presidio_analyzer import AnalyzerEngine, DictAnalyzerResult, RecognizerResult
from presidio_analyzer.nlp_engine import NlpArtifacts

logger = logging.getLogger("presidio-analyzer")


class BatchAnalyzerEngine:
    """
    Batch analysis of documents (tables, lists, dicts).

    Wrapper class to run Presidio Analyzer Engine on multiple values,
    either lists/iterators of strings, or dictionaries.

    :param analyzer_engine: AnalyzerEngine instance to use
    for handling the values in those collections.
    """

    def __init__(self, analyzer_engine: Optional[AnalyzerEngine] = None):
        self.analyzer_engine = analyzer_engine
        if not analyzer_engine:
            self.analyzer_engine = AnalyzerEngine()

    def analyze_iterator(
        self,
        texts: Iterable[Union[str, bool, float, int]],
        language: str,
        batch_size: int = 1,
        n_process: int = 1,
        **kwargs,
    ) -> List[List[RecognizerResult]]:
        """
        Analyze an iterable of strings.

        :param texts: An list containing strings to be analyzed.
        :param language: Input language
        :param batch_size: Batch size to process in a single iteration
        :param n_process: Number of processors to use. Defaults to `1`
        :param kwargs: Additional parameters for the `AnalyzerEngine.analyze` method.
        (default value depends on the nlp engine implementation)
        """

        # validate types
        texts = self._validate_types(texts)

        # Process the texts as batch for improved performance
        nlp_artifacts_batch: Iterator[Tuple[str, NlpArtifacts]] = (
            self.analyzer_engine.nlp_engine.process_batch(
                texts=texts,
                language=language,
                batch_size=batch_size,
                n_process=n_process,
            )
        )

        list_results = []
        for text, nlp_artifacts in nlp_artifacts_batch:
            results = self.analyzer_engine.analyze(
                text=str(text), nlp_artifacts=nlp_artifacts, language=language, **kwargs
            )

            list_results.append(results)

        return list_results

    def analyze_dict(
        self,
        input_dict: Dict[str, Union[Any, Iterable[Any]]],
        language: str,
        keys_to_skip: Optional[List[str]] = None,
        batch_size: int = 1,
        n_process: int = 1,
        **kwargs,
    ) -> Iterator[DictAnalyzerResult]:
        """
        Analyze a dictionary of keys (strings) and values/iterable of values.

        Non-string values are returned as is.

        :param input_dict: The input dictionary for analysis
        :param language: Input language
        :param keys_to_skip: Keys to ignore during analysis. A nested key is
        given as its dot-separated path from the top level, e.g. "key_a.key_a1"
        :param batch_size: Batch size to process in a single iteration
        :param n_process: Number of processors to use. Defaults to `1`

        :param kwargs: Additional keyword arguments
        for the `AnalyzerEngine.analyze` method.
        Use this to pass arguments to the analyze method,
        such as `ad_hoc_recognizers`, `context`, `return_decision_process`.
        See `AnalyzerEngine.analyze` for the full list.
        """

        context = []
        if "context" in kwargs:
            context = kwargs["context"]
            del kwargs["context"]

        if not keys_to_skip:
            keys_to_skip = []

        for key, value in input_dict.items():
            if not value or key in keys_to_skip:
                yield DictAnalyzerResult(key=key, value=value, recognizer_results=[])
                continue  # skip this key as requested

            # Add the key as an additional context
            specific_context = context[:]
            specific_context.append(key)

            if type(value) in (str, int, bool, float):
                results: List[RecognizerResult] = self.analyzer_engine.analyze(
                    text=str(value), language=language, context=[key], **kwargs
                )
            elif isinstance(value, dict):
                new_keys_to_skip = self._get_nested_keys_to_skip(key, keys_to_skip)
                results = self.analyze_dict(
                    input_dict=value,
                    language=language,
                    context=specific_context,
                    keys_to_skip=new_keys_to_skip,
                    **kwargs,
                )
            elif isinstance(value, Iterable):
                # Recursively iterate nested dicts

                results: List[List[RecognizerResult]] = self.analyze_iterator(
                    texts=value,
                    language=language,
                    context=specific_context,
                    n_process=n_process,
                    batch_size=batch_size,
                    **kwargs,
                )
            else:
                raise ValueError(f"type {type(value)} is unsupported.")

            yield DictAnalyzerResult(key=key, value=value, recognizer_results=results)

    @staticmethod
    def _validate_types(value_iterator: Iterable[Any]) -> Iterator[Any]:
        for val in value_iterator:
            if val and type(val) not in (int, float, bool, str):
                err_msg = (
                    "Analyzer.analyze_iterator only works "
                    "on primitive types (int, float, bool, str). "
                    "Lists of objects are not yet supported."
                )
                logger.error(err_msg)
                raise ValueError(err_msg)
            yield val

    @staticmethod
    def _get_nested_keys_to_skip(key, keys_to_skip):
        prefix = f"{key}."
        return [k.removeprefix(prefix) for k in keys_to_skip if k.startswith(prefix)]
