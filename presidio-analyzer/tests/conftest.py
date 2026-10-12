import shutil
from pathlib import Path
from typing import Dict, List

import pytest

from presidio_analyzer import (
    EntityRecognizer,
    Pattern,
    PatternRecognizer,
    AnalyzerEngine,
)
from presidio_analyzer import RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider, NlpEngine
from presidio_analyzer.predefined_recognizers import NLP_RECOGNIZERS, PREDEFINED_RECOGNIZERS
from tests.mocks import RecognizerRegistryMock, NlpEngineMock


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "skip_engine(nlp_engine): skip test for given nlp engine"
    )


@pytest.fixture(scope="session")
def nlp_engine_provider() -> NlpEngineProvider:
    return NlpEngineProvider()


@pytest.fixture(scope="session")
def nlp_engines(request, nlp_engine_provider) -> Dict[str, NlpEngine]:
    available_engines = {}

    nlp_engines = nlp_engine_provider.nlp_engines
    for name, engine_cls in nlp_engines.items():
        if name == "spacy":
            available_engines[f"{name}_en"] = engine_cls(
                models=[{"lang_code": "en", "model_name": "en_core_web_lg"}]
            )
        elif name == "stanza":
            available_engines[f"{name}_en"] = engine_cls(
                models=[{"lang_code": "en", "model_name": "en"}]
            )
        elif name == "transformers":
            available_engines[f"{name}_en"] = engine_cls(
                models=[
                    {
                        "lang_code": "en",
                        "model_name": {
                            "spacy": "en_core_web_sm",
                            "transformers": "StanfordAIMI/stanford-deidentifier-base",
                        },
                    }
                ]
            )
        elif name == "slim":
            available_engines[f"{name}_en"] = engine_cls(
                models=[{"lang_code": "en", "model_name": "en_core_web_sm"}]
            )
        elif name == "no_op":
            available_engines[f"{name}_en"] = engine_cls(
                models=[{"lang_code": "en", "model_name": "no_op"}]
            )
        else:
            raise ValueError("Unsupported engine for tests")

    return available_engines


@pytest.fixture(autouse=True)
def skip_by_engine(request, nlp_engines):
    marker = request.node.get_closest_marker("skip_engine")
    if marker:
        marker_arg = marker.args[0]
        if marker_arg not in nlp_engines:
            pytest.skip(f"skipped on this engine: {marker_arg}")


@pytest.fixture(scope="session")
def spacy_nlp_engine(nlp_engines):
    nlp_engine = nlp_engines.get("spacy_en", None)
    if nlp_engine:
        nlp_engine.load()
    return nlp_engine


@pytest.fixture(scope="session")
def nlp_recognizers() -> Dict[str, EntityRecognizer]:
    return {name: rec_cls() for name, rec_cls in NLP_RECOGNIZERS.items()}


@pytest.fixture(scope="session")
def mandatory_recognizers() -> List[str]:
    return list(PREDEFINED_RECOGNIZERS)


@pytest.fixture(scope="session")
def ner_strength() -> float:
    return 0.85


@pytest.fixture(scope="session")
def max_score() -> float:
    return EntityRecognizer.MAX_SCORE


@pytest.fixture(scope="session")
def min_score() -> float:
    return EntityRecognizer.MIN_SCORE


@pytest.fixture(scope="module")
def loaded_registry() -> RecognizerRegistry:
    return RecognizerRegistry()


@pytest.fixture(scope="module")
def mock_registry() -> RecognizerRegistryMock:
    return RecognizerRegistryMock()


@pytest.fixture(scope="module")
def mock_nlp_engine() -> NlpEngineMock:
    return NlpEngineMock()


@pytest.fixture(scope="module")
def analyzer_engine_simple(mock_registry, mock_nlp_engine) -> AnalyzerEngine:
    return AnalyzerEngine(registry=mock_registry, nlp_engine=mock_nlp_engine)


@pytest.fixture(scope="session")
def zip_code_recognizer():
    regex = r"(\b\d{5}(?:\-\d{4})?\b)"
    zipcode_pattern = Pattern(name="zip code (weak)", regex=regex, score=0.01)
    zip_recognizer = PatternRecognizer(
        supported_entity="ZIP", patterns=[zipcode_pattern]
    )
    return zip_recognizer


def pytest_sessionfinish():
    """Remove files created during mock spaCy models creation."""

    mock_models = ("he_test", "bn_test")

    for mock_model in mock_models:
        test_model_path1 = Path(Path(__file__).parent, mock_model)
        test_model_path2 = Path(Path(__file__).parent.parent, mock_model)
        for path in (test_model_path1, test_model_path2):
            if path.exists():
                try:
                    shutil.rmtree(path)
                except OSError as e:
                    print("Failed to remove file: %s - %s." % (e.filename, e.strerror))
