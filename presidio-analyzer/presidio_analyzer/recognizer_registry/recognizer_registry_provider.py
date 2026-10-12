from __future__ import annotations

import logging
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from presidio_analyzer import EntityRecognizer
from presidio_analyzer.input_validation import ConfigurationValidator
from presidio_analyzer.nlp_engine import NlpEngine, NoOpNlpEngine
from presidio_analyzer.predefined_recognizers import SpacyRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistry
from presidio_analyzer.recognizer_registry.recognizers_loader_utils import (
    RecognizerConfigurationLoader,
    RecognizerListLoader,
)

logger = logging.getLogger("presidio-analyzer")


class RecognizerRegistryProvider:
    r"""
    Utility class for loading Recognizer Registry.

    Use this class to load recognizer registry from a yaml file

    :param conf_file: Path to yaml file containing registry configuration
    :param registry_configuration: Dict containing registry configuration
    :example:
        {
            "supported_languages": ["de", "es"],
            "recognizers": [
                {
                    "name": "Zip code Recognizer",
                    "supported_language": "en",
                    "patterns": [
                        {
                            "name": "zip code (weak)",
                            "regex": "(\\b\\d{5}(?:\\-\\d{4})?\\b)",
                            "score": 0.01,
                        }
                    ],
                    "context": ["zip", "code"],
                    "supported_entity": "ZIP",
                }
            ]
        }
    """

    def __init__(
        self,
        conf_file: Optional[Union[Path, str]] = None,
        registry_configuration: Optional[Dict] = None,
        nlp_engine: Optional[NlpEngine] = None,
    ):
        self.configuration = RecognizerConfigurationLoader.get(
            conf_file=conf_file, registry_configuration=registry_configuration
        )

        self.configuration = (
            ConfigurationValidator.validate_recognizer_registry_configuration(
                self.configuration
            )
        )
        self.nlp_engine = nlp_engine

    def create_recognizer_registry(self) -> RecognizerRegistry:
        """Create a recognizer registry according to configuration loaded previously."""
        supported_languages = self.configuration.get("supported_languages")
        global_regex_flags = self.configuration.get("global_regex_flags")
        recognizers_conf = self.configuration.get("recognizers")
        recognizers = RecognizerListLoader.get(
            recognizers_conf,
            supported_languages,
            global_regex_flags,
        )

        recognizers = list(recognizers)

        self.__update_based_on_nlp_recognizer_conf(
            recognizers, recognizers_conf, supported_languages
        )

        registry = RecognizerRegistry(
            recognizers=recognizers,
            supported_languages=supported_languages,
            global_regex_flags=global_regex_flags,
        )
        registry.validate_nlp_engine_compatibility(self.nlp_engine)

        return registry

    def __update_based_on_nlp_recognizer_conf(
        self,
        recognizers: List[EntityRecognizer],
        recognizers_conf: Optional[Dict],
        supported_languages: List[str],
    ) -> None:
        """Update the list of recognizers based on the NLP recognizer configuration.

        The method adds the NLP recognizer to the list of recognizers
        if it is not already present,
        or removes it if it is not enabled in the configuration.
        Furthermore, it checks if there are
        any inconsistencies in configuration. For example:
        - Multiple enabled NLP recognizers in the configuration for one language.
        - The NLP recognizer in the configuration does not match the Nlp Engine.

        :param recognizers: List of recognizers to update.
        :param recognizers_conf: Configuration of the recognizers from the YAML file
        :param supported_languages: List of supported languages.

        :raises ValueError: If there are multiple enabled NLP recognizers
        in the configuration.
        :raises ValueError: If the NLP recognizer
        in the configuration does not match the Nlp Engine.
        """
        nlp_engine = self.nlp_engine

        if not nlp_engine:
            return

        if isinstance(nlp_engine, NoOpNlpEngine):
            logger.info(
                "Skipping NLP recognizer configuration updates for no-op NLP engine."
            )
            return

        for language in nlp_engine.get_supported_languages():
            self.__update_based_on_nlp_recognizer_conf_and_lang(
                recognizers=recognizers, nlp_engine=nlp_engine, language=language
            )
            self.__remove_disabled_nlp_recognizers(
                recognizers=recognizers,
                recognizers_conf=recognizers_conf,
                language=language,
            )

    @staticmethod
    def __update_based_on_nlp_recognizer_conf_and_lang(
        recognizers: List[EntityRecognizer],
        nlp_engine: NlpEngine,
        language: str,
    ):
        """
        Update the list of recognizers with nlp recognizers.

        Update based on the NLP recognizer configuration for a specific language.
        """

        nlp_recognizers = [
            rec
            for rec in recognizers
            if isinstance(rec, SpacyRecognizer) and rec.supported_language == language
        ]

        # Case 1: NLP recognizer is not in the list of recognizers
        if not nlp_recognizers:
            warning_text = (
                f"NLP recognizer (e.g. SpacyRecognizer, StanzaRecognizer) "
                f"is not in the list of recognizers "
                f"for language {language}. "
                f"Adding the default recognizer to the list."
                f"If you wish to remove the NLP recognizer, "
                f"define it as `enabled=false`."
            )
            logger.warning(warning_text)
            warnings.warn(warning_text)
            if nlp_engine:
                nlp_recognizer_cls = RecognizerRegistry.get_nlp_recognizer(
                    nlp_engine=nlp_engine
                )
                recognizers.append(
                    nlp_recognizer_cls(
                        supported_language=language,
                        supported_entities=nlp_engine.get_supported_entities(),
                    )
                )
            else:
                recognizers.append(SpacyRecognizer(supported_language=language))
            return

        # Case 2: There are multiple NLP recognizers for this language, throw error
        if len(nlp_recognizers) > 1:
            raise ValueError(
                f"Multiple NLP recognizers for language {language} "
                f"found in the configuration. "
                f"Please remove the duplicates."
            )

        # Case 3: There is a mismatch between the NLP Engine and the NLP Recognizer
        nlp_recognizer = nlp_recognizers[0]
        expected_nlp_recognizer_cls = RecognizerRegistry.get_nlp_recognizer(nlp_engine)
        if nlp_recognizer.__class__ != expected_nlp_recognizer_cls:
            raise ValueError(
                f"There is a mismatch between the NLP Engine defined "
                f"({nlp_engine.__class__.__name__}),"
                f"and the configured NLP recognizer "
                f"({nlp_recognizer.__class__.__name__})."
                f"Make sure the NLP recognizer is aligned with the "
                f"NLP engine and that all others are removed/disabled."
            )

    @staticmethod
    def __remove_disabled_nlp_recognizers(
        recognizers: List[EntityRecognizer],
        recognizers_conf: Dict[str, Any],
        language: str,
    ):
        """
        Remove recognizers that are disabled in the configuration.

        Goes through the recognizer conf provided by the user,
        and checks if a recognizer for a given language is disabled.
        If yes, it removes it from the recognizers list
        (as some are not removed in the previous step).
        """

        disabled = [
            rec_conf
            for rec_conf in recognizers_conf
            if not RecognizerListLoader.is_recognizer_enabled(rec_conf)
        ]

        disabled_rec_names = [
            RecognizerListLoader.get_recognizer_name(rec) for rec in disabled
        ]

        if not disabled:
            return

        disabled_rec_classes = [
            cls
            for cls in RecognizerListLoader.get_all_existing_recognizers()
            if cls.__name__ in disabled_rec_names
        ]

        lang_recognizers = [
            rec for rec in recognizers if rec.supported_language == language
        ]

        for recognizer in lang_recognizers:
            if type(recognizer) in disabled_rec_classes:
                recognizers.remove(recognizer)
                logger.info(
                    f"Disabled {recognizer.__class__.__name__} "
                    f"recognizer for language {language}."
                )
