import copy
import logging
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Type, Union

import regex as re
import yaml

from presidio_analyzer import EntityRecognizer, PatternRecognizer
from presidio_analyzer.nlp_engine import (
    NlpEngine,
    NoOpNlpEngine,
    SpacyNlpEngine,
    StanzaNlpEngine,
    TransformersNlpEngine,
)
from presidio_analyzer.predefined_recognizers import (
    SpacyRecognizer,
    StanzaRecognizer,
    TransformersRecognizer,
)
from presidio_analyzer.recognizer_registry.recognizers_loader_utils import (
    RecognizerConfigurationLoader,
    RecognizerListLoader,
)
from presidio_analyzer.score_thresholds import normalize_score_thresholds

logger = logging.getLogger("presidio-analyzer")


class RecognizerRegistry:
    """
    Detect, register and hold all recognizers to be used by the analyzer.

    :param recognizers: An optional list of recognizers,
    that will be available instead of the predefined recognizers
    :param global_regex_flags: regex flags to be used in regex matching,
    including deny-lists
    :param supported_languages: List of languages supported by this registry.

    """

    def __init__(
        self,
        recognizers: Optional[Iterable[EntityRecognizer]] = None,
        global_regex_flags: Optional[int] = re.DOTALL | re.MULTILINE | re.IGNORECASE,
        supported_languages: Optional[List[str]] = None,
    ):
        if recognizers:
            self.recognizers = recognizers
        else:
            self.recognizers = []
        self.global_regex_flags = global_regex_flags
        self.supported_languages = (
            supported_languages if supported_languages else ["en"]
        )

    def validate_nlp_engine_compatibility(
        self, nlp_engine: Optional[NlpEngine]
    ) -> None:
        """Validate that registered recognizers can use the selected NLP engine."""
        if not isinstance(nlp_engine, NoOpNlpEngine):
            return

        nlp_recognizers = [
            rec for rec in self.recognizers if isinstance(rec, SpacyRecognizer)
        ]
        if nlp_recognizers:
            names = sorted({rec.__class__.__name__ for rec in nlp_recognizers})
            raise ValueError(
                "NoOpNlpEngine cannot be used with NLP engine recognizers. "
                f"Remove or disable these recognizers: {names}."
            )

    def _create_nlp_recognizer(
        self,
        nlp_engine: Optional[NlpEngine] = None,
        supported_language: Optional[str] = None,
    ) -> SpacyRecognizer:
        nlp_recognizer = self.get_nlp_recognizer(nlp_engine)

        if nlp_engine:
            return nlp_recognizer(
                supported_language=supported_language,
                supported_entities=nlp_engine.get_supported_entities(),
            )

        return nlp_recognizer(supported_language=supported_language)

    def add_nlp_recognizer(self, nlp_engine: NlpEngine) -> None:
        """
        Adding NLP recognizer in accordance with the nlp engine.

        :param nlp_engine: The NLP engine.
        :return: None
        """

        if isinstance(nlp_engine, NoOpNlpEngine):
            self.validate_nlp_engine_compatibility(nlp_engine)
            logger.info("Skipping NLP recognizer registration for no-op NLP engine.")
            return

        if not nlp_engine:
            supported_languages = self.supported_languages
        else:
            supported_languages = nlp_engine.get_supported_languages()

        self.recognizers.extend(
            [
                self._create_nlp_recognizer(
                    nlp_engine=nlp_engine, supported_language=supported_language
                )
                for supported_language in supported_languages
            ]
        )

    def load_predefined_recognizers(
        self,
        languages: Optional[List[str]] = None,
        nlp_engine: NlpEngine = None,
        countries: Optional[List[str]] = None,
    ) -> None:
        """
        Load the existing recognizers into memory.

        :param languages: List of languages for which to load recognizers
        :param nlp_engine: The NLP engine to use.
        :param countries: Optional list of country codes (case-insensitive,
            ISO 3166-1 alpha-2 — e.g. ``["us", "uk"]``).
            When provided, the loaded recognizers are limited per the
            ``country_code`` attribute on each recognizer:

            - recognizers with ``country_code is None`` (locale-agnostic
              built-ins, NER, NLP engine, third-party recognizers, and any
              custom recognizer that hasn't opted into the country tag) are
              **always loaded**;
            - recognizers with ``country_code`` set are loaded only when
              their code is in ``countries``.

            Passing an empty list (``countries=[]``) keeps only
            locale-agnostic recognizers. Passing ``None`` (the default)
            preserves the previous behavior of loading every predefined
            recognizer.
        :return: None
        """

        registry_configuration = {"global_regex_flags": self.global_regex_flags}
        if languages is not None:
            registry_configuration["supported_languages"] = languages
        if countries is not None:
            # Threaded through the configuration the same way as
            # ``supported_languages`` so the filter is applied inside
            # ``RecognizerListLoader.get(...)`` and behaves uniformly
            # whether driven from Python or from a YAML config file.
            registry_configuration["supported_countries"] = countries

        configuration = RecognizerConfigurationLoader.get(
            registry_configuration=registry_configuration
        )
        recognizers = RecognizerListLoader.get(**configuration)

        self.recognizers.extend(recognizers)
        self.add_nlp_recognizer(nlp_engine=nlp_engine)

    @staticmethod
    def get_nlp_recognizer(
        nlp_engine: NlpEngine,
    ) -> Type[SpacyRecognizer]:
        """Return the recognizer leveraging the selected NLP Engine."""

        if isinstance(nlp_engine, StanzaNlpEngine):
            return StanzaRecognizer
        if isinstance(nlp_engine, TransformersNlpEngine):
            return TransformersRecognizer
        if isinstance(nlp_engine, NoOpNlpEngine):
            raise ValueError("NoOpNlpEngine does not have an NLP recognizer")
        if not nlp_engine or isinstance(nlp_engine, SpacyNlpEngine):
            return SpacyRecognizer
        else:
            logger.warning(
                "nlp engine should be either SpacyNlpEngine,"
                "StanzaNlpEngine or TransformersNlpEngine"
            )
            # Returning default
            return SpacyRecognizer

    def get_recognizers(
        self,
        language: str,
        entities: Optional[List[str]] = None,
        all_fields: bool = False,
        ad_hoc_recognizers: Optional[List[EntityRecognizer]] = None,
    ) -> List[EntityRecognizer]:
        """
        Return a list of recognizers which supports the specified name and language.

        :param entities: the requested entities
        :param language: the requested language
        :param all_fields: a flag to return all fields of a requested language.
        :param ad_hoc_recognizers: Additional recognizers provided by the user
        as part of the request
        :return: A list of the recognizers which supports the supplied entities
        and language
        :raises ValueError: if language is None, entities is None when all_fields
        is False, or if no recognizers match the request at all.

        Partly unsupported requests log a warning and return the matching
        recognizers. This warn-and-ignore behavior
        is deprecated and will raise an error in a future version. Use
        AnalyzerEngine.get_supported_entities(language) to find supported entities,
        or provide matching ad-hoc recognizers.
        """
        if language is None:
            raise ValueError("No language provided")

        if entities is None and all_fields is False:
            raise ValueError("No entities provided")

        all_possible_recognizers = copy.copy(self.recognizers)
        if ad_hoc_recognizers:
            all_possible_recognizers.extend(ad_hoc_recognizers)

        # filter out unwanted recognizers
        to_return = set()
        if all_fields:
            to_return = [
                rec
                for rec in all_possible_recognizers
                if language == rec.supported_language
            ]
        else:
            for entity in entities:
                subset = [
                    rec
                    for rec in all_possible_recognizers
                    if entity in rec.supported_entities
                    and language == rec.supported_language
                ]

                if not subset:
                    logger.warning(
                        "Entity %s doesn't have the corresponding"
                        " recognizer in language : %s. Ignoring unsupported entities"
                        " is deprecated and will raise an error in a future version."
                        " Use AnalyzerEngine.get_supported_entities(language) to find"
                        " supported entities, or add a matching recognizer.",
                        entity,
                        language,
                    )
                else:
                    to_return.update(set(subset))

        logger.debug(
            "Returning a total of %s recognizers",
            str(len(to_return)),
        )

        if not to_return:
            raise ValueError("No matching recognizers were found to serve the request.")

        return list(to_return)

    def get_country_codes(self) -> List[str]:
        """Return the set of country codes currently represented in the registry.

        Aggregates the resolved country tag (via
        :meth:`EntityRecognizer.country_code`) across all loaded
        recognizers — including both class-level ``COUNTRY_CODE`` and
        per-instance ``country_code=`` constructor kwargs — and excludes
        generic / locale-agnostic ones. Useful for debugging country-
        filter behavior:

        >>> registry = RecognizerRegistry()
        >>> registry.load_predefined_recognizers()
        >>> sorted(registry.get_country_codes())  # doctest: +SKIP
        ['au', 'ca', 'de', 'es', 'fi', 'in', 'it', 'kr', 'ng', 'pl', 'se',
         'sg', 'th', 'tr', 'uk', 'us']

        :return: A sorted list of unique country codes (lowercased) seen on
            the loaded recognizers.
        """
        codes = set()
        for rec in self.recognizers:
            try:
                code = rec.country_code()
            except Exception:  # pragma: no cover — defensive
                code = None
            if isinstance(code, str) and code:
                codes.add(code.lower())
        return sorted(codes)

    def add_recognizer(self, recognizer: EntityRecognizer) -> None:
        """
        Add a new recognizer to the list of recognizers.

        :param recognizer: Recognizer to add
        """
        if not isinstance(recognizer, EntityRecognizer):
            raise ValueError("Input is not of type EntityRecognizer")

        self.recognizers.append(recognizer)

    def remove_recognizer(
        self, recognizer_name: str, language: Optional[str] = None
    ) -> None:
        """
        Remove a recognizer based on its name.

        :param recognizer_name: Name of recognizer to remove
        :param language: The supported language of the recognizer to be removed,
        in case multiple recognizers with the same name are present,
        and only one should be removed.
        """

        if not language:
            new_recognizers = [
                rec for rec in self.recognizers if rec.name != recognizer_name
            ]

            logger.info(
                "Removed %s recognizers which had the name %s",
                str(len(self.recognizers) - len(new_recognizers)),
                recognizer_name,
            )

        else:
            new_recognizers = [
                rec
                for rec in self.recognizers
                if rec.name != recognizer_name or rec.supported_language != language
            ]

            logger.info(
                "Removed %s recognizers which had the name %s and language %s",
                str(len(self.recognizers) - len(new_recognizers)),
                recognizer_name,
                language,
            )

        self.recognizers = new_recognizers

    def add_pattern_recognizer_from_dict(self, recognizer_dict: Dict) -> None:
        """
        Load a pattern recognizer from a Dict into the recognizer registry.

        :param recognizer_dict: Dict holding a serialization of an PatternRecognizer

        :example:
        >>> registry = RecognizerRegistry()
        >>> recognizer = { "name": "Titles Recognizer", "supported_language": "en","supported_entity": "TITLE", "deny_list": ["Mr.","Mrs."]}
        >>> registry.add_pattern_recognizer_from_dict(recognizer)
        """  # noqa: E501

        recognizer_config = recognizer_dict.copy()
        score_thresholds = normalize_score_thresholds(
            recognizer_config.pop("score_thresholds", None)
        )
        recognizer = PatternRecognizer.from_dict(recognizer_config)
        recognizer.score_thresholds = score_thresholds
        self.add_recognizer(recognizer)

    def add_recognizers_from_yaml(self, yml_path: Union[str, Path]) -> None:
        r"""
        Read YAML file and load recognizers into the recognizer registry.

        See example yaml file here:
        https://github.com/data-privacy-stack/presidio/blob/main/presidio-analyzer/presidio_analyzer/conf/example_recognizers.yaml

        :example:
        >>> yaml_file = "recognizers.yaml"
        >>> registry = RecognizerRegistry()
        >>> registry.add_recognizers_from_yaml(yaml_file)

        """

        try:
            with open(yml_path) as stream:
                yaml_recognizers = yaml.safe_load(stream)

            for yaml_recognizer in yaml_recognizers["recognizers"]:
                self.add_pattern_recognizer_from_dict(yaml_recognizer)
        except OSError as io_error:
            print(f"Error reading file {yml_path}")
            raise io_error
        except yaml.YAMLError as yaml_error:
            print(f"Failed to parse file {yml_path}")
            raise yaml_error
        except TypeError as yaml_error:
            print(f"Failed to parse file {yml_path}")
            raise yaml_error

    def __instantiate_recognizer(
        self, recognizer_class: Type[EntityRecognizer], supported_language: str
    ):
        """
        Instantiate a recognizer class given type and input.

        :param recognizer_class: Class object of the recognizer
        :param supported_language: Language this recognizer should support
        """

        inst = recognizer_class(supported_language=supported_language)
        if isinstance(inst, PatternRecognizer):
            inst.global_regex_flags = self.global_regex_flags
        return inst

    def _get_supported_languages(self) -> List[str]:
        languages = []
        for rec in self.recognizers:
            languages.append(rec.supported_language)

        return list(set(languages))

    def get_supported_entities(
        self, languages: Optional[List[str]] = None
    ) -> List[str]:
        """
        Return the supported entities by the set of recognizers loaded.

        :param languages: The languages to get the supported entities for.
        If languages=None, returns all entities for all languages.
        """
        if not languages:
            languages = self._get_supported_languages()

        supported_entities = []
        for language in languages:
            recognizers = self.get_recognizers(language=language, all_fields=True)

            for recognizer in recognizers:
                supported_entities.extend(recognizer.get_supported_entities())

        return list(set(supported_entities))
