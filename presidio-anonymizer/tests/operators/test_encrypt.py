from unittest import mock

import pytest

from presidio_anonymizer.operators import Encrypt, AESCipher
from presidio_anonymizer.entities import InvalidParamError


@mock.patch.object(AESCipher, "encrypt")
def test_given_anonymize_then_aes_encrypt_called_and_its_result_is_returned(
    mock_encrypt,
):
    expected_anonymized_text = "encrypted_text"
    mock_encrypt.return_value = expected_anonymized_text

    anonymized_text = Encrypt().operate(text="text", params={"key": "key"})

    assert anonymized_text == expected_anonymized_text


@mock.patch.object(AESCipher, "encrypt")
def test_given_anonymize_with_bytes_key_then_aes_encrypt_result_is_returned(
        mock_encrypt,
):
    expected_anonymized_text = "encrypted_text"
    mock_encrypt.return_value = expected_anonymized_text

    anonymized_text = Encrypt().operate(text="text",
                                        params={"key": b'1111111111111111'})

    assert anonymized_text == expected_anonymized_text


def test_given_verifying_an_valid_length_key_no_exceptions_raised():
    Encrypt().validate(params={"key": "128bitslengthkey"})


def test_given_verifying_an_valid_length_bytes_key_no_exceptions_raised():
    Encrypt().validate(params={"key": b'1111111111111111'})


@pytest.mark.parametrize("value", [0, "", [], "true", 1])
def test_given_a_falsy_or_non_boolean_deterministic_then_ipe_raised(value):
    # `validate_type` skips falsy values, so these would otherwise be read as
    # False and the caller would silently get random IVs instead of an error.
    with pytest.raises(
        InvalidParamError,
        match="Invalid parameter value for deterministic.",
    ):
        Encrypt().validate(params={"key": "1111111111111111", "deterministic": value})


def test_given_verifying_an_invalid_length_key_then_ipe_raised():
    with pytest.raises(
        InvalidParamError,
        match="Invalid input, key must be of length 128, 192 or 256 bits",
    ):
        Encrypt().validate(params={"key": "key"})


@mock.patch.object(AESCipher, "encrypt")
def test_given_no_deterministic_param_then_aes_encrypt_called_with_false(
    mock_encrypt,
):
    mock_encrypt.return_value = "encrypted_text"

    Encrypt().operate(text="text", params={"key": "key"})

    assert mock_encrypt.call_args.kwargs["deterministic"] is False


@mock.patch.object(AESCipher, "encrypt")
def test_given_deterministic_param_then_it_is_passed_to_aes_encrypt(
    mock_encrypt,
):
    mock_encrypt.return_value = "encrypted_text"

    Encrypt().operate(text="text", params={"key": "key", "deterministic": True})

    assert mock_encrypt.call_args.kwargs["deterministic"] is True


def test_given_deterministic_then_the_same_text_is_encrypted_to_the_same_value():
    params = {"key": "128bitslengthkey", "deterministic": True}

    encrypted_text = Encrypt().operate(text="James Bond", params=params)

    assert encrypted_text == Encrypt().operate(text="James Bond", params=params)
    assert AESCipher.decrypt(b"128bitslengthkey", encrypted_text) == "James Bond"


def test_given_verifying_a_deterministic_boolean_then_no_exceptions_raised():
    Encrypt().validate(params={"key": "128bitslengthkey", "deterministic": True})
    Encrypt().validate(params={"key": "128bitslengthkey", "deterministic": False})


def test_given_verifying_a_non_boolean_deterministic_then_ipe_raised():
    with pytest.raises(
        InvalidParamError,
        match="Invalid parameter value for deterministic. "
        "Expecting 'boolean', but got 'string'.",
    ):
        Encrypt().validate(params={"key": "128bitslengthkey", "deterministic": "yes"})
