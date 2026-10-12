import pytest
from presidio_analyzer.predefined_recognizers import UuidRecognizer

from tests import assert_result_within_score_range


@pytest.fixture(scope="module")
def recognizer():
    """Return a UuidRecognizer instance for testing."""
    return UuidRecognizer()


@pytest.fixture(scope="module")
def entities():
    """Return the entity list this recognizer supports."""
    return ["UUID"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off
        # Version 4 (random) - most common
        ("Request ID: 550e8400-e29b-41d4-a716-446655440000",
         1, ((12, 48),), ((0.5, 0.5),)),
        ("User UUID: 6fa459ea-ee8a-3ca4-894e-db77e160355e",
         1, ((11, 47),), ((0.5, 0.5),)),

        # Version 1 (time-based)
        ("Trace: f47ac10b-58cc-1372-8567-0e02b2c3d479",
         1, ((7, 43),), ((0.5, 0.5),)),

        # Version 2 (DCE Security, RFC 4122)
        ("DCE UUID: 550e8400-e29b-21d4-a716-446655440000",
         1, ((10, 46),), ((0.5, 0.5),)),

        # Version 3 (MD5 name-based, RFC 4122)
        ("6ba7b810-9dad-31d1-80b4-00c04fd430c8",
         1, ((0, 36),), ((0.5, 0.5),)),

        # Version 5 (SHA-1 name-based)
        ("Object id 74738ff5-5367-5958-9aee-98fffdcd1876 created",
         1, ((10, 46),), ((0.5, 0.5),)),

        # Version 6 (reordered time-based, RFC 9562)
        ("Sortable ID: 1ec9414c-232a-6b00-b3c8-9e6bdeced846",
         1, ((13, 49),), ((0.5, 0.5),)),

        # Version 7 (timestamp-based, RFC 9562)
        ("New record: 018f4f8e-9a3b-7c3d-8e9f-1a2b3c4d5e6f",
         1, ((12, 48),), ((0.5, 0.5),)),

        # Version 8 (vendor/implementation-specific, RFC 9562)
        ("Custom UUID: 550e8400-e29b-81d4-a716-446655440000",
         1, ((13, 49),), ((0.5, 0.5),)),

        # Uppercase
        ("GUID: 550E8400-E29B-41D4-A716-446655440000",
         1, ((6, 42),), ((0.5, 0.5),)),

        # With context keywords
        ("unique identifier: 550e8400-e29b-41d4-a716-446655440000",
         1, ((19, 55),), ((0.5, "max"),)),
        ("The guid is 6fa459ea-ee8a-3ca4-894e-db77e160355e",
         1, ((12, 48),), ((0.5, "max"),)),

        # Multiple UUIDs
        (
            "IDs: 550e8400-e29b-41d4-a716-446655440000 and "
            "f47ac10b-58cc-1372-8567-0e02b2c3d479",
            2,
            ((5, 41), (46, 82)),
            ((0.5, 0.5), (0.5, 0.5)),
        ),

        # Invalid cases - should not match
        ("Not a UUID: 550e8400-e29b-41d4-a716",
         0, (), ()),  # Too short
        ("Invalid: zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz",
         0, (), ()),  # Invalid hex
        ("Nil UUID: 00000000-0000-0000-0000-000000000000",
         0, (), ()),  # Nil UUID filtered
        ("Bad version: 550e8400-e29b-01d4-a716-446655440000",
         0, (), ()),  # Invalid version nibble (0)
        ("Bad version: 550e8400-e29b-91d4-a716-446655440000",
         0, (), ()),  # Invalid version nibble (9)
        ("Bad variant: 550e8400-e29b-41d4-1716-446655440000",
         0, (), ()),  # Invalid variant nibble
        # fmt: on
    ],
)
def test_when_uuids_then_succeed(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
    max_score,
):
    """Verify UuidRecognizer detects valid UUIDs and rejects invalid ones."""
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    assert len(expected_positions) == expected_len
    assert len(expected_score_ranges) == expected_len
    for res, (st_pos, fn_pos), (st_score, fn_score) in zip(
        results, expected_positions, expected_score_ranges
    ):
        if fn_score == "max":
            fn_score = max_score
        assert_result_within_score_range(
            res, entities[0], st_pos, fn_pos, st_score, fn_score
        )
