"""Anomnymizers validations utility methods."""

from presidio_anonymizer.entities import InvalidParamError


def validate_parameter_in_range(
    values_range, parameter_value, parameter_name: str, parameter_type: type
) -> None:
    """Validate an anonymizer parameter.

    validates the existence of an anonymizer parameter and that it is an
    instance of the parameter_type and that it is within the range of provided values.
    Otherwise, raise the appropriate InvalidParamException with the
    parameter_name as content.
    """
    validate_parameter(parameter_value, parameter_name, object)
    if parameter_value not in values_range:
        raise InvalidParamError(
            f"Parameter {parameter_name} value {parameter_value} is not in "
            f"range of values {values_range}"
        )


def validate_parameter_not_empty(
    parameter_value, entity: str, parameter_name: str
) -> None:
    """Validate parameter exists and not only empty."""
    if not parameter_value:
        raise InvalidParamError(
            f"Invalid input, {entity} must contain {parameter_name}"
        )


def validate_parameter_exists(
    parameter_value, entity: str, parameter_name: str
) -> None:
    """Validate parameter is not empty."""
    if parameter_value is None:
        raise InvalidParamError(
            f"Invalid input, {entity} must contain {parameter_name}"
        )


def validate_parameter(
    parameter_value, parameter_name: str, parameter_type: type
) -> None:
    """Validate an anonymizer parameter.

    Both validate the existence of an anonymizer parameter and that it is an
    instance of the parameter_type. Otherwise, raise the appropriate
    InvalidParamException with the parameter_name as content.
    """
    if parameter_value is None:
        raise InvalidParamError(f"Expected parameter {parameter_name}")
    validate_type(parameter_value, parameter_name, parameter_type)


def validate_type(parameter_value, parameter_name, parameter_type):
    """
    Validate an anonymizer parameter.

    Validate it exists and if so, that it is the instance of the parameter_type.
    Otherwise, raise the appropriate InvalidParamException with the parameter_name
    as content.
    """
    if parameter_value and not isinstance(parameter_value, parameter_type):
        message = _get_bad_typed_parameter_error_message(
            parameter_name,
            expected_type=parameter_type,
            actual_type=type(parameter_value),
        )
        raise InvalidParamError(message)


def validate_type_strict(parameter_value, parameter_name, parameter_type) -> None:
    """
    Validate the type of a parameter whose falsy values are still meaningful.

    :func:`validate_type` skips the check when the value is falsy, which is
    what optional string and numeric parameters want. A boolean parameter
    cannot use it: ``0``, ``""`` and ``[]`` would pass and then be read as
    ``False``, so a caller who wrote ``"deterministic": 0`` in JSON would
    silently get the opposite of a validation error. ``None`` still means
    "not supplied" and passes.
    """
    if parameter_value is not None and not isinstance(parameter_value, parameter_type):
        message = _get_bad_typed_parameter_error_message(
            parameter_name,
            expected_type=parameter_type,
            actual_type=type(parameter_value),
        )
        raise InvalidParamError(message)


def _get_bad_typed_parameter_error_message(parameter_name, expected_type, actual_type):
    type_to_json_type = {
        str: "string",
        bool: "boolean",
        int: "number",
        list: "array",
        object: "object",
    }
    expected_type_display_name = type_to_json_type.get(expected_type)
    actual_type_display_name = type_to_json_type.get(actual_type)
    if expected_type_display_name and actual_type_display_name:
        return (
            f"Invalid parameter value for {parameter_name}. "
            f"Expecting '{expected_type_display_name}', "
            f"but got '{actual_type_display_name}'."
        )
    else:
        return f"Invalid parameter value for '{parameter_name}'."
