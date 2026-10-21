import pytest

from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import (
    InvalidParamError,
    OperatorConfig,
    RecognizerResult,
)
from presidio_anonymizer.services.validators import validate_parameter, validate_type


def _get_default_mask_parameters():
    return {"masking_char": "*", "chars_to_mask": 4, "from_end": False}


@pytest.mark.parametrize("validator", [validate_type, validate_parameter])
@pytest.mark.parametrize(
    "value,expected_type,expected_message",
    [
        (0, str, "Expecting 'string', but got 'number'."),
        (False, str, "Expecting 'string', but got 'boolean'."),
        ("", int, "Expecting 'number', but got 'string'."),
        ([], int, "Expecting 'number', but got 'array'."),
        ({}, str, None),
    ],
)
def test_given_falsy_parameter_with_wrong_type_then_ipe_raised(
    validator, value, expected_type, expected_message
):
    with pytest.raises(InvalidParamError) as error:
        validator(value, "name", expected_type)

    expected = (
        f"Invalid parameter value for name. {expected_message}"
        if expected_message is not None
        else "Invalid parameter value for 'name'."
    )
    assert str(error.value) == expected


@pytest.mark.parametrize("validator", [validate_type, validate_parameter])
@pytest.mark.parametrize(
    "value,expected_type", [(0, int), (False, bool), ("", str), ([], list), ({}, dict)]
)
def test_given_falsy_parameter_with_correct_type_then_we_pass(
    validator, value, expected_type
):
    validator(value, "name", expected_type)


@pytest.mark.parametrize(
    "parameter,value",
    [("masking_char", 0), ("chars_to_mask", ""), ("from_end", "")],
)
def test_when_mask_parameter_has_falsy_wrong_type_then_engine_raises_ipe(
    parameter, value
):
    params = _get_default_mask_parameters()
    params[parameter] = value

    with pytest.raises(
        InvalidParamError, match=f"Invalid parameter value for {parameter}"
    ):
        AnonymizerEngine().anonymize(
            text="合成测试",
            analyzer_results=[RecognizerResult("PERSON", 0, 4, 1.0)],
            operators={"PERSON": OperatorConfig("mask", params)},
        )


@pytest.mark.parametrize("chars_to_mask,expected", [(0, "合成测试"), (4, "****")])
def test_when_valid_falsy_mask_parameters_then_chinese_output_is_preserved(
    chars_to_mask, expected
):
    params = _get_default_mask_parameters()
    params["chars_to_mask"] = chars_to_mask

    result = AnonymizerEngine().anonymize(
        text="合成测试",
        analyzer_results=[RecognizerResult("PERSON", 0, 4, 1.0)],
        operators={"PERSON": OperatorConfig("mask", params)},
    )

    assert result.text == expected
