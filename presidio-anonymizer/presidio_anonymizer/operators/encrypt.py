from typing import Dict

from presidio_anonymizer.entities import InvalidParamError
from presidio_anonymizer.operators import Operator, OperatorType
from presidio_anonymizer.operators.aes_cipher import AESCipher
from presidio_anonymizer.services.validators import (
    validate_parameter,
    validate_type_strict,
)


class Encrypt(Operator):
    """Anonymizes text to an encrypted form, or it to be restored using decrypted."""

    KEY = "key"
    DETERMINISTIC = "deterministic"

    def operate(self, text: str = None, params: Dict = None) -> str:
        """
        Anonymize the text with an encrypted text.

        :param text: The text for encryption.
        :param params:
            * *key* The key supplied by the user for the encryption (bytes or str).
            * *deterministic* Whether the same text should always encrypt to the
                              same value, defaults to False.
        :return: The encrypted text
        """
        key = params.get(self.KEY)
        if isinstance(key, str):
            key = key.encode("utf8")
        deterministic = params.get(self.DETERMINISTIC, False)
        encrypted_text = AESCipher.encrypt(key, text, deterministic=deterministic)
        return encrypted_text

    def validate(self, params: Dict = None) -> None:
        """
        Validate Encrypt parameters.

        :param params:
            * *key* The key supplied by the user for the encryption.
                    Should be a string of 128, 192 or 256 bits length.
            * *deterministic* Optional boolean. When True, the same text always
                              encrypts to the same value, which keeps references
                              across a dataset intact but reveals which values
                              are equal to one another.
        :raises InvalidParamException: in case on an invalid parameter.
        """
        validate_type_strict(
            params.get(self.DETERMINISTIC), self.DETERMINISTIC, bool
        )
        key = params.get(self.KEY)
        if isinstance(key, str):
            validate_parameter(key, self.KEY, str)
            if not AESCipher.is_valid_key_size(key.encode("utf8")):
                raise InvalidParamError(
                    f"Invalid input, {self.KEY} must be of length 128, 192 or 256 bits"
                )
        else:
            validate_parameter(key, self.KEY, bytes)
            if not AESCipher.is_valid_key_size(key):
                raise InvalidParamError(
                    f"Invalid input, {self.KEY} must be of length 128, 192 or 256 bits"
                )

    def operator_name(self) -> str:
        """Return operator name."""
        return "encrypt"

    def operator_type(self) -> OperatorType:
        """Return operator type."""
        return OperatorType.Anonymize
