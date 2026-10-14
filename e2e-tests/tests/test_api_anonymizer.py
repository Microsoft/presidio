import json

import pytest

from common.assertions import equal_json_strings
from common.methods import anonymize, anonymizers, deanonymize


@pytest.mark.api
def test_given_anonymize_called_with_valid_request_then_expected_valid_response_returned():
    request_body = """
    {
        "text": "hello world, my name is Jane Doe. My number is: 034453334",
        "anonymizers": {
            "DEFAULT": { "type": "replace", "new_value": "ANONYMIZED" },
            "PHONE_NUMBER": { "type": "mask", "masking_char": "*", "chars_to_mask": 4, "from_end": true }
        },
        "analyzer_results": [
            { "start": 24, "end": 32, "score": 0.8, "entity_type": "NAME" },
            { "start": 24, "end": 28, "score": 0.8, "entity_type": "FIRST_NAME" },
            { "start": 29, "end": 32, "score": 0.6, "entity_type": "LAST_NAME" },
            { "start": 48, "end": 57,  "score": 0.95,
                "entity_type": "PHONE_NUMBER" }
        ]
    }
    """

    response_status, response_content = anonymize(request_body)

    expected_response = """
    {
        "text": "hello world, my name is ANONYMIZED. My number is: 03445****", 
        "items": [
            {"operator": "mask", "entity_type": "PHONE_NUMBER", "start": 50, "end": 59, "text":"03445****", "score": 0.95}, 
            {"operator": "replace", "entity_type": "NAME", "start": 24, "end": 34, "text":"ANONYMIZED", "score": 0.8}
        ]
    }
    """

    assert response_status == 200
    assert equal_json_strings(expected_response, response_content)


@pytest.mark.api
def test_given_anonymize_called_with_empty_text_then_invalid_input_message_returned():
    request_body = """
    {
        "text": "",
        "anonymizers": {
            "DEFAULT": { "type": "replace", "new_value": "ANONYMIZED" }
        },
        "analyzer_results": []
    }
    """

    response_status, response_content = anonymize(request_body)

    expected_response = """{"text": "", "items": []}"""
    assert response_status == 200
    assert equal_json_strings(expected_response, response_content)


@pytest.mark.api
def test_given_anonymize_called_with_empty_analyzer_results_then_unchanged_text_is_returned():
    request_body = """
    {
        "text": "hello world! nice to meet you!",
        "anonymizers": {
            "DEFAULT": { "type": "replace", "new_value": "ANONYMIZED" },
            "PHONE_NUMBER": { "type": "mask", "masking_char": "*", "chars_to_mask": 4, "from_end": true }
        },
        "analyzer_results": [

        ]
    }
    """
    response_status, response_content = anonymize(request_body)

    expected_response = """{"text": "hello world! nice to meet you!", "items": []}"""
    assert response_status == 200
    assert equal_json_strings(expected_response, response_content)


@pytest.mark.api
def test_given_anonymize_called_with_deformed_body_then_bad_request_error_returned():
    request_body = """
    {
        "text": "hello world, my name is Jane Doe. My number is: 034453334",
        "anonymizers": {
            "DEFAULT": {"type": "replace", "new_value": "ANONYMIZED"},
        },
        "analyzer_results": [
            {"start": 24, "end": 32, "score": 0.8, "entity_type": "NAME"},
            {"start": 24, "end": 28, "score": 0.8, "entity_type": "FIRST_NAME"},
        ]
    }
    """
    response_status, response_content = anonymize(request_body)

    expected_response = '{"error": "The browser (or proxy) sent a request that this server could not understand."}'
    assert response_status == 400
    assert equal_json_strings(expected_response, response_content)


@pytest.mark.api
def test_given_anonymize_called_with_custom_then_bad_request_error_returned():
    request_body = """
    {
        "text": "The user has the following two emails: email1@conto.com and email2@conto.com",
        "anonymizers": {
            "DEFAULT": { "type": "custom", "new_value": "lambda x:  x[::-1]" }            
        },
        "analyzer_results": [
            { "start": 39, "end": 55, "score": 1.0, "entity_type": "EMAIL_ADDRESS" },
            { "start": 60, "end": 76, "score": 1.0, "entity_type": "EMAIL_ADDRESS" }
        ]
    }
    """
    response_status, response_content = anonymize(request_body)

    expected_response = '{"error": "Custom type anonymizer is not supported"}'
    assert response_status == 400
    assert equal_json_strings(expected_response, response_content)


@pytest.mark.api
def test_given_anonymizers_called_then_expected_anonymizers_list_returned():
    response_status, response_content = anonymizers()

    expected_response = """
        ["hash", "mask", "redact", "replace", "encrypt", "custom"]
    """

    assert response_status == 200
    assert equal_json_strings(expected_response, response_content)


@pytest.mark.api
def test_given_decrypt_called_with_encrypted_text_then_decrypted_text_returned():
    text = "e6HnOMnIxbd4a8Qea44LshQDnjvxwzBIaAz+YqHNnMW2mC5r3AWoay8Spsoajyyy"
    request_body = {
        "text": text,
        "deanonymizers": {"NUMBER": {"type": "decrypt", "key": "1111111111111111"}},
        "anonymizer_results": [{"start": 0, "end": len(text), "entity_type": "NUMBER"}],
    }

    response_status, response_content = deanonymize(json.dumps(request_body))

    expected_response = """{"text": "text_for_encryption", "items": [{"start": 0, "end": 19, "operator":"decrypt", "text": "text_for_encryption","entity_type":"NUMBER", "score": null}]}"""

    assert response_status == 200
    assert equal_json_strings(expected_response, response_content)


@pytest.mark.api
def test_given_decrypt_called_with_invalid_key_then_invalid_input_response_returned():
    text = "e6HnOMnIxbd4a8Qea44LshQDnjvxwzBIaAz + YqHNnMW2mC5r3AWoay8Spsoajyyy"
    request_body = {
        "text": text,
        "deanonymizers": {"NUMBER": {"type": "decrypt", "key": "invalidkey"}},
        "anonymizer_results": [{"start": 0, "end": len(text), "entity_type": "NUMBER"}],
    }

    response_status, response_content = deanonymize(json.dumps(request_body))

    expected_response = """
    {
        "error": "Invalid input, key must be of length 128, 192 or 256 bits"
    }
    """

    assert response_status == 422
    assert equal_json_strings(expected_response, response_content)


@pytest.mark.api
def test_given_decrypt_called_with_missing_key_then_invalid_input_response_returned():
    request_body = """
    {
        "text": "e6HnOMnIxbd4a8Qea44LshQDnjvxwzBIaAz+YqHNnMW2mC5r3AWoay8Spsoajyyy"
    }
    """

    response_status, response_content = deanonymize(request_body)

    expected_response = """{"text": "e6HnOMnIxbd4a8Qea44LshQDnjvxwzBIaAz+YqHNnMW2mC5r3AWoay8Spsoajyyy", "items": []}"""
    assert response_status == 200
    assert equal_json_strings(expected_response, response_content)


@pytest.mark.api
def test_given_decrypt_called_with_missing_text_then_empty_text_is_returned():
    request_body = """
    {
        "key": "1111111111111111"
    }
    """

    response_status, response_content = deanonymize(request_body)

    expected_response = """{"text": "", "items": []}"""

    assert response_status == 200
    assert equal_json_strings(expected_response, response_content)


@pytest.mark.api
def test_given_decrypt_called_with_missing_payload_then_bad_request_response_returned():
    request_body = """
    { }
    """

    response_status, response_content = deanonymize(request_body)

    expected_response = """
    {
        "error": "Invalid request json"
    }
    """

    assert response_status == 400
    assert equal_json_strings(expected_response, response_content)


@pytest.mark.api
def test_given_encrypt_called_then_decrypt_returns_the_original_encrypted_text():
    text_for_encryption = "Lorem Ipsum is a Software Engineer"
    key = "1111111111111111"
    anonymize_request = {
        "text": text_for_encryption,
        "anonymizers": {
            "DEFAULT": {"type": "encrypt", "key": key},
            "TITLE": {"type": "encrypt", "key": "2222222222222222"},
        },
        "analyzer_results": [
            {
                "start": 0,
                "end": 12,
                "score": 0.8,
                "entity_type": "NAME",
            },
            {
                "start": 18,
                "end": len(text_for_encryption),
                "score": 0.8,
                "entity_type": "TITLE",
            },
        ],
    }
    _, anonymize_response_content = anonymize(json.dumps(anonymize_request))
    encrypted_text = json.loads(anonymize_response_content)["text"]

    decrypt_request = {
        "text": encrypted_text,
        "deanonymizers": {
            "DEFAULT": {"type": "decrypt", "key": "1111111111111111"},
            "TITLE": {"type": "decrypt", "key": "2222222222222222"},
        },
        "anonymizer_results": [
            {
                "start": 0,
                "end": 44,
                "entity_type": "NAME",
            },
            {
                "start": 50,
                "end": 114,
                "entity_type": "TITLE",
            },
        ],
    }

    _, decrypted_text_response = deanonymize(json.dumps(decrypt_request))

    decrypted_text = json.loads(decrypted_text_response)["text"]
    assert decrypted_text == text_for_encryption


@pytest.mark.api
def test_keep_name():
    request_body = """
    {
        "text": "hello world, my name is Jane Doe. My number is: 034453334",
        "anonymizers": {
            "NAME": { "type": "keep"},
            "PHONE_NUMBER": { "type": "replace" }
        },
        "analyzer_results": [
            { "start": 24, "end": 32, "score": 0.80, "entity_type": "NAME" },
            { "start": 48, "end": 57, "score": 0.95, "entity_type": "PHONE_NUMBER" }
        ]
    }
    """

    response_status, response_content = anonymize(request_body)

    expected_response = """
    {
        "text": "hello world, my name is Jane Doe. My number is: <PHONE_NUMBER>", 
        "items": [
            {"operator": "replace", "entity_type": "PHONE_NUMBER", "start": 48, "end": 62, "text":"<PHONE_NUMBER>", "score": 0.95}, 
            {"operator": "keep", "entity_type": "NAME", "start": 24, "end": 32, "text":"Jane Doe", "score": 0.8}
        ]
    }
    """

    assert response_status == 200
    assert equal_json_strings(expected_response, response_content)


@pytest.mark.api
def test_overlapping_keep_first():
    request_body = """
    {
        "text": "I'm George Washington Square Park",
        "anonymizers": {
            "NAME": { "type": "keep"},
            "LOCATION": { "type": "replace" }
        },
        "analyzer_results": [
            { "start": 4, "end": 21, "score": 0.80, "entity_type": "NAME" },
            { "start": 11, "end": 33, "score": 0.80, "entity_type": "LOCATION" }
        ]
    }
    """

    response_status, response_content = anonymize(request_body)

    expected_response = """
    {
        "text": "I'm George Washington<LOCATION>", 
        "items": [
            {"operator": "replace", "entity_type": "LOCATION", "start": 21, "end": 31, "text":"<LOCATION>", "score": 0.8}, 
            {"operator": "keep", "entity_type": "NAME", "start": 4, "end": 21, "text":"George Washington", "score": 0.8}
        ]
    }
    """

    assert response_status == 200
    assert equal_json_strings(expected_response, response_content)


@pytest.mark.api
def test_overlapping_keep_second():
    request_body = """
    {
        "text": "I'm George Washington Square Park",
        "anonymizers": {
            "NAME": { "type": "replace"},
            "LOCATION": { "type": "keep" }
        },
        "analyzer_results": [
            { "start": 4, "end": 21, "score": 0.80, "entity_type": "NAME" },
            { "start": 11, "end": 33, "score": 0.80, "entity_type": "LOCATION" }
        ]
    }
    """

    response_status, response_content = anonymize(request_body)

    expected_response = """
    {
        "text": "I'm <NAME>Washington Square Park", 
        "items": [
            {"operator": "keep", "entity_type": "LOCATION", "start": 10, "end": 32, "text":"Washington Square Park", "score": 0.8}, 
            {"operator": "replace", "entity_type": "NAME", "start": 4, "end": 10, "text":"<NAME>", "score": 0.8}
        ]
    }
    """

    assert response_status == 200
    assert equal_json_strings(expected_response, response_content)


@pytest.mark.api
def test_overlapping_keep_both():
    request_body = """
    {
        "text": "I'm George Washington Square Park",
        "anonymizers": {
            "DEFAULT": { "type": "keep" }
        },
        "analyzer_results": [
            { "start": 4, "end": 21, "score": 0.80, "entity_type": "NAME" },
            { "start": 11, "end": 33, "score": 0.80, "entity_type": "LOCATION" }
        ]
    }
    """

    response_status, response_content = anonymize(request_body)

    expected_response = """
    {
        "text": "I'm George WashingtonWashington Square Park", 
        "items": [
            {"operator": "keep", "entity_type": "LOCATION", "start": 21, "end": 43, "text":"Washington Square Park", "score": 0.8}, 
            {"operator": "keep", "entity_type": "NAME", "start": 4, "end": 21, "text":"George Washington", "score": 0.8}
        ]
    }
    """

    assert response_status == 200
    assert equal_json_strings(expected_response, response_content)
