import datetime
import logging
import os
from typing import TYPE_CHECKING, Dict, List, Optional, Union

import regex as re

from presidio_analyzer import (
    AnalysisExplanation,
    EntityRecognizer,
    LocalRecognizer,
    Pattern,
    RecognizerResult,
)

if TYPE_CHECKING:
    from presidio_analyzer.nlp_engine import NlpArtifacts

logger = logging.getLogger("presidio-analyzer")

REGEX_TIMEOUT_SECONDS = int(os.environ.get("REGEX_TIMEOUT_SECONDS", 60))


class PatternRecognizer(LocalRecognizer):
    """
    PII entity recognizer using regular expressions or deny-lists.

    :param patterns: A list of patterns to detect
    :param deny_list: A list of words to detect,
    in case our recognizer uses a predefined list of words (deny list)
    :param context: list of context words
    :param deny_list_score: confidence score for a term
    identified using a deny-list
    :param global_regex_flags: regex flags to be used in regex matching,
    including deny-lists.
    :param country_code: Optional ISO 3166-1 alpha-2 country tag, forwarded
    to :class:`EntityRecognizer`. Lets custom recognizers declare a country
    without subclassing — typically used by ``from_dict`` and the
    corresponding YAML ``type: custom`` entries. Subclasses with a class-
    level :attr:`EntityRecognizer.COUNTRY_CODE` should leave this unset
    or pass the matching value.

    Country tagging may be declared at the class level via
    :attr:`EntityRecognizer.COUNTRY_CODE` (the canonical path for
    predefined recognizers) or per-instance via the ``country_code``
    constructor kwarg; see :class:`EntityRecognizer` for the full
    reconciliation rules.
    """

    def __init__(
        self,
        supported_entity: str,
        name: str = None,
        supported_language: str = "en",
        patterns: List[Pattern] = None,
        deny_list: List[str] = None,
        context: List[str] = None,
        deny_list_score: float = 1.0,
        global_regex_flags: Optional[int] = re.DOTALL | re.MULTILINE | re.IGNORECASE,
        version: str = "0.0.1",
        country_code: Optional[str] = None,
    ):
        if not supported_entity:
            raise ValueError("Pattern recognizer should be initialized with entity")

        if not patterns and not deny_list:
            raise ValueError(
                "Pattern recognizer should be initialized with patterns"
                " or with deny list"
            )

        super().__init__(
            supported_entities=[supported_entity],
            supported_language=supported_language,
            name=name,
            version=version,
            country_code=country_code,
        )
        if patterns is None:
            self.patterns = []
        else:
            self.patterns = patterns
        self.context = context
        self.deny_list_score = deny_list_score
        self.global_regex_flags = global_regex_flags

        if deny_list:
            deny_list_pattern = self._deny_list_to_regex(deny_list)
            self.patterns.append(deny_list_pattern)
            self.deny_list = deny_list
        else:
            self.deny_list = []

    def load(self):  # noqa: D102
        pass

    def analyze(
        self,
        text: str,
        entities: List[str],
        nlp_artifacts: Optional["NlpArtifacts"] = None,
        regex_flags: Optional[int] = None,
    ) -> List[RecognizerResult]:
        """
        Analyzes text to detect PII using regular expressions or deny-lists.

        :param text: Text to be analyzed
        :param entities: Entities this recognizer can detect
        :param nlp_artifacts: Output values from the NLP engine
        :param regex_flags: regex flags to be used in regex matching
        :return:
        """
        results = []

        if self.patterns:
            pattern_result = self.__analyze_patterns(text, regex_flags)
            results.extend(pattern_result)

        return results

    def _deny_list_to_regex(self, deny_list: List[str]) -> Pattern:
        """
        Convert a list of words to a matching regex.

        To be analyzed by the analyze method as any other regex patterns.

        :param deny_list: the list of words to detect
        :return:the regex of the words for detection
        """

        # Escape deny list elements as preparation for regex
        escaped_deny_list = [re.escape(element) for element in deny_list]
        regex = r"(?:^|(?<=\W))(" + "|".join(escaped_deny_list) + r")(?:(?=\W)|$)"
        return Pattern(name="deny_list", regex=regex, score=self.deny_list_score)

    def validate_result(self, pattern_text: str) -> Optional[bool]:
        """
        Validate the pattern logic e.g., by running checksum on a detected pattern.

        :param pattern_text: the text to validated.
        Only the part in text that was detected by the regex engine
        (the pattern's capture group if set, otherwise the whole match)
        :return: A bool indicating whether the validation was successful.
        """
        return None

    def invalidate_result(self, pattern_text: str) -> Optional[bool]:
        """
        Logic to check for result invalidation by running pruning logic.

        For example, each SSN number group should not consist of all the same digits.

        :param pattern_text: the text to validated.
        Only the part in text that was detected by the regex engine
        (the pattern's capture group if set, otherwise the whole match)
        :return: A bool indicating whether the result is invalidated
        """
        return None

    @staticmethod
    def build_regex_explanation(
        recognizer_name: str,
        pattern_name: str,
        pattern: str,
        original_score: float,
        validation_result: bool,
        regex_flags: int,
    ) -> AnalysisExplanation:
        """
        Construct an explanation for why this entity was detected.

        :param recognizer_name: Name of recognizer detecting the entity
        :param pattern_name: Regex pattern name which detected the entity
        :param pattern: Regex pattern logic
        :param original_score: Score given by the recognizer
        :param validation_result: Whether validation was used and its result
        :param regex_flags: Regex flags used in the regex matching
        :return: Analysis explanation
        """
        textual_explanation = (
            f"Detected by `{recognizer_name}` using pattern `{pattern_name}`"
        )

        explanation = AnalysisExplanation(
            recognizer=recognizer_name,
            original_score=original_score,
            pattern_name=pattern_name,
            pattern=pattern,
            validation_result=validation_result,
            regex_flags=regex_flags,
            textual_explanation=textual_explanation,
        )
        return explanation

    @staticmethod
    def __regex_has_group(compiled_regex, capture_group: Union[int, str]) -> bool:
        if isinstance(capture_group, str):
            return capture_group in compiled_regex.groupindex
        return capture_group <= compiled_regex.groups

    def __analyze_patterns(
        self, text: str, flags: int = None
    ) -> List[RecognizerResult]:
        """
        Evaluate all patterns in the provided text.

        Including words in the provided deny-list

        :param text: text to analyze
        :param flags: regex flags
        :return: A list of RecognizerResult
        """
        flags = flags if flags else self.global_regex_flags
        results = []
        for pattern in self.patterns:
            match_start_time = datetime.datetime.now()

            # Compile regex if flags differ from flags the regex was compiled with
            if not pattern.compiled_regex or pattern.compiled_with_flags != flags:
                pattern.compiled_with_flags = flags
                pattern.compiled_regex = re.compile(pattern.regex, flags=flags)

            # Flags such as re.VERBOSE can change the groups in a regex
            if pattern.capture_group is not None and not self.__regex_has_group(
                pattern.compiled_regex, pattern.capture_group
            ):
                logger.warning(
                    "Regex pattern '%s' has no capture group %r "
                    "when compiled with the regex flags in use, skipping.",
                    pattern.name,
                    pattern.capture_group,
                )
                continue
            group = 0 if pattern.capture_group is None else pattern.capture_group

            try:
                matches = pattern.compiled_regex.finditer(
                    text, timeout=REGEX_TIMEOUT_SECONDS
                )
                match_time = datetime.datetime.now() - match_start_time
                logger.debug(
                    "--- match_time[%s]: %.6f seconds",
                    pattern.name,
                    match_time.total_seconds(),
                )

                for match in matches:
                    start, end = match.span(group)
                    current_match = text[start:end]

                    # Skip empty results, including a capture group that did not
                    # participate in the match (its span is (-1, -1))
                    if current_match == "":
                        continue

                    score = pattern.score

                    validation_result = self.validate_result(current_match)
                    description = self.build_regex_explanation(
                        self.name,
                        pattern.name,
                        pattern.regex,
                        score,
                        validation_result,
                        flags,
                    )
                    pattern_result = RecognizerResult(
                        entity_type=self.supported_entities[0],
                        start=start,
                        end=end,
                        score=score,
                        analysis_explanation=description,
                        recognition_metadata={
                            RecognizerResult.RECOGNIZER_NAME_KEY: self.name,
                            RecognizerResult.RECOGNIZER_IDENTIFIER_KEY: self.id,
                        },
                    )

                    if validation_result is not None:
                        if validation_result:
                            pattern_result.score = EntityRecognizer.MAX_SCORE
                        else:
                            pattern_result.score = EntityRecognizer.MIN_SCORE

                    invalidation_result = self.invalidate_result(current_match)
                    if invalidation_result is not None and invalidation_result:
                        pattern_result.score = EntityRecognizer.MIN_SCORE

                    if pattern_result.score > EntityRecognizer.MIN_SCORE:
                        results.append(pattern_result)

                    # Update analysis explanation score after validation or invalidation
                    description.score = pattern_result.score
            except TimeoutError:
                logger.warning(
                    "Regex pattern '%s' timed out after %s seconds, skipping.",
                    pattern.name,
                    REGEX_TIMEOUT_SECONDS,
                    exc_info=True,
                )

        results = EntityRecognizer.remove_duplicates(results)
        return results

    def to_dict(self) -> Dict:
        """Serialize instance into a dictionary."""
        return_dict = super().to_dict()

        return_dict["patterns"] = [pat.to_dict() for pat in self.patterns]
        return_dict["deny_list"] = self.deny_list
        return_dict["context"] = self.context
        return_dict["supported_entity"] = return_dict["supported_entities"][0]
        del return_dict["supported_entities"]

        return return_dict

    @classmethod
    def from_dict(cls, entity_recognizer_dict: Dict) -> "PatternRecognizer":
        """Create instance from a serialized dict."""
        # Make a copy to avoid mutating the input
        entity_recognizer_dict = entity_recognizer_dict.copy()

        patterns = entity_recognizer_dict.get("patterns")
        if patterns:
            patterns_list = [Pattern.from_dict(pat) for pat in patterns]
            entity_recognizer_dict["patterns"] = patterns_list

        # Transform supported_entities (plural) to supported_entity (singular)
        # PatternRecognizer only accepts supported_entity (singular)
        if (
            "supported_entity" in entity_recognizer_dict
            and "supported_entities" in entity_recognizer_dict
        ):
            raise ValueError(
                "Both 'supported_entity' and 'supported_entities' "
                "are present in the input dictionary. "
                "Only one should be provided."
            )
        if "supported_entities" in entity_recognizer_dict:
            supported_entities = entity_recognizer_dict.pop("supported_entities")
            if supported_entities and len(supported_entities) > 0:
                # Only set if not already present
                if "supported_entity" not in entity_recognizer_dict:
                    entity_recognizer_dict["supported_entity"] = supported_entities[0]

        return cls(**entity_recognizer_dict)
