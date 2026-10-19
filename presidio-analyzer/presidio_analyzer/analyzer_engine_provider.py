import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.input_validation import ConfigurationValidator
from presidio_analyzer.nlp_engine import NlpEngine, NlpEngineProvider
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

logger = logging.getLogger("presidio-analyzer")


class AnalyzerEngineProvider:
    """
    Utility function for loading Presidio Analyzer.

    Use this class to load presidio analyzer engine from a yaml file

    :param analyzer_engine_conf_file: the path to the analyzer configuration file
    :param nlp_engine_conf_file: the path to the nlp engine configuration file
    :param recognizer_registry_conf_file: the path to the recognizer
    registry configuration file
    """

    def __init__(
        self,
        analyzer_engine_conf_file: Optional[Union[Path, str]] = None,
        nlp_engine_conf_file: Optional[Union[Path, str]] = None,
        recognizer_registry_conf_file: Optional[Union[Path, str]] = None,
    ):
        if analyzer_engine_conf_file:
            ConfigurationValidator.validate_file_path(analyzer_engine_conf_file)
        if nlp_engine_conf_file:
            ConfigurationValidator.validate_file_path(nlp_engine_conf_file)
        if recognizer_registry_conf_file:
            ConfigurationValidator.validate_file_path(recognizer_registry_conf_file)

        self.configuration = self.get_configuration(conf_file=analyzer_engine_conf_file)
        self.nlp_engine_conf_file = nlp_engine_conf_file
        self.recognizer_registry_conf_file = recognizer_registry_conf_file

    def get_configuration(
        self, conf_file: Optional[Union[Path, str]]
    ) -> Union[Dict[str, Any]]:
        """Retrieve analyzer engine configuration from the provided file."""

        if not conf_file:
            default_conf_file = self._get_full_conf_path()
            with open(default_conf_file) as file:
                configuration = yaml.safe_load(file)
            logger.info(
                f"Analyzer Engine configuration file "
                f"not provided. Using {default_conf_file}."
            )
        else:
            try:
                logger.info(f"Reading analyzer configuration from {conf_file}")
                with open(conf_file) as file:
                    configuration = yaml.safe_load(file)
            except OSError:
                logger.warning(
                    f"configuration file {conf_file} not found.  Using default config."
                )
                with open(self._get_full_conf_path()) as file:
                    configuration = yaml.safe_load(file)
            except Exception:
                logger.warning(
                    f"Failed to parse file {conf_file}, resorting to default"
                )
                with open(self._get_full_conf_path()) as file:
                    configuration = yaml.safe_load(file)

        ConfigurationValidator.validate_analyzer_configuration(configuration)
        logger.debug("Analyzer configuration validation passed")

        return configuration

    def create_engine(self) -> AnalyzerEngine:
        """
        Load Presidio Analyzer from yaml configuration file.

        :return: analyzer engine initialized with yaml configuration
        """

        nlp_engine = self._load_nlp_engine()
        supported_languages = self.configuration.get("supported_languages", ["en"])
        default_score_threshold = self.configuration.get("default_score_threshold", 0)

        registry = self._load_recognizer_registry(
            supported_languages=supported_languages, nlp_engine=nlp_engine
        )

        analyzer = AnalyzerEngine(
            nlp_engine=nlp_engine,
            registry=registry,
            supported_languages=supported_languages,
            default_score_threshold=default_score_threshold,
        )

        return analyzer

    def _load_recognizer_registry(
        self,
        supported_languages: List[str],
        nlp_engine: NlpEngine,
    ) -> RecognizerRegistry:
        """Load recognizer registry.

        Inline ``recognizer_registry`` section in the analyzer conf takes
        priority over a separately provided per-section file so that a unified
        ANALYZER_CONF_FILE is self-contained and is not silently overridden by
        a per-section file that was baked into the image as a Dockerfile default.
        A per-section file is only used when no inline section is present.
        """
        if "recognizer_registry" in self.configuration:
            registry_configuration = self.configuration["recognizer_registry"]
            provider = RecognizerRegistryProvider(
                registry_configuration={
                    **registry_configuration,
                    "supported_languages": supported_languages,
                },
                nlp_engine=nlp_engine,
            )
        elif self.recognizer_registry_conf_file:
            logger.info(
                f"Reading recognizer registry "
                f"configuration from {self.recognizer_registry_conf_file}"
            )
            provider = RecognizerRegistryProvider(
                conf_file=self.recognizer_registry_conf_file, nlp_engine=nlp_engine
            )
        else:
            logger.warning(
                "configuration file is missing for 'recognizer_registry'. "
                "Using default configuration for recognizer registry"
            )
            registry_configuration = self.configuration.get("recognizer_registry", {})
            provider = RecognizerRegistryProvider(
                registry_configuration={
                    **registry_configuration,
                    "supported_languages": supported_languages,
                },
                nlp_engine=nlp_engine,
            )
        registry = provider.create_recognizer_registry()

        return registry

    def _load_nlp_engine(self) -> NlpEngine:
        """Load NLP engine.

        Inline ``nlp_configuration`` section in the analyzer conf takes
        priority over a separately provided per-section file so that a unified
        ANALYZER_CONF_FILE is self-contained and is not silently overridden by
        a per-section file that was baked into the image as a Dockerfile default.
        A per-section file is only used when no inline section is present.
        """
        if "nlp_configuration" in self.configuration:
            nlp_configuration = self.configuration["nlp_configuration"]
            provider = NlpEngineProvider(nlp_configuration=nlp_configuration)
        elif self.nlp_engine_conf_file:
            logger.info(f"Reading nlp configuration from {self.nlp_engine_conf_file}")
            provider = NlpEngineProvider(conf_file=self.nlp_engine_conf_file)
        else:
            logger.warning(
                "configuration file is missing for 'nlp_configuration'."
                "Using default configuration for nlp engine"
            )
            provider = NlpEngineProvider()

        return provider.create_engine()

    @staticmethod
    def _get_full_conf_path(
        default_conf_file: Union[Path, str] = "default_analyzer.yaml",
    ) -> Path:
        """Return a Path to the default conf file."""
        return Path(Path(__file__).parent, "conf", default_conf_file)
