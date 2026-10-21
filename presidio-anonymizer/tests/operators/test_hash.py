import pytest

from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import (
    InvalidParamError,
    OperatorConfig,
    RecognizerResult,
)
from presidio_anonymizer.operators import Hash


@pytest.mark.parametrize(
    "text, anonymized_text",
    [
        # fmt: off
        (
            "123456",
            "09cc8b29be2dbdcef23f37ba045fd9eddbd9900473260cb72651e4e62715eba4",
        ),  # Hash 123456 + salt
        (
            "54321",
            "677280e77c0b09c902fc2c5dcbaa8667c66ff00dfb96afed583355ce326b82b1",
        ),  # Hash 54321 + salt
        (
            "😈😈😈😈",
            "a42d48e20f00251055b13aaa0b4596045dba4c409f96ebe541f80048cbbf9e5f",
        ),
        # Hash 'Unicode EmojiSources' character + salt
        # fmt: on
    ],
)
def test_when_given_valid_value_without_hash_type_then_expected_sha256_string_returned(
    text, anonymized_text
):
    params = {"salt": b"0123456789abcdef"}
    actual_anonymized_text = Hash().operate(text=text, params=params)

    assert anonymized_text == actual_anonymized_text


@pytest.mark.parametrize(
    "text, hash_type, anonymized_text",
    [
        # fmt: off
        (
            "123456",
            "sha256",
            "09cc8b29be2dbdcef23f37ba045fd9eddbd9900473260cb72651e4e62715eba4",
        ),  # Sha256 Hash 123456 + salt
        (
            "54321",
            "sha256",
            "677280e77c0b09c902fc2c5dcbaa8667c66ff00dfb96afed583355ce326b82b1",
        ),  # Sha256 Hash 54321 + salt
        (
            "😈😈😈😈",
            "sha256",
            "a42d48e20f00251055b13aaa0b4596045dba4c409f96ebe541f80048cbbf9e5f",
        ),  # Sha256 Hash 'Unicode EmojiSources' character + salt
        (
            "123456",
            "sha512",
            "94ca1fb2ea72ef4ec2bb191a68e2b16708881be543c0c90c1ec329b9c04c231"
            "3350fa129c5395c308fc7de7e16d5c09fb804da0a84f254638c72ce11ce06d7b6",
        ),  # Sha512 Hash 123456 + salt
        (
            "54321",
            "sha512",
            "c6f994054cd8be2769b94f74a00bc580f19d17ab0a2d99c732d682b6dfec76ae"
            "666a44bc475c996b47ac5c4657dc68037d0c9a70c931a402e47031fc6081761c",
        ),  # Sha512 Hash 54321 + salt
        (
            "😈😈😈😈",
            "sha512",
            "a01d392a6a28fea6496fc3ad5b0d56420d24032de2ef41dfd3f378ac7ad0dbc2"
            "dce9d9714a6c95e6b119bd01b7c4f1af95dde222f9dc68fa0dee91649b0f98cf",
        ),  # Sha512 Hash 'Unicode EmojiSources' character + salt
        # fmt: on
    ],
)
def test_when_given_valid_value_with_hash_type_then_expected_string_returned(
    text, hash_type, anonymized_text
):
    params = {
        "hash_type": hash_type,
        "salt": b"0123456789abcdef",
    }
    actual_anonymized_text = Hash().operate(text=text, params=params)

    assert anonymized_text == actual_anonymized_text


def test_when_hash_type_not_in_range_then_ipe_raised():
    params = _get_default_hash_parameters()
    params["hash_type"] = "not_a_hash"

    with pytest.raises(
        InvalidParamError,
        match="Parameter hash_type value not_a_hash is not in range of values"
        " \\['sha256', 'sha512'\\]",
    ):
        Hash().validate(params)


def test_when_hash_type_is_missing_then_we_pass():
    params = _get_default_hash_parameters()
    params.pop("hash_type")

    Hash().validate(params)


def test_when_hash_type_is_empty_string_then_ipe_raised():
    params = _get_default_hash_parameters()
    params["hash_type"] = ""

    with pytest.raises(
        InvalidParamError,
        match="Parameter hash_type value  is not in range of values"
        " \\['sha256', 'sha512'\\]",
    ):
        Hash().validate(params)


def test_when_validate_anonymizer_then_correct_name():
    assert Hash().operator_name() == "hash"


def test_when_salt_provided_then_hash_is_different():
    """Test that providing salt changes the hash output."""
    text = "123456"
    
    # Hash without salt
    params_no_salt = {}
    hash_no_salt = Hash().operate(text=text, params=params_no_salt)
    
    # Hash with salt (must be at least 16 bytes)
    params_with_salt = {"salt": b"random_salt_val1"}  # 16 bytes
    hash_with_salt = Hash().operate(text=text, params=params_with_salt)
    
    # Hashes should be different
    assert hash_no_salt != hash_with_salt


def test_when_same_salt_provided_then_hash_is_deterministic():
    """Test that same text with same salt produces same hash."""
    text = "sensitive_data"
    salt = b"my_secret_salt16"  # 16 bytes minimum
    
    params = {"salt": salt}
    hash1 = Hash().operate(text=text, params=params)
    hash2 = Hash().operate(text=text, params=params)
    
    # Same text + same salt should produce same hash
    assert hash1 == hash2


def test_when_different_salt_provided_then_hash_is_different():
    """Test that same text with different salts produces different hashes."""
    text = "sensitive_data"
    
    params1 = {"salt": b"salt1_0123456789"}  # 16 bytes
    hash1 = Hash().operate(text=text, params=params1)
    
    params2 = {"salt": b"salt2_0123456789"}  # 16 bytes
    hash2 = Hash().operate(text=text, params=params2)
    
    # Same text + different salt should produce different hashes
    assert hash1 != hash2


def test_when_salt_is_string_then_it_is_converted_to_bytes():
    """Test that string salt is properly converted to bytes."""
    text = "data"
    salt_str = "my_salt123456789"  # 16 chars = 16 bytes
    salt_bytes = b"my_salt123456789"
    
    params_str = {"salt": salt_str}
    hash_str = Hash().operate(text=text, params=params_str)
    
    params_bytes = {"salt": salt_bytes}
    hash_bytes = Hash().operate(text=text, params=params_bytes)
    
    # String and bytes salt should produce same hash
    assert hash_str == hash_bytes


def test_when_no_salt_provided_then_random_salt_is_used():
    """Test that when no salt is provided, operator generates random salt per call."""
    text = "123456"
    
    # Create one operator instance
    operator = Hash()
    
    # Hash same text twice without salt
    params = {}
    hash1 = operator.operate(text=text, params=params)
    hash2 = operator.operate(text=text, params=params)
    
    # Each call should produce different hash (random salt per call)
    assert hash1 != hash2
    
    # Different operator instance should also produce different hash
    operator2 = Hash()
    hash3 = operator2.operate(text=text, params=params)
    assert hash1 != hash3
    assert hash2 != hash3


def test_when_user_salt_provided_then_hash_is_deterministic():
    """Test that user-provided salt produces deterministic hashes."""
    text = "data"
    user_salt = b"user_salt_123456"  # 16 bytes minimum
    
    # Create two operator instances
    operator1 = Hash()
    operator2 = Hash()
    
    # Use same user salt with both operators
    params = {"salt": user_salt}
    hash1 = operator1.operate(text=text, params=params)
    hash2 = operator2.operate(text=text, params=params)
    
    # Should produce same hash (deterministic with user salt)
    assert hash1 == hash2
    
    # Verify it's different from hash without explicit salt
    params_no_salt = {}
    hash_no_explicit_salt = operator1.operate(text=text, params=params_no_salt)
    # Random salt will produce different hash
    assert hash1 != hash_no_explicit_salt


def test_when_salt_too_short_then_error_raised():
    """Test that salt shorter than 16 bytes raises InvalidParamError."""
    text = "data"
    short_salt = b"short"  # Only 5 bytes, less than minimum 16
    
    params = {"salt": short_salt}
    with pytest.raises(
        InvalidParamError,
        match="Salt must be at least 16 bytes"
    ):
        Hash().operate(text=text, params=params)


def test_when_salt_is_empty_then_error_raised():
    """Test that empty salt parameter raises InvalidParamError."""
    text = "data"
    empty_salt = b""  # Empty salt
    
    params = {"salt": empty_salt}
    with pytest.raises(
        InvalidParamError,
        match="Salt parameter cannot be empty"
    ):
        Hash().operate(text=text, params=params)


def test_when_salt_minimum_length_then_accepted():
    """Test that salt with exactly 16 bytes is accepted."""
    text = "data"
    min_salt = b"0123456789abcdef"  # Exactly 16 bytes
    
    params = {"salt": min_salt}
    # Should not raise an error
    result = Hash().operate(text=text, params=params)
    assert result is not None
    assert len(result) == 64  # SHA256 default produces 64 hex characters


@pytest.mark.parametrize(
    "bad_salt",
    [
        1234567890123456,  # a number in a JSON request body
        1.5,
        True,
        ["0123456789abcdef"],  # array, long enough to pass a bare len() check
        {"salt": "0123456789abcdef"},  # object, same as above
    ],
)
def test_when_salt_is_not_a_string_or_bytes_then_validate_raises(bad_salt):
    """A wrongly typed salt must be rejected by validate(), not crash operate()."""
    with pytest.raises(InvalidParamError, match="Salt must be a string or bytes"):
        Hash().validate(params={"salt": bad_salt})


def test_when_salt_is_missing_or_none_then_random_salt_is_used():
    """An omitted or null salt keeps hashing non-deterministic."""
    with_none_salt = [
        Hash().operate(text="data", params={"salt": None}) for _ in range(5)
    ]
    without_salt = [Hash().operate(text="data", params={}) for _ in range(5)]
    assert len(set(with_none_salt + without_salt)) > 1


def test_when_salt_type_is_invalid_then_anonymize_raises_invalid_param_error():
    """The engine validates operators, so a bad salt never reaches operate()."""
    engine = AnonymizerEngine()
    with pytest.raises(InvalidParamError, match="Invalid salt type 'int'"):
        engine.anonymize(
            text="Call 555-555-5555",
            analyzer_results=[
                RecognizerResult(
                    entity_type="PHONE_NUMBER", start=5, end=16, score=0.9
                )
            ],
            operators={
                "DEFAULT": OperatorConfig("hash", {"salt": 1234567890123456})
            },
        )


def _get_default_hash_parameters():
    return {"hash_type": ""}
