import pytest

from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.deanonymize_engine import DeanonymizeEngine
from presidio_anonymizer.entities import (
    InvalidParamError,
    RecognizerResult,
    OperatorResult,
    OperatorConfig,
)
from presidio_anonymizer.operators import Decrypt, OperatorType, DeanonymizeKeep
from tests.mock_operators import create_reverser_operator


def test_given_operator_decrypt_with_valid_params_then_decrypt_text_successfully():
    text = "My name is S184CMt9Drj7QaKQ21JTrpYzghnboTF9pn/neN8JME0="
    encryption_results = [
        OperatorResult(start=11, end=55, entity_type="PERSON"),
    ]
    engine = DeanonymizeEngine()
    decryption = engine.deanonymize(
        text,
        encryption_results,
        {"DEFAULT": OperatorConfig(Decrypt.NAME, {"key": b"WmZq4t7w!z%C&F)J"})},
    )
    assert decryption.text == "My name is Chloë"
    assert len(decryption.items) == 1
    assert decryption.items[0].text == "Chloë"
    assert decryption.items[0].end == 16
    assert decryption.items[0].start == 11
    assert decryption.items[0].entity_type == "PERSON"


def test_empty_text_returns_empty_text():
    text = ""
    encryption_results = []
    engine = DeanonymizeEngine()
    decryption = engine.deanonymize(
        text,
        encryption_results,
        {"DEFAULT": OperatorConfig(Decrypt.NAME, {"key": "WmZq4t7w!z%C&F)J"})},
    )

    assert text == decryption.text


def test_given_short_key_then_we_fail():
    text = "My name is S184CMt9Drj7QaKQ21JTrpYzghnboTF9pn/neN8JME0="
    encryption_results = [
        OperatorResult(start=11, end=55, entity_type="PERSON"),
    ]
    engine = DeanonymizeEngine()
    expected_result = "Invalid input, key must be of length 128, 192 or 256 bits"
    with pytest.raises(InvalidParamError, match=expected_result):
        engine.deanonymize(
            text,
            encryption_results,
            {"PERSON": OperatorConfig(Decrypt.NAME, {"key": "1234"})},
        )


def test_given_deterministic_encrypt_then_repeated_pii_shares_one_decryptable_value():
    key = "WmZq4t7w!z%C&F)J"
    text = "My name is Chloë and not Chloë"
    analyzer_results = [
        RecognizerResult("PERSON", 11, 16, 0.8),
        RecognizerResult("PERSON", 25, 30, 0.8),
    ]
    anonymizers_config = {
        "PERSON": OperatorConfig("encrypt", {"key": key, "deterministic": True})
    }

    anonymized = AnonymizerEngine().anonymize(
        text, analyzer_results, anonymizers_config
    )

    # Referential integrity: both occurrences encrypt to the same value.
    assert anonymized.items[0].text == anonymized.items[1].text

    decryption = DeanonymizeEngine().deanonymize(
        anonymized.text,
        anonymized.items,
        {"DEFAULT": OperatorConfig(Decrypt.NAME, {"key": key})},
    )

    assert decryption.text == text


def test_given_anonymize_with_encrypt_then_text_returned_with_encrypted_content():
    unencrypted_text = "My name is "
    expected_encrypted_text = "Chloë"
    text = unencrypted_text + expected_encrypted_text
    start_index = 11
    end_index = 16
    key = "WmZq4t7w!z%C&F)J"
    analyzer_results = [RecognizerResult("PERSON", start_index, end_index, 0.8)]
    anonymizers_config = {"PERSON": OperatorConfig("encrypt", {"key": key})}

    actual_anonymize_result = AnonymizerEngine().anonymize(
        text, analyzer_results, anonymizers_config
    )

    assert len(actual_anonymize_result.items) == 1
    anonymized_entities = actual_anonymize_result.items

    engine = DeanonymizeEngine()
    decryption = engine.deanonymize(
        actual_anonymize_result.text,
        anonymized_entities,
        {"PERSON": OperatorConfig(Decrypt.NAME, {"key": key})},
    )
    assert decryption.text == "My name is Chloë"
    assert len(decryption.items) == 1
    assert decryption.items[0].text == "Chloë"
    assert decryption.items[0].end == 16
    assert decryption.items[0].start == 11
    assert decryption.items[0].entity_type == "PERSON"


def test_given_request_deanonymizers_return_list():
    engine = DeanonymizeEngine()
    expected_list = ["deanonymize_keep", "decrypt"]
    anon_list = engine.get_deanonymizers()

    assert len(anon_list) == len(expected_list)
    assert set(anon_list) == set(expected_list)


def test_add_deanonymizer_returns_updated_list(mock_deanonymizer_cls):
    engine = DeanonymizeEngine()
    deanon_list_len = len(engine.get_deanonymizers())
    engine.add_deanonymizer(mock_deanonymizer_cls)
    deanon_list = engine.get_deanonymizers()
    assert len(deanon_list) == deanon_list_len + 1
    assert mock_deanonymizer_cls().operator_name() in deanon_list


def test_e2e_custom_operator_returns_original():
    text = "hello"
    recognizer_results = [RecognizerResult("WORD", 0, 5, 0.8)]
    anonymizer_engine = AnonymizerEngine()
    anonymizer_engine.add_anonymizer(create_reverser_operator(OperatorType.Anonymize))
    anonymized = anonymizer_engine.anonymize(
        text, recognizer_results, {"WORD": OperatorConfig("Reverser")}
    )

    assert anonymized.text == text[::-1]

    deanonymizer_engine = DeanonymizeEngine()
    deanonymizer_engine.add_deanonymizer(
        create_reverser_operator(OperatorType.Deanonymize)
    )
    deanonymized = deanonymizer_engine.deanonymize(
        anonymized.text, anonymized.items, {"WORD": OperatorConfig("Reverser")}
    )

    assert deanonymized.text == text


def test_remove_deanonymizer_removes_anonymizer():
    engine = DeanonymizeEngine()
    num_of_deanonymizers = len(engine.get_deanonymizers())
    engine.remove_deanonymizer(DeanonymizeKeep)
    deanonymizers = engine.get_deanonymizers()
    assert len(deanonymizers) == num_of_deanonymizers - 1
