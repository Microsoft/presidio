import base64
import hmac
import os
from hashlib import sha256

import pytest

from presidio_anonymizer.operators import AESCipher


@pytest.mark.parametrize(
    # fmt: off
    "key,text",
    [
        (b'1111111111111111', "text_for_encryption"),  # 16 bits key
        (b'111111111111111111111111', "text_for_encryption"),  # 24 bits key
        (b'11111111111111111111111111111111', "text_for_encryption"),  # 32 bits key
        (b'1111111111111111', "PII with a Résumé"),  # Text with e-acute
        (b'1111111111111111', "面汤"),  # Chinese text
        (b'1111111111111111', "הצפן אותי"),  # Hebrew text
        (b'1111111111111111', "😈😈😈😈"),  # Text with EmojiSources character
        (os.urandom(16), "text_for_encryption"),   # random 16 bits key
    ],
    # fmt: on
)
def test_given_valid_key_and_text_then_text_encryption_and_decryption_returns_same_text(
    key, text
):
    encrypted_text = AESCipher.encrypt(key, text)

    decrypted_text = AESCipher.decrypt(key, encrypted_text)
    assert text == decrypted_text


@pytest.mark.parametrize(
    # fmt: off
    "key,text",
    [
        (b'1111111111111111', "text_for_encryption"),  # 16 bits key
        (b'111111111111111111111111', "text_for_encryption"),  # 24 bits key
        (b'11111111111111111111111111111111', "text_for_encryption"),  # 32 bits key
        (b'1111111111111111', "PII with a Résumé"),  # Text with e-acute
        (b'1111111111111111', "面汤"),  # Chinese text
        (b'1111111111111111', "הצפן אותי"),  # Hebrew text
        (b'1111111111111111', "😈😈😈😈"),  # Text with EmojiSources character
    ],
    # fmt: on
)
def test_given_deterministic_then_same_key_and_text_return_same_encrypted_text(
    key, text
):
    encrypted_text = AESCipher.encrypt(key, text, deterministic=True)

    assert encrypted_text == AESCipher.encrypt(key, text, deterministic=True)
    assert AESCipher.decrypt(key, encrypted_text) == text


def test_given_no_deterministic_then_same_key_and_text_return_different_texts():
    key = b"1111111111111111"

    assert AESCipher.encrypt(key, "text_for_encryption") != AESCipher.encrypt(
        key, "text_for_encryption"
    )


def test_given_deterministic_then_different_texts_return_different_encrypted_texts():
    key = b"1111111111111111"

    assert AESCipher.encrypt(key, "text_for_encryption", deterministic=True) != (
        AESCipher.encrypt(key, "another_text_for_encryption", deterministic=True)
    )


def test_given_deterministic_then_different_keys_return_different_encrypted_texts():
    text = "text_for_encryption"

    assert AESCipher.encrypt(b"1111111111111111", text, deterministic=True) != (
        AESCipher.encrypt(b"2222222222222222", text, deterministic=True)
    )


def test_given_deterministic_then_iv_is_keyed_and_not_a_bare_hash_of_the_text():
    key = b"1111111111111111"
    text = "text_for_encryption"
    encoded_text = text.encode("utf-8")

    encrypted_text = AESCipher.encrypt(key, text, deterministic=True)
    iv = base64.urlsafe_b64decode(encrypted_text)[:16]

    iv_key = hmac.new(key, b"presidio-anonymizer/deterministic-iv", sha256).digest()
    assert iv == hmac.new(iv_key, encoded_text, sha256).digest()[:16]
    # An unkeyed digest would let anyone confirm a guessed value from the IV.
    assert iv != sha256(encoded_text).digest()[:16]
    # And the key driving AES does not also key the value published in the clear.
    assert iv != hmac.new(key, encoded_text, sha256).digest()[:16]


def test_given_invalid_key_length_then_value_error_raised():
    invalid_length_key = b"1111"
    with pytest.raises(ValueError, match="Invalid key size \(32\) for AES"):
        AESCipher.encrypt(invalid_length_key, "text")


@pytest.mark.parametrize(
    # fmt: off
    "key,is_valid",
    [
        (b'', False),  # Empty bit-string key
        (b'1111111111111111', True),  # 16 bits key
        (b'11111111111111111', False),  # 17 bits key
        (b'111111111111111111111111', True),  # 24 bits key
        (b'1111111111111111111111111', False),  # 25 bits key
        (b'11111111111111111111111111111111', True),  # 32 bits key
        (b'111111111111111111111111111111111', False),  # 33 bits key
        (os.urandom(16), True),  # random 16 bits key
    ],
    # fmt: on
)
def test_given_is_valid_key_size_called_then_aes_valid_key_sizes_returned(
    key, is_valid
):
    assert AESCipher.is_valid_key_size(key) == is_valid
