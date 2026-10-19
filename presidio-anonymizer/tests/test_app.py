import json

import pytest

from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_anonymize_single_text_unchanged(client):
    request_body = {
        "text": "hello world, my name is Jane Doe.",
        "anonymizers": {"DEFAULT": {"type": "replace", "new_value": "ANONYMIZED"}},
        "analyzer_results": [
            {"start": 24, "end": 32, "score": 0.8, "entity_type": "NAME"}
        ],
    }

    response = client.post("/anonymize", json=request_body)
    body = json.loads(response.data)

    assert response.status_code == 200
    assert isinstance(body, dict)
    assert body["text"] == "hello world, my name is ANONYMIZED."


def test_anonymize_batch_returns_one_result_per_text(client):
    request_body = {
        "text": [
            "hello world, my name is Jane Doe.",
            "call me at 034453334",
        ],
        "anonymizers": {
            "DEFAULT": {"type": "replace", "new_value": "ANONYMIZED"},
        },
        "analyzer_results": [
            [{"start": 24, "end": 32, "score": 0.8, "entity_type": "NAME"}],
            [{"start": 11, "end": 20, "score": 0.9, "entity_type": "PHONE_NUMBER"}],
        ],
    }

    response = client.post("/anonymize", json=request_body)
    body = json.loads(response.data)

    assert response.status_code == 200
    assert isinstance(body, list)
    assert len(body) == 2
    assert body[0]["text"] == "hello world, my name is ANONYMIZED."
    assert body[1]["text"] == "call me at ANONYMIZED"


def test_anonymize_batch_missing_analyzer_results_leaves_text_unchanged(client):
    request_body = {
        "text": ["hello world!", "nice to meet you"],
        "anonymizers": {"DEFAULT": {"type": "replace", "new_value": "ANONYMIZED"}},
    }

    response = client.post("/anonymize", json=request_body)
    body = json.loads(response.data)

    assert response.status_code == 200
    assert [item["text"] for item in body] == ["hello world!", "nice to meet you"]
    assert all(item["items"] == [] for item in body)


def test_anonymize_batch_length_mismatch_returns_422(client):
    request_body = {
        "text": ["one", "two", "three"],
        "anonymizers": {"DEFAULT": {"type": "replace", "new_value": "X"}},
        "analyzer_results": [[]],
    }

    response = client.post("/anonymize", json=request_body)
    body = json.loads(response.data)

    assert response.status_code == 422
    assert "analyzer_results" in body["error"]


def test_deanonymize_single_text_unchanged(client):
    key = "1111111111111111"
    encrypt_body = {
        "text": "my number is 034453334",
        "anonymizers": {"DEFAULT": {"type": "encrypt", "key": key}},
        "analyzer_results": [
            {"start": 13, "end": 22, "score": 0.9, "entity_type": "PHONE_NUMBER"}
        ],
    }
    encrypted = json.loads(client.post("/anonymize", json=encrypt_body).data)

    decrypt_body = {
        "text": encrypted["text"],
        "deanonymizers": {"DEFAULT": {"type": "decrypt", "key": key}},
        "anonymizer_results": [
            {
                "start": item["start"],
                "end": item["end"],
                "entity_type": item["entity_type"],
            }
            for item in encrypted["items"]
        ],
    }
    response = client.post("/deanonymize", json=decrypt_body)
    body = json.loads(response.data)

    assert response.status_code == 200
    assert body["text"] == "my number is 034453334"


def test_deanonymize_batch_returns_one_result_per_text(client):
    key = "1111111111111111"
    encrypt_body = {
        "text": ["number is 034453334", "number is 099998888"],
        "anonymizers": {"DEFAULT": {"type": "encrypt", "key": key}},
        "analyzer_results": [
            [{"start": 10, "end": 19, "score": 0.9, "entity_type": "PHONE_NUMBER"}],
            [{"start": 10, "end": 19, "score": 0.9, "entity_type": "PHONE_NUMBER"}],
        ],
    }
    encrypted = json.loads(client.post("/anonymize", json=encrypt_body).data)

    decrypt_body = {
        "text": [item["text"] for item in encrypted],
        "deanonymizers": {"DEFAULT": {"type": "decrypt", "key": key}},
        "anonymizer_results": [
            [
                {
                    "start": item["items"][0]["start"],
                    "end": item["items"][0]["end"],
                    "entity_type": item["items"][0]["entity_type"],
                }
            ]
            for item in encrypted
        ],
    }

    response = client.post("/deanonymize", json=decrypt_body)
    body = json.loads(response.data)

    assert response.status_code == 200
    assert isinstance(body, list)
    assert body[0]["text"] == "number is 034453334"
    assert body[1]["text"] == "number is 099998888"


def test_deanonymize_batch_length_mismatch_returns_422(client):
    request_body = {
        "text": ["one", "two"],
        "deanonymizers": {"DEFAULT": {"type": "decrypt", "key": "1111111111111111"}},
        "anonymizer_results": [[]],
    }

    response = client.post("/deanonymize", json=request_body)
    body = json.loads(response.data)

    assert response.status_code == 422
    assert "anonymizer_results" in body["error"]
