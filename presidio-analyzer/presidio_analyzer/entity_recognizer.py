import logging
from abc import abstractmethod
from itertools import groupby
from typing import TYPE_CHECKING, ClassVar, Dict, List, Optional, Tuple

from presidio_analyzer import RecognizerResult
from presidio_analyzer.score_thresholds import normalize_score_thresholds

if TYPE_CHECKING:
    from presidio_analyzer.nlp_engine import NlpArtifacts

logger = logging.getLogger("presidio-analyzer")


class EntityRecognizer:
    """
    A class representing an abstract PII entity recognizer.

    EntityRecognizer is an abstract class to be inherited by
    Recognizers which hold the logic for recognizing specific PII entities.

    EntityRecognizer exposes a method called enhance_using_context which
    can be overridden in case a custom context aware enhancement is needed
    in derived class of a recognizer.

    :param supported_entities: the entities supported by this recognizer
    (for example, phone number, address, etc.)
    :param supported_language: the language supported by this recognizer.
    The supported language code is iso6391Name
    :param name: the name of this recognizer (optional)
    :param version: the recognizer current version
    :param context: a list of words which can help boost confidence score
    when they appear in context of the matched entity
    :param country_code: Optional ISO 3166-1 alpha-2 country tag. Custom
        recognizers may set it per instance; predefined recognizers should
        prefer the class-level :attr:`COUNTRY_CODE`. Values are stripped,
        lower-cased, and must match :attr:`COUNTRY_CODE` when both are set.
    :param score_thresholds: Optional default and entity-specific score thresholds.
    """

    MIN_SCORE = 0
    MAX_SCORE = 1.0
    #: Canonical class-level country tag. Subclasses override on the class
    #: itself (e.g. ``COUNTRY_CODE = "us"``) and predefined country
    #: recognizers always declare it this way. Custom recognizers without
    #: a subclass can pass ``country_code=`` to the constructor instead;
    #: read both via the :meth:`country_code` / :meth:`is_country_specific`
    #: instance methods.
    COUNTRY_CODE: ClassVar[Optional[str]] = None

    def __init__(
        self,
        supported_entities: List[str],
        name: str = None,
        supported_language: str = "en",
        version: str = "0.0.1",
        context: Optional[List[str]] = None,
        country_code: Optional[str] = None,
        score_thresholds: Optional[Dict[str, float]] = None,
    ):
        self.supported_entities = supported_entities

        if name is None:
            self.name = self.__class__.__name__  # assign class name as name
        else:
            self.name = name

        self._id = f"{self.name}_{id(self)}"

        self.supported_language = supported_language
        self.version = version
        self.is_loaded = False
        self.context = context if context else []
        self.score_thresholds = score_thresholds

        self._country_code = self._resolve_country_code(country_code)

        self.load()
        logger.info("Loaded recognizer: %s", self.name)
        self.is_loaded = True

    @property
    def score_thresholds(self) -> Dict[str, float]:
        """Return a defensive copy of this recognizer's score thresholds."""
        return self._score_thresholds.copy()

    @score_thresholds.setter
    def score_thresholds(self, value: Optional[Dict[str, float]]) -> None:
        """Validate and store this recognizer's score thresholds.

        :param value: The default and entity-specific score thresholds.
        """
        self._score_thresholds = normalize_score_thresholds(value)

    @classmethod
    def _resolve_country_code(cls, passed: Optional[str]) -> Optional[str]:
        """Reconcile a constructor-passed country code with the class attribute.

        Implements the two-path tagging matrix: the class-level
        :attr:`COUNTRY_CODE` is the canonical declaration for predefined
        recognizers, and the constructor kwarg is the path for custom
        recognizers (typically routed through ``from_dict`` from YAML).
        Both can be set as long as they agree; conflicting values raise
        ``ValueError`` so a Polish tax-ID recognizer can't be silently
        re-tagged as British, regardless of which path the misconfiguration
        comes from.

        :param passed: The value supplied to ``__init__`` (already typed
            as ``Optional[str]``).
        :return: The lower-cased, stripped country code stored on the
            instance, or ``None`` for locale-agnostic recognizers.
        :raises TypeError: If ``passed`` is set but is not a string.
        :raises ValueError: If ``passed`` is blank, or if it disagrees
            with a class-level :attr:`COUNTRY_CODE`.
        """
        class_code = cls.COUNTRY_CODE
        normalized_class = (
            class_code.lower() if isinstance(class_code, str) else class_code
        )

        if passed is None:
            return normalized_class

        if not isinstance(passed, str):
            raise TypeError(
                f"country_code must be a string or None, got "
                f"{type(passed).__name__}: {passed!r}."
            )
        trimmed = passed.strip()
        if not trimmed:
            raise ValueError(
                f"country_code must be a non-empty string; got {passed!r}."
            )
        normalized_passed = trimmed.lower()

        if normalized_class is not None and normalized_passed != normalized_class:
            raise ValueError(
                f"country_code={passed!r} conflicts with class-level "
                f"{cls.__name__}.COUNTRY_CODE={class_code!r}. The class "
                f"attribute is the canonical declaration; pass the matching "
                f"value or omit ``country_code=`` entirely."
            )

        return normalized_passed

    def country_code(self) -> Optional[str]:
        """Return the country tag for this recognizer, or ``None`` if generic.

        Resolved at construction time from the class-level
        :attr:`COUNTRY_CODE` attribute and the optional ``country_code``
        constructor kwarg; the two are reconciled by
        :meth:`_resolve_country_code` so this method always returns a
        single, lower-cased value (or ``None``). Note this is an instance
        method — to introspect a class without instantiating, read
        ``cls.COUNTRY_CODE`` directly.
        """
        return self._country_code

    def is_country_specific(self) -> bool:
        """Return ``True`` iff this recognizer is tagged with a country.

        Equivalent to ``self.country_code() is not None``. Provided as a
        named predicate because filter / registry / discoverability code
        reads more naturally with an explicit "is this country-specific?"
        question than with a None-check.
        """
        return self.country_code() is not None

    @property
    def id(self):
        """Return a unique identifier of this recognizer."""

        return self._id

    @abstractmethod
    def load(self) -> None:
        """
        Initialize the recognizer assets if needed.

        (e.g. machine learning models)
        """

    @abstractmethod
    def analyze(
        self, text: str, entities: List[str], nlp_artifacts: "NlpArtifacts"
    ) -> List[RecognizerResult]:
        """
        Analyze text to identify entities.

        :param text: The text to be analyzed
        :param entities: The list of entities this recognizer is able to detect
        :param nlp_artifacts: A group of attributes which are the result of
        an NLP process over the input text.
        :return: List of results detected by this recognizer.
        """
        return None

    def enhance_using_context(
        self,
        text: str,
        raw_recognizer_results: List[RecognizerResult],
        other_raw_recognizer_results: List[RecognizerResult],
        nlp_artifacts: "NlpArtifacts",
        context: Optional[List[str]] = None,
    ) -> List[RecognizerResult]:
        """Enhance confidence score using context of the entity.

        Override this method in derived class in case a custom logic
        is needed, otherwise return value will be equal to
        raw_results.

        in case a result score is boosted, derived class need to update
        result.recognition_metadata[RecognizerResult.IS_SCORE_ENHANCED_BY_CONTEXT_KEY]

        :param text: The actual text that was analyzed
        :param raw_recognizer_results: This recognizer's results, to be updated
        based on recognizer specific context.
        :param other_raw_recognizer_results: Other recognizer results matched in
        the given text to allow related entity context enhancement
        :param nlp_artifacts: The nlp artifacts contains elements
                              such as lemmatized tokens for better
                              accuracy of the context enhancement process
        :param context: list of context words
        """
        return raw_recognizer_results

    def get_supported_entities(self) -> List[str]:
        """
        Return the list of entities this recognizer can identify.

        :return: A list of the supported entities by this recognizer
        """
        return self.supported_entities

    def get_supported_language(self) -> str:
        """
        Return the language this recognizer can support.

        :return: A list of the supported language by this recognizer
        """
        return self.supported_language

    def get_version(self) -> str:
        """
        Return the version of this recognizer.

        :return: The current version of this recognizer
        """
        return self.version

    def to_dict(self) -> Dict:
        """
        Serialize self to dictionary.

        :return: a dictionary
        """
        return_dict = {
            "supported_entities": self.supported_entities,
            "supported_language": self.supported_language,
            "name": self.name,
            "version": self.version,
        }
        if self._country_code is not None:
            return_dict["country_code"] = self._country_code
        return return_dict

    @classmethod
    def from_dict(cls, entity_recognizer_dict: Dict) -> "EntityRecognizer":
        """
        Create EntityRecognizer from a dict input.

        :param entity_recognizer_dict: Dict containing keys and values for instantiation
        """
        return cls(**entity_recognizer_dict)

    @staticmethod
    def remove_duplicates(results: List[RecognizerResult]) -> List[RecognizerResult]:
        """
        Remove duplicate, zero-score, and contained results.

        Results with a score of zero are removed. A result is also removed if another
        result of the same type fully contains it and has an equal or higher score.
        :param results: List[RecognizerResult]
        :return: List[RecognizerResult]
        """
        results = list(set(results))
        results = sorted(
            results,
            key=lambda x: (
                str(x.entity_type),
                x.start,
                -(x.end - x.start),
                -x.score,
            ),
        )
        filtered_results = []

        for _, entity_results in groupby(
            results, key=lambda result: result.entity_type
        ):
            active_results = []

            for result in entity_results:
                if result.score == 0:
                    continue

                # Only overlapping results can contain the current result.
                active_results = [
                    filtered
                    for filtered in active_results
                    if filtered.end >= result.start
                ]

                to_keep = True
                for filtered in active_results:
                    # If result is contained in one of the other results
                    if result.contained_in(filtered) and result.score <= filtered.score:
                        to_keep = False
                        break

                if to_keep:
                    filtered_results.append(result)
                    active_results.append(result)

        # Restore the existing score-first result order.
        return sorted(
            filtered_results,
            key=lambda x: (-x.score, x.start, -(x.end - x.start)),
        )

    @staticmethod
    def sanitize_value(text: str, replacement_pairs: List[Tuple[str, str]]) -> str:
        """
        Cleanse the input string of the replacement pairs specified as argument.

        :param text: input string
        :param replacement_pairs: pairs of what has to be replaced with which value
        :return: cleansed string
        """
        for search_string, replacement_string in replacement_pairs:
            text = text.replace(search_string, replacement_string)
        return text
