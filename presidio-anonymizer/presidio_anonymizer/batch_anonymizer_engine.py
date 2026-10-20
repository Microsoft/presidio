import collections
from typing import Any, Dict, Iterable, List, Optional, Union

from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import (
    DictRecognizerResult,
    InvalidParamError,
    RecognizerResult,
)


class BatchAnonymizerEngine:
    """
    BatchAnonymizerEngine class.

    A class that provides functionality to anonymize in batches.
    :param anonymizer_engine: An instance of the AnonymizerEngine class.
    """

    def __init__(self, anonymizer_engine: Optional[AnonymizerEngine] = None):
        self.anonymizer_engine = anonymizer_engine or AnonymizerEngine()

    def anonymize_list(
        self,
        texts: List[Optional[Union[str, bool, int, float]]],
        recognizer_results_list: List[List[RecognizerResult]],
        **kwargs,
    ) -> List[Union[str, Any]]:
        """
        Anonymize a list of strings.

        :param texts: List containing the texts to be anonymized (original texts).
            Items with a `type` not in `(str, bool, int, float)` will not be anonymized.
        :param recognizer_results_list: A list of lists of RecognizerResult,
        the output of the AnalyzerEngine on each text in the list.
        :param kwargs: Additional kwargs for the `AnonymizerEngine.anonymize` method
        :raises InvalidParamError: If the length of texts does not match the
            length of recognizer_results_list.
        """
        return_list = []
        if not recognizer_results_list:
            recognizer_results_list = [[] for _ in range(len(texts))]
        elif len(texts) != len(recognizer_results_list):
            raise InvalidParamError(
                f"Invalid input, the number of texts ({len(texts)}) must match the "
                f"number of recognizer results ({len(recognizer_results_list)})."
            )
        for text, recognizer_results in zip(texts, recognizer_results_list):
            if type(text) in (str, bool, int, float):
                res = self.anonymizer_engine.anonymize(
                    text=str(text), analyzer_results=recognizer_results, **kwargs
                )
                return_list.append(res.text)
            else:
                return_list.append(text)

        return return_list

    def anonymize_dict(
        self, analyzer_results: Iterable[DictRecognizerResult], **kwargs
    ) -> Dict[str, str]:
        """
        Anonymize values in a dictionary.

        :param analyzer_results: Iterator of `DictRecognizerResult`
        containing the output of the AnalyzerEngine.analyze_dict on the input text.
        :param kwargs: Additional kwargs for the `AnonymizerEngine.anonymize` method
        """

        return_dict = {}
        for result in analyzer_results:
            if isinstance(result.value, dict):
                resp = self.anonymize_dict(
                    analyzer_results=result.recognizer_results, **kwargs
                )
                return_dict[result.key] = resp

            elif isinstance(result.value, str):
                resp = self.anonymizer_engine.anonymize(
                    text=result.value,
                    analyzer_results=result.recognizer_results,
                    **kwargs,
                )
                return_dict[result.key] = resp.text

            elif isinstance(result.value, collections.abc.Iterable):
                anonymize_response = self.anonymize_list(
                    texts=result.value,
                    recognizer_results_list=result.recognizer_results,
                    **kwargs,
                )
                return_dict[result.key] = anonymize_response
            else:
                return_dict[result.key] = result.value
        return return_dict
