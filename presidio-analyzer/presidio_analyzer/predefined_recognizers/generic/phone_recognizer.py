from typing import List, Optional

import phonenumbers
from phonenumbers.phonenumberutil import NumberParseException

from presidio_analyzer import (
    AnalysisExplanation,
    EntityRecognizer,
    LocalRecognizer,
    RecognizerResult,
)
from presidio_analyzer.nlp_engine import NlpArtifacts


class PhoneRecognizer(LocalRecognizer):
    """Recognize multi-regional phone numbers.

     Using python-phonenumbers, along with fixed and regional context words.
    :param context: Base context words for enhancing the assurance scores.
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param supported_regions: The regions for phone number matching and validation
    :param leniency: The strictness level of phone number formats.
    Accepts values from 0 to 3, where 0 is the lenient and 3 is the most strictest.
    """

    SCORE = 0.4
    CONTEXT = ["phone", "number", "telephone", "cell", "cellphone", "mobile", "call"]
    DEFAULT_SUPPORTED_REGIONS = ("US", "GB", "DE", "FR", "IL", "IN", "CA", "BR")

    def __init__(
        self,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "PHONE_NUMBER",
        # For all regions, use phonenumbers.SUPPORTED_REGIONS
        supported_regions=DEFAULT_SUPPORTED_REGIONS,
        leniency: Optional[int] = 1,
        name: Optional[str] = None,
    ):
        context = context if context else self.CONTEXT
        self.supported_regions = supported_regions
        self.leniency = leniency
        super().__init__(
            supported_entities=[supported_entity],
            supported_language=supported_language,
            context=context,
            name=name,
        )

    def load(self) -> None:  # noqa: D102
        pass

    def analyze(
        self, text: str, entities: List[str], nlp_artifacts: NlpArtifacts = None
    ) -> List[RecognizerResult]:
        """Analyzes text to detect phone numbers using python-phonenumbers.

        Iterates over entities, fetching regions, then matching regional
        phone number patterns against the text.
        :param text: Text to be analyzed
        :param entities: Entities this recognizer can detect
        :param nlp_artifacts: Additional metadata from the NLP engine
        :return: List of phone numbers RecognizerResults
        """
        results = []
        for region in self.supported_regions:
            for match in phonenumbers.PhoneNumberMatcher(
                text, region, leniency=self.leniency
            ):
                try:
                    parsed_number = phonenumbers.parse(text[match.start : match.end])
                    region = phonenumbers.region_code_for_number(parsed_number)
                    results += [
                        self._get_recognizer_result(match, text, region, nlp_artifacts)
                    ]
                except NumberParseException:
                    results += [
                        self._get_recognizer_result(match, text, region, nlp_artifacts)
                    ]

        return EntityRecognizer.remove_duplicates(results)

    def _get_recognizer_result(self, match, text, region, nlp_artifacts):
        result = RecognizerResult(
            entity_type=self.supported_entities[0],
            start=match.start,
            end=match.end,
            score=self.SCORE,
            analysis_explanation=self._get_analysis_explanation(region),
            recognition_metadata={
                RecognizerResult.RECOGNIZER_NAME_KEY: self.name,
                RecognizerResult.RECOGNIZER_IDENTIFIER_KEY: self.id,
            },
        )

        return result

    def _get_analysis_explanation(self, region):
        return AnalysisExplanation(
            recognizer=PhoneRecognizer.__name__,
            original_score=self.SCORE,
            textual_explanation=f"Recognized as {region} region phone number, "
            f"using PhoneRecognizer",
        )
