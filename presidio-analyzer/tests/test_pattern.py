import pytest

from presidio_analyzer import Pattern


@pytest.fixture(scope="module")
def my_pattern():
    return Pattern(name="my pattern", score=0.9, regex="[re]")


@pytest.fixture(scope="module")
def my_pattern_dict():
    return {"name": "my pattern", "regex": "[re]", "score": 0.9}


def test_when_use_to_dict_return_dict(my_pattern, my_pattern_dict):
    expected = my_pattern_dict
    actual = my_pattern.to_dict()

    assert expected == actual


def test_when_use_from_dict_return_pattern(my_pattern, my_pattern_dict):
    expected = my_pattern
    actual = Pattern.from_dict(my_pattern_dict)

    assert expected.name == actual.name
    assert expected.score == actual.score
    assert expected.regex == actual.regex


def test_pattern_validation_success():
    """Test that Pattern class validates correctly with valid data."""
    pattern_data = {
        "name": "US ZIP Code",
        "regex": r"\b\d{5}(?:-\d{4})?\b",
        "score": 0.85
    }

    pattern = Pattern.from_dict(pattern_data)
    assert pattern.name == "US ZIP Code"
    assert pattern.score == 0.85
    assert pattern.regex == r"\b\d{5}(?:-\d{4})?\b"

def test_pattern_validation_invalid_regex():
    """Test that Pattern class rejects invalid regex patterns."""
    pattern_data = {
        "name": "Invalid Pattern",
        "regex": "[unclosed_bracket",  # Invalid regex
        "score": 0.5
    }

    with pytest.raises(ValueError) as exc_info:
        Pattern.from_dict(pattern_data)


def test_pattern_validation_invalid_score_range():
    """Test that Pattern class rejects scores outside [0,1] range."""
    pattern_data = {
        "name": "Invalid Score",
        "regex": r"\btest\b",
        "score": 1.5  # Invalid: > 1.0
    }

    with pytest.raises(ValueError) as exc_info:
        Pattern.from_dict(pattern_data)


def test_backward_compatibility_pattern_to_dict():
    """Test that Pattern maintains backward compatibility with to_dict method."""
    pattern = Pattern(name="test", regex=r"\btest\b", score=0.5)
    pattern_dict = pattern.to_dict()

    expected = {"name": "test", "regex": r"\btest\b", "score": 0.5}
    assert pattern_dict == expected


def test_when_capture_group_not_set_then_it_defaults_to_none_and_is_not_serialized():
    pattern = Pattern(name="test", regex=r"id: (\d+)", score=0.5)

    assert pattern.capture_group is None
    assert "capture_group" not in pattern.to_dict()


@pytest.mark.parametrize(
    "regex, capture_group",
    [
        (r"id: (\d+)", 0),
        (r"id: (\d+)", 1),
        (r"id: (?P<value>\d+)", "value"),
    ],
)
def test_when_capture_group_set_then_round_trips_through_dict(regex, capture_group):
    pattern = Pattern(
        name="test", regex=regex, score=0.5, capture_group=capture_group
    )

    pattern_dict = pattern.to_dict()
    restored = Pattern.from_dict(pattern_dict)

    assert pattern_dict == {
        "name": "test",
        "score": 0.5,
        "regex": regex,
        "capture_group": capture_group,
    }
    assert restored.capture_group == capture_group


@pytest.mark.parametrize(
    "regex, capture_group, expected_message",
    [
        (
            r"id: (\d+)",
            2,
            r"capture_group 2 is out of range: regex defines 1 capture group\(s\)",
        ),
        (
            r"id: \d+",
            1,
            r"capture_group 1 is out of range: regex defines 0 capture group\(s\)",
        ),
        (
            r"id: (?P<value>\d+)",
            "number",
            r"capture_group 'number' is not a named group in the regex. "
            r"Named groups: \['value'\]",
        ),
        (
            r"id: (\d+)",
            "value",
            r"capture_group 'value' is not a named group in the regex. "
            r"Named groups: \[\]",
        ),
        (
            r"id: (\d+)",
            -1,
            r"capture_group must be a non-negative integer, got -1",
        ),
        (
            r"id: (\d+)",
            True,
            r"capture_group must be an int or a str, got bool",
        ),
        (
            r"id: (\d+)",
            1.0,
            r"capture_group must be an int or a str, got float",
        ),
    ],
)
def test_when_capture_group_invalid_then_raises_value_error(
    regex, capture_group, expected_message
):
    with pytest.raises(ValueError, match=expected_message):
        Pattern(name="test", regex=regex, score=0.5, capture_group=capture_group)
