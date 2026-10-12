import re
import json

import pytest

from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import (
    InvalidParamError,
    RecognizerResult,
    OperatorConfig,
)
from presidio_anonymizer.operators import AESCipher, OperatorType, Redact
from tests.mock_operators import (
    create_reverser_operator,
    create_instance_counter_anonymizer,
)


def test_given_url_at_the_end_then_we_redact_is_successfully():
    text = "The url is http://microsoft.com"
    anonymizer_config = {
        "URL": OperatorConfig("redact"),
    }

    analyzer_results = [
        RecognizerResult(start=11, end=31, score=1.0, entity_type="URL"),
        RecognizerResult(start=18, end=31, score=1.0, entity_type="URL"),
    ]
    expected_result = (
        '{"text": "The url is ", "items": [{"start": 11, "end": 11, "entity_type": '
        '"URL", "text": "", "operator": "redact", "score": 1.0}]}'
    )
    run_engine_and_validate(text, anonymizer_config, analyzer_results, expected_result)


def test_given_operator_decrypt_then_we_fail():
    text = "hello world, my name is Jane Doe. My number is: 03-4453334"
    anonymizers_config = {"DEFAULT": OperatorConfig("decrypt", {"key": "key"})}
    analyzer_results = [
        RecognizerResult(start=24, end=32, score=0.8, entity_type="NAME"),
    ]
    engine = AnonymizerEngine()
    with pytest.raises(
        InvalidParamError,
        match="Invalid operator class 'decrypt'.",
    ):
        engine.anonymize(text, analyzer_results, anonymizers_config)


def test_given_name_and_phone_number_then_we_anonymize_correctly():
    text = "hello world, my name is Jane Doe. My number is: 03-4453334"
    anonymizer_config = {
        "DEFAULT": OperatorConfig(
            "mask", {"masking_char": "*", "chars_to_mask": 20, "from_end": False}
        ),
        "PHONE_NUMBER": OperatorConfig(
            "mask", {"masking_char": "*", "chars_to_mask": 6, "from_end": True}
        ),
    }
    analyzer_results = [
        RecognizerResult(start=24, end=32, score=0.8, entity_type="NAME"),
        RecognizerResult(start=48, end=57, score=0.95, entity_type="PHONE_NUMBER"),
    ]
    expected_result = (
        '{"text": "hello world, my name is ********. My number is: '
        '03-******4", "items": [{"start": 48, "end": 57, "entity_type": '
        '"PHONE_NUMBER", "text": "03-******", "operator": "mask", "score": 0.95}, '
        '{"start": 24, "end": 32, "entity_type": "NAME", '
        '"text": "********", "operator": "mask", "score": 0.8}]}'
    )
    run_engine_and_validate(text, anonymizer_config, analyzer_results, expected_result)


def test_given_name_and_phone_number_without_anonymizers_then_we_use_default():
    text = "hello world, my name is Jane Doe. My number is: 03-4453334"
    anonymizer_config = {
        "ABC": OperatorConfig(
            "mask", {"masking_char": "*", "chars_to_mask": 6, "from_end": True}
        )
    }
    analyzer_results = [
        RecognizerResult(start=24, end=32, score=0.8, entity_type="NAME"),
        RecognizerResult(start=48, end=57, score=0.95, entity_type="PHONE_NUMBER"),
    ]
    expected_result = (
        '{"text": "hello world, my name is <NAME>. My number is: '
        '<PHONE_NUMBER>4", "items": [{"start": 46, "end": 60, '
        '"entity_type": "PHONE_NUMBER", "text": "<PHONE_NUMBER>", '
        '"operator": "replace", "score": 0.95}, {"start": 24, "end": 30, '
        '"entity_type": "NAME", "text": "<NAME>", '
        '"operator": "replace", "score": 0.8}]}'
    )
    run_engine_and_validate(text, anonymizer_config, analyzer_results, expected_result)


def test_given_redact_and_replace_then_we_anonymize_successfully():
    text = "hello world, my name is Jane Doe. My number is: 03-4453334"
    anonymizer_config = {
        "NAME": OperatorConfig("redact", {"new_value": "ANONYMIZED"}),
        "PHONE_NUMBER": OperatorConfig("replace", {"new_value": ""}),
    }
    analyzer_results = [
        RecognizerResult(start=24, end=32, score=0.8, entity_type="NAME"),
        RecognizerResult(start=48, end=57, score=0.95, entity_type="PHONE_NUMBER"),
    ]
    expected_result = (
        '{"text": "hello world, my name is . My number is: '
        '<PHONE_NUMBER>4", "items": [{"start": 40, "end": 54, '
        '"entity_type": "PHONE_NUMBER", "text": "<PHONE_NUMBER>", '
        '"operator": "replace", "score": 0.95}, {"start": 24, "end": 24, '
        '"entity_type": "NAME", "text": "", "operator": '
        '"redact", "score": 0.8}]}'
    )
    run_engine_and_validate(text, anonymizer_config, analyzer_results, expected_result)


def test_given_intersecting_entities_then_we_anonymize_correctly():
    text = "hello world, my name is Jane Doe. My number is: 03-4453334"
    anonymizer_config = {}
    analyzer_results = [
        RecognizerResult(start=24, end=32, score=0.6, entity_type="FULL_NAME"),
        RecognizerResult(start=48, end=56, score=0.95, entity_type="PHONE_NUMBER"),
        RecognizerResult(start=54, end=57, score=0.8, entity_type="SSN"),
        RecognizerResult(start=24, end=28, score=0.9, entity_type="FIRST_NAME"),
        RecognizerResult(start=29, end=33, score=0.6, entity_type="LAST_NAME"),
        RecognizerResult(start=24, end=30, score=0.8, entity_type="NAME"),
    ]
    expected_result = (
        '{"text": "hello world, my name is <FULL_NAME><LAST_NAME> My '
        'number is: <PHONE_NUMBER><SSN>4", "items": [{"start": 75, '
        '"end": 80, "entity_type": "SSN", "text": "<SSN>", '
        '"operator": "replace", "score": 0.8}, {"start": 61, "end": 75, '
        '"entity_type": "PHONE_NUMBER", "text": "<PHONE_NUMBER>", '
        '"operator": "replace", "score": 0.95}, {"start": 35, "end": 46, '
        '"entity_type": "LAST_NAME", "text": "<LAST_NAME>", '
        '"operator": "replace", "score": 0.6}, {"start": 24, "end": 35, '
        '"entity_type": "FULL_NAME", "text": "<FULL_NAME>", '
        '"operator": "replace", "score": 0.6}]}'
    )
    run_engine_and_validate(text, anonymizer_config, analyzer_results, expected_result)


def test_given_intersecting_the_same_entities_then_we_anonymize_correctly():
    text = "hello world, my name is Jane Doe. My number is: 03-4453334"
    anonymizer_config = {}
    analyzer_results = [
        RecognizerResult(start=24, end=32, score=0.6, entity_type="FULL_NAME"),
        RecognizerResult(start=29, end=33, score=0.6, entity_type="FULL_NAME"),
    ]
    expected_result = (
        '{"text": "hello world, my name is <FULL_NAME> My number is: 03-4453334", '
        '"items": [{"start": 24, "end": 35, "entity_type": "FULL_NAME",'
        ' "text": "<FULL_NAME>", "operator": "replace", "score": 0.6}]}'
    )
    run_engine_and_validate(text, anonymizer_config, analyzer_results, expected_result)


@pytest.mark.parametrize(
    # fmt: off
    "hash_type,expected_hash_length",
    [
        ("sha256", 64),  # SHA256 produces 64 hex characters
        ("sha512", 128),  # SHA512 produces 128 hex characters
        ("", 64),  # Default is SHA256
    ],
    # fmt: on
)
def test_given_hash_then_we_anonymize_correctly(hash_type, expected_hash_length):
    text = "hello world, my name is Jane Doe. My number is: 034453334"
    params = {}
    if hash_type:
        params = {"hash_type": hash_type}
    anonymizer_config = {"DEFAULT": OperatorConfig("hash", params)}
    analyzer_results = [
        RecognizerResult(start=48, end=57, score=0.95, entity_type="PHONE_NUMBER"),
        RecognizerResult(start=24, end=28, score=0.8, entity_type="FIRST_NAME"),
        RecognizerResult(start=29, end=32, score=0.6, entity_type="LAST_NAME"),
        RecognizerResult(start=24, end=32, score=0.8, entity_type="NAME"),
    ]
    
    engine = AnonymizerEngine()
    result = engine.anonymize(text, analyzer_results, anonymizer_config)
    
    # Verify the structure
    assert len(result.items) == 2  # NAME and PHONE_NUMBER (merged duplicates)
    
    # Verify hash lengths
    for item in result.items:
        assert len(item.text) == expected_hash_length
        assert item.operator == "hash"
        # Verify it's a valid hex string
        assert all(c in '0123456789abcdef' for c in item.text)
        # Verify it's not the original text
        assert item.text.lower() not in text.lower()
    
    # Verify that "Jane Doe" was hashed to the same value
    # (there should be only one NAME entity due to merging)
    name_items = [item for item in result.items if item.entity_type == "NAME"]
    assert len(name_items) == 1


def test_when_hash_without_salt_then_different_hashes_per_entity():
    """Test that hash operator produces different hashes for each entity when no salt provided."""
    text = "My name is Jane Doe and Jane Doe number is: 034453334"
    anonymizer_config = {"DEFAULT": OperatorConfig("hash", {})}
    analyzer_results = [
        RecognizerResult(start=11, end=19, score=0.8, entity_type="NAME"),  # First "Jane Doe"
        RecognizerResult(start=24, end=32, score=0.8, entity_type="NAME"),  # Second "Jane Doe"
        RecognizerResult(start=44, end=53, score=0.95, entity_type="PHONE_NUMBER"),
    ]
    
    engine = AnonymizerEngine()
    result = engine.anonymize(text, analyzer_results, anonymizer_config)
    
    # Extract the hashed values
    hashed_names = [item.text for item in result.items if item.entity_type == "NAME"]
    
    # Each entity gets a different hash (no within-call consistency without user salt)
    assert len(hashed_names) == 2
    assert hashed_names[0] != hashed_names[1]


def test_when_hash_with_user_salt_then_same_values_get_same_hash():
    """Test that user-provided salt produces consistent hashes for same values."""
    text = "My name is Jane Doe and Jane Doe called"
    user_salt = "my_consistent_salt"
    anonymizer_config = {"DEFAULT": OperatorConfig("hash", {"salt": user_salt})}
    analyzer_results = [
        RecognizerResult(start=11, end=19, score=0.8, entity_type="NAME"),  # First "Jane Doe"
        RecognizerResult(start=24, end=32, score=0.8, entity_type="NAME"),  # Second "Jane Doe"
    ]
    
    engine = AnonymizerEngine()
    result = engine.anonymize(text, analyzer_results, anonymizer_config)
    
    # Extract the hashed values
    hashed_names = [item.text for item in result.items if item.entity_type == "NAME"]
    
    # With user salt, same value gets same hash (referential integrity)
    assert len(hashed_names) == 2
    assert hashed_names[0] == hashed_names[1]


def test_when_hash_with_different_sessions_then_different_hashes():
    """Test that hash operator produces different hashes across different anonymization sessions."""
    text = "My name is Jane Doe"
    anonymizer_config = {"DEFAULT": OperatorConfig("hash", {})}
    analyzer_results = [
        RecognizerResult(start=11, end=19, score=0.8, entity_type="NAME"),
    ]
    
    engine = AnonymizerEngine()
    
    # Run anonymization twice
    result1 = engine.anonymize(text, analyzer_results, anonymizer_config)
    result2 = engine.anonymize(text, analyzer_results, anonymizer_config)
    
    # Hashes should be different (different salts in different sessions)
    hash1 = result1.items[0].text
    hash2 = result2.items[0].text
    assert hash1 != hash2


def test_when_hash_with_user_provided_salt_then_hash_is_reproducible():
    """Test that user-provided salt produces reproducible hashes across sessions."""
    text = "My name is Jane Doe"
    user_salt = "my_consistent_salt"
    anonymizer_config = {"DEFAULT": OperatorConfig("hash", {"salt": user_salt})}
    analyzer_results = [
        RecognizerResult(start=11, end=19, score=0.8, entity_type="NAME"),
    ]
    
    engine = AnonymizerEngine()
    
    # Run anonymization twice with same user salt
    result1 = engine.anonymize(text, analyzer_results, anonymizer_config)
    result2 = engine.anonymize(text, analyzer_results, anonymizer_config)
    
    # Hashes should be the same (same user-provided salt)
    hash1 = result1.items[0].text
    hash2 = result2.items[0].text
    assert hash1 == hash2


@pytest.mark.parametrize(
    "text, salt, hash_type, expected_hash",
    [
        # fmt: off
        # SHA256 known-answer tests with specific salt
        (
            "123456",
            b"test_salt_16byte",  # 16 bytes exactly
            "sha256",
            "31ac5824179e43275be4f75b10886a915b8ffbe4238786dd17e2cc23325d6e47",
        ),
        (
            "Jane Doe",
            b"my_secure_salt16",  # 16 bytes exactly
            "sha256",
            "4180ab6f00d4379f01e57fc87593247f05fe2a3e3ad7b2b223d41d593ff3374e",
        ),
        # SHA512 known-answer tests with specific salt
        (
            "123456",
            b"test_salt_16byte",
            "sha512",
            "3a19179a550de9c20ff6c99d8dfd43e819835d4981fd972ac1280b393cd79357"
            "6386cafd7a955d0802760bc3169609c25f8bbf0e6b3c93c7a44ebadc223f1fa6",
        ),
        (
            "sensitive_data",
            b"0123456789abcdef",  # 16 bytes exactly
            "sha512",
            "0acd60e620b6894a99ed05d481bab628f0c3cabb3f4b37f9c8c5c2ba2cc06d4b"
            "09656c589761018cefcef8bc81b2a7ace5b4803a91e997376f4a2559e0418640",
        ),
        # fmt: on
    ],
)
def test_hash_with_known_salt_produces_expected_output(text, salt, hash_type, expected_hash):
    """Test that hashing with a known salt produces expected deterministic output."""
    
    params = {"hash_type": hash_type, "salt": salt}
    anonymizer_config = {"DEFAULT": OperatorConfig("hash", params)}
    
    # Create a simple analyzer result for the entire text
    analyzer_results = [
        RecognizerResult(start=0, end=len(text), score=0.9, entity_type="TEST"),
    ]
    
    engine = AnonymizerEngine()
    result = engine.anonymize(text, analyzer_results, anonymizer_config)
    
    # The hash should match the expected value
    assert result.items[0].text == expected_hash
    
    # Verify it's reproducible
    result2 = engine.anonymize(text, analyzer_results, anonymizer_config)
    assert result2.items[0].text == expected_hash


def test_given_single_entity_then_score_is_propagated_to_result():
    """Score from analyzer result appears on the corresponding OperatorResult."""
    text = "My name is Jane Doe"
    anonymizer_config = {"PERSON": OperatorConfig("replace")}
    analyzer_results = [
        RecognizerResult(start=11, end=19, score=0.85, entity_type="PERSON"),
    ]

    engine = AnonymizerEngine()
    result = engine.anonymize(text, analyzer_results, anonymizer_config)

    assert result.items[0].score == 0.85


def test_given_multiple_entities_then_each_score_is_propagated_correctly():
    """Each OperatorResult carries the score of its originating RecognizerResult."""
    text = "My name is Jane Doe. My number is 034453334"
    anonymizer_config = {}
    analyzer_results = [
        RecognizerResult(start=11, end=19, score=0.8, entity_type="NAME"),
        RecognizerResult(start=34, end=43, score=0.95, entity_type="PHONE_NUMBER"),
    ]

    engine = AnonymizerEngine()
    result = engine.anonymize(text, analyzer_results, anonymizer_config)

    result_by_type = {item.entity_type: item for item in result.items}
    assert result_by_type["NAME"].score == 0.8
    assert result_by_type["PHONE_NUMBER"].score == 0.95


@pytest.mark.parametrize(
    "operator_name,operator_params",
    [
        ("replace", {}),
        ("redact", {}),
        ("mask", {"masking_char": "*", "chars_to_mask": 4, "from_end": False}),
        ("hash", {}),
    ],
)
def test_given_different_operators_then_score_is_always_propagated(
    operator_name, operator_params
):
    """Score is propagated regardless of which operator is applied."""
    text = "My name is Jane Doe"
    anonymizer_config = {"NAME": OperatorConfig(operator_name, operator_params)}
    analyzer_results = [
        RecognizerResult(start=11, end=19, score=0.75, entity_type="NAME"),
    ]

    engine = AnonymizerEngine()
    result = engine.anonymize(text, analyzer_results, anonymizer_config)

    assert result.items[0].score == 0.75


def test_given_conflicting_entities_then_winning_entity_score_is_preserved():
    """When conflict resolution drops an entity, the surviving entity keeps its own score."""
    text = "hello world, my name is Jane Doe"
    anonymizer_config = {}
    analyzer_results = [
        RecognizerResult(start=24, end=32, score=0.6, entity_type="FULL_NAME"),
        RecognizerResult(start=24, end=28, score=0.9, entity_type="FIRST_NAME"),  # loses
        RecognizerResult(start=24, end=30, score=0.8, entity_type="NAME"),        # loses
    ]

    engine = AnonymizerEngine()
    result = engine.anonymize(text, analyzer_results, anonymizer_config)

    assert len(result.items) == 1
    assert result.items[0].entity_type == "FULL_NAME"
    assert result.items[0].score == 0.6  # its own score, not the score of dropped entities


def test_given_score_in_result_then_it_is_present_in_json_output():
    """Score is included in to_json() serialized output."""
    text = "My name is Jane Doe"
    anonymizer_config = {}
    analyzer_results = [
        RecognizerResult(start=11, end=19, score=0.85, entity_type="NAME"),
    ]

    engine = AnonymizerEngine()
    result = engine.anonymize(text, analyzer_results, anonymizer_config)

    output = json.loads(result.to_json())
    assert output["items"][0]["score"] == pytest.approx(0.85)


def run_engine_and_validate(
    text: str, anonymizers_config, analyzer_results, expected_result
):
    engine = AnonymizerEngine()
    try:
        actual_anonymize_result = engine.anonymize(
            text, analyzer_results, anonymizers_config
        )
    except Exception as e:
        actual_anonymize_result = str(e)
    assert actual_anonymize_result.to_json() == expected_result


def test_given_anonymize_called_with_error_scenarios_then_expected_errors_returned():
    text = "hello world, my name is Jane Doe. My number is: 03-4453334"
    anonymizers = {
        "PHONE_NUMBER": OperatorConfig(
            "mask",
            {"masking_char": "non_character", "chars_to_mask": 6, "from_end": True},
        )
    }
    analyzer_results = [RecognizerResult("PHONE_NUMBER", 48, 57, 0.95)]

    engine = AnonymizerEngine()

    try:
        actual_anonymize_result = engine.anonymize(text, analyzer_results, anonymizers)
    except Exception as e:
        actual_anonymize_result = str(e)

    assert actual_anonymize_result == "Invalid input, masking_char must be a character"


def test_given_anonymize_with_encrypt_then_text_returned_with_encrypted_content():
    unencrypted_text = "My name is "
    expected_encrypted_text = "Chloë"
    text = unencrypted_text + expected_encrypted_text
    start_index = 11
    end_index = 16
    key = "WmZq4t7w!z%C&F)J"
    analyzer_results = [RecognizerResult("PERSON", start_index, end_index, 0.8)]
    anonymizers_config = {"PERSON": OperatorConfig("encrypt", {"key": key})}

    actual_anonymize_result = (
        AnonymizerEngine().anonymize(text, analyzer_results, anonymizers_config).text
    )

    assert actual_anonymize_result[:start_index] == unencrypted_text
    actual_encrypted_text = actual_anonymize_result[start_index:]
    assert actual_encrypted_text != expected_encrypted_text
    actual_decrypted_text = AESCipher.decrypt(key.encode(), actual_encrypted_text)
    assert actual_decrypted_text == expected_encrypted_text


def test_empty_text_returns_correct_results():
    text = ""
    analyzer_results = []

    actual_anonymize_result = AnonymizerEngine().anonymize(text, analyzer_results)

    assert actual_anonymize_result.text == text


def test_add_anonymizer_returns_updated_list(mock_anonymizer_cls):
    engine = AnonymizerEngine()
    anon_list_len = len(engine.get_anonymizers())
    engine.add_anonymizer(mock_anonymizer_cls)
    anon_list = engine.get_anonymizers()
    assert len(anon_list) == anon_list_len + 1
    assert mock_anonymizer_cls().operator_name() in anon_list


def test_anonymizer_engine_uses_custom_operator():
    engine = AnonymizerEngine()
    engine.add_anonymizer(create_reverser_operator(OperatorType.Anonymize))
    text = "hello"
    analyzer_results = [RecognizerResult("WORD", 0, 5, 1.0)]

    actual_anonymize_result = engine.anonymize(
        text, analyzer_results, {"WORD": OperatorConfig("Reverser")}
    )
    assert actual_anonymize_result.text == "hello"[::-1]


def test_remove_anonymizer_removes_anonymizer():
    engine = AnonymizerEngine()
    num_of_anonymizers = len(engine.get_anonymizers())
    engine.remove_anonymizer(Redact)
    anonymizers = engine.get_anonymizers()
    assert len(anonymizers) == num_of_anonymizers - 1


def test_operator_metadata_returns_updated_results(three_person_analyzer_results):
    counter_anonymizer = create_instance_counter_anonymizer()
    engine = AnonymizerEngine()
    engine.add_anonymizer(counter_anonymizer)
    text, analyzer_results = three_person_analyzer_results

    entity_mapping = dict()

    actual_anonymize_result = engine.anonymize(
        text,
        analyzer_results,
        {
            "DEFAULT": OperatorConfig(
                "entity_counter", {"entity_mapping": entity_mapping}

            )
        },
    )

    pattern = r'<PERSON_\d+>'
    assert len(re.findall(pattern, actual_anonymize_result.text)) == 3
    for results in actual_anonymize_result.items:
        assert results.operator == "entity_counter"
        assert results.entity_type == "PERSON"
        assert re.findall(pattern, results.text)
