# ruff: noqa: D103,E501
"""Tests for the analyzer REST API server."""

from unittest.mock import patch

import pytest
from app import create_app
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NoOpNlpEngine
from presidio_analyzer.predefined_recognizers import IbanRecognizer


@pytest.fixture
def client():
    engine = AnalyzerEngine(
        registry=RecognizerRegistry([IbanRecognizer()]),
        nlp_engine=NoOpNlpEngine(models=[{"lang_code": "en", "model_name": "no_op"}]),
    )
    with patch("app.AnalyzerEngineProvider") as provider:
        provider.return_value.create_engine.return_value = engine
        app = create_app()
        app.testing = True
        yield app.test_client()


@pytest.mark.parametrize("entities", [["IBAN_CODE"], ["IT_FISCAL_CODE", "IBAN_CODE"]])
def test_given_supported_entities_then_return_exact_results(client, entities, caplog):
    with caplog.at_level("WARNING", logger="presidio-analyzer"):
        response = client.post(
            "/analyze",
            json={
                "text": "codice fiscale RSSMRA85M01H501Q, IBAN IT60X0542811101000000123456",
                "language": "en",
                "entities": entities,
            },
        )

    assert response.status_code == 200
    assert response.get_json() == [
        {
            "entity_type": "IBAN_CODE",
            "start": 38,
            "end": 65,
            "score": 1.0,
            "analysis_explanation": None,
        }
    ]
    warnings = [
        record.message for record in caplog.records if record.levelname == "WARNING"
    ]
    if "IT_FISCAL_CODE" in entities:
        assert len(warnings) == 1
        assert "IT_FISCAL_CODE" in warnings[0]
        assert "language : en" in warnings[0]
        assert "deprecated" in warnings[0]
        assert "will raise an error in a future version" in warnings[0]
    else:
        assert warnings == []


def test_given_no_matching_entities_then_return_500(client):
    response = client.post(
        "/analyze",
        json={"text": "test", "language": "en", "entities": ["UNSUPPORTED_ENTITY"]},
    )

    assert response.status_code == 500
    assert response.get_json() == {
        "error": "No matching recognizers were found to serve the request."
    }


def test_given_unsupported_language_for_supported_entities_then_return_500(client):
    response = client.get("/supportedentities?language=he")

    assert response.status_code == 500
    assert response.get_json() == {
        "error": "No matching recognizers were found to serve the request."
    }
