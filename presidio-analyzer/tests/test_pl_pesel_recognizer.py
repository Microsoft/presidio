from pathlib import Path

import presidio_analyzer
import pytest
import yaml
from presidio_analyzer.predefined_recognizers import PlPeselRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

from tests import assert_result


@pytest.fixture(scope="module")
def recognizer():
    return PlPeselRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["PL_PESEL"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions",
    [
        # fmt: off
        # Valid PESEL numbers — these pass both the regex (encoded date of birth)
        # and the check-digit algorithm: check = (10 - weighted_sum % 10) % 10.
        # See https://en.wikipedia.org/wiki/PESEL#Check_digit
        ("44051401458", 1, ((0, 11),),),
        ("My pesel is 44051401458.", 1, ((12, 23),)),
        ("02070803628", 1, ((0, 11),),),
        ("11111111116", 1, ((0, 11),),),
        # Invalid: check digit does not match the weighted sum
        ("44051401459", 0, ()),
        ("85040812345", 0, ()),
        # Invalid: regex rejects illegal month/day encodings
        ("1111321111", 0, ()),
        ("11110021111", 0, ()),
        # Invalid: hyphen-separated groups are not a PESEL format
        ("11-11-11-11114", 0, ()),
        # Invalid: an 11-digit window inside a longer run of digits is not a PESEL
        ("44051401359123", 0, ()),
        ("PESEL: 44051401359123", 0, ()),
        ("440514014588", 0, ()),
        ("1440514014582", 0, ()),
        # Valid: PESEL at the start, after a label, at the end, next to a letter
        ("44051401458 is my PESEL", 1, ((0, 11),)),
        ("PESEL: 44051401458", 1, ((7, 18),)),
        ("PESEL 44051401458", 1, ((6, 17),)),
        ("PESEL44051401458", 1, ((5, 16),)),
        ("44051401458 and 02070803628", 2, ((0, 11), (16, 27))),
        # Valid: only a digit extends the number, so a PESEL next to a letter
        # on either side still matches, with the letter outside the span
        ("X44051401458", 1, ((1, 12),)),
        ("44051401458X", 1, ((0, 11),)),
        # fmt: on
    ],
)
def test_when_all_pl_pesels_then_succeed(
    text, expected_len, expected_positions, recognizer, entities, max_score
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos) in zip(results, expected_positions):
        assert_result(res, entities[0], st_pos, fn_pos, max_score)


@pytest.mark.parametrize(
    "pesel, expected",
    [
        # Real-world and algorithmically-generated valid PESEL numbers
        ("44051401458", True),
        ("02070803628", True),
        ("11111111116", True),
        # Wrong check digit
        ("44051401459", False),
        ("85040812345", False),
        # Wrong length
        ("4405140145", False),
        ("440514014588", False),
        # Non-digit characters
        ("4405140145A", False),
        ("44-051401458", False),
    ],
)
def test_validate_result_checksum(pesel, expected, recognizer):
    assert recognizer.validate_result(pesel) is expected


def test_when_enabled_from_yaml_then_only_standalone_pesel_is_detected(
    entities, max_score
):
    """Boundary fix must hold through the path users enable the recognizer from.

    The recognizer is reached by flipping its YAML entry on, so the test loads
    the shipped entry through ``RecognizerRegistryProvider`` and checks that the
    standalone PESEL matches while the 14-digit run next to it does not.
    """
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entry = next(r for r in recognizers if r.get("name") == "PlPeselRecognizer")

    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["pl"],
            "recognizers": [dict(entry, enabled=True)],
        }
    ).create_recognizer_registry()

    (loaded,) = registry.recognizers
    results = loaded.analyze("PESEL: 44051401458 44051401359123", entities)
    assert len(results) == 1
    assert_result(results[0], entities[0], 7, 18, max_score)
