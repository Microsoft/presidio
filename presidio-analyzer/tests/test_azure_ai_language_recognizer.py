import os
import importlib
from unittest.mock import MagicMock

import pytest
import dotenv

from presidio_analyzer.predefined_recognizers import AzureAILanguageRecognizer

dotenv.load_dotenv()


def requires_env_vars():
    azure_ai_key = os.environ.get("AZURE_AI_KEY", "")
    azure_ai_endpoint = os.environ.get("AZURE_AI_ENDPOINT", "")

    return pytest.mark.skipif(
        azure_ai_key == "" or azure_ai_endpoint == "",
        reason=f"Environment variables are not set"
    )


@requires_env_vars()
def test_get_supported_entities():
    azure_ai_recognizer = AzureAILanguageRecognizer()
    supported_entities = azure_ai_recognizer.get_supported_entities()
    assert len(supported_entities) > 10


@requires_env_vars()
def test_analyze_simple():
    azure_ai_recognizer = AzureAILanguageRecognizer(supported_language="en")
    text = "My name is John Smith and my email is john.smith@email.com"
    results = azure_ai_recognizer.analyze(text=text)
    assert len(results) == 2


@requires_env_vars()
def test_analyze_subset_of_entities_on_request():
    azure_ai_recognizer = AzureAILanguageRecognizer(supported_language="en")
    text = "My name is John Smith and my email is john.smith@email.com"
    results = azure_ai_recognizer.analyze(text=text, entities=["EMAIL"])
    assert len(results) == 1
    assert results[0].entity_type == "EMAIL"


@requires_env_vars()
def test_analyze_subset_of_entities_on_init():
    azure_ai_recognizer = AzureAILanguageRecognizer(
        supported_language="en", supported_entities=["EMAIL"]
    )
    text = "My name is John Smith and my email is john.smith@email.com"
    results = azure_ai_recognizer.analyze(text=text)
    assert len(results) == 1
    assert results[0].entity_type == "EMAIL"
    assert results[0].start == 38
    assert results[0].end == 58


def test_mocked_entities_match_recognizer_results():
    try:
        importlib.import_module("azure.ai.textanalytics")
    except ImportError:
        pytest.skip("Skipping test because 'azure.ai.textanalytics' is not installed")

    from azure.ai.textanalytics import PiiEntity, TextAnalyticsClient, \
        RecognizePiiEntitiesResult
    from azure.core.credentials import AzureKeyCredential

    ent1 = PiiEntity(text="Raj", category="Person",
                     length=3, offset=0, confidence_score=0.8)
    ent2 = PiiEntity(text="My email is ab@email.com",
                     category="EMAIL", length=12, offset=12, confidence_score=0.9)
    mock_entities = [ent1, ent2]

    ta_client = TextAnalyticsClient(endpoint="", credential=AzureKeyCredential(key=""))

    mock_results = [RecognizePiiEntitiesResult(entities=mock_entities)]

    ta_client.recognize_pii_entities = MagicMock(return_value=mock_results)

    azure_ai_recognizer = AzureAILanguageRecognizer(ta_client=ta_client)
    results = azure_ai_recognizer.analyze(text="Raj's email is ab@email.com")

    for expected, actual in zip(mock_entities, results):
        assert expected.category == actual.entity_type
        assert expected.offset == actual.start
        assert expected.length == actual.end - actual.start
        assert expected.confidence_score == actual.score


def _mock_ta_client():
    try:
        importlib.import_module("azure.ai.textanalytics")
    except ImportError:
        pytest.skip("Skipping test because 'azure.ai.textanalytics' is not installed")

    from azure.ai.textanalytics import TextAnalyticsClient
    from azure.core.credentials import AzureKeyCredential

    return TextAnalyticsClient(endpoint="", credential=AzureKeyCredential(key=""))


def test_name_defaults_to_the_display_name():
    recognizer = AzureAILanguageRecognizer(ta_client=_mock_ta_client())
    assert recognizer.name == "Azure AI Language PII"


def test_name_can_be_overridden():
    # RecognizerListLoader passes `name` for every entry it builds, so the
    # constructor has to accept it; a `class_name` entry relies on it winning
    # over the hardcoded display name.
    recognizer = AzureAILanguageRecognizer(
        ta_client=_mock_ta_client(), name="Custom Azure PII"
    )
    assert recognizer.name == "Custom Azure PII"


def test_context_is_accepted():
    # The kwarg #1457 originally failed on. RemoteRecognizer takes it, so the
    # subclass has to forward it rather than reject it.
    recognizer = AzureAILanguageRecognizer(
        ta_client=_mock_ta_client(), context=["patient", "record"]
    )
    assert recognizer.context == ["patient", "record"]
