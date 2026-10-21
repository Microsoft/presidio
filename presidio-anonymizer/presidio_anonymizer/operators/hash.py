"""Hashes the PII text entity."""

import os
from hashlib import sha256, sha512
from typing import Dict, Optional, Union

from presidio_anonymizer.entities import InvalidParamError
from presidio_anonymizer.operators import Operator, OperatorType
from presidio_anonymizer.services.validators import validate_parameter_in_range

MIN_SALT_LENGTH = 16


class Hash(Operator):
    """Hash given text with sha256/sha512 algorithm."""

    HASH_TYPE = "hash_type"
    SALT = "salt"
    SHA256 = "sha256"
    SHA512 = "sha512"

    def operate(self, text: str = None, params: Dict = None) -> str:
        """
        Hash given value using sha256 or sha512 with salt.

        :param text: The text to hash
        :param params: Dictionary containing:
            - hash_type: The hash algorithm to use (sha256 or sha512)
            - salt: Optional user-provided salt for reproducible hashing.
                    If not provided, a random salt is generated per entity.
                    Must be a string or bytes of at least 16 bytes (128 bits)
                    if provided.
        :return: hashed original text with salt
        """
        hash_type = self._get_hash_type_or_default(params)

        # Use user-provided salt if available, otherwise generate random salt
        salt = self._validate_salt(params.get(self.SALT))
        if salt is None:
            # Generate random salt for this entity (prevents brute-force attacks)
            salt = os.urandom(32)

        # Concatenate text and salt before hashing
        salted_text = text.encode() + salt

        hash_switcher = {
            self.SHA256: lambda s: sha256(s),
            self.SHA512: lambda s: sha512(s),
        }
        return hash_switcher.get(hash_type)(salted_text).hexdigest()

    def validate(self, params: Dict = None) -> None:
        """Validate the hash type and the optional salt."""
        validate_parameter_in_range(
            [self.SHA256, self.SHA512],
            self._get_hash_type_or_default(params),
            self.HASH_TYPE,
            str,
        )
        self._validate_salt(params.get(self.SALT))

    @staticmethod
    def _validate_salt(salt: Optional[Union[str, bytes, bytearray]]) -> Optional[bytes]:
        """
        Validate the user-provided salt and normalize it to bytes.

        :param salt: The salt as provided by the user, or None if not provided.
        :return: The salt as bytes, or None when no salt was provided, which
                means a random salt should be generated per entity.
        """
        if salt is None:
            return None
        if not isinstance(salt, (str, bytes, bytearray)):
            raise InvalidParamError(
                f"Invalid salt type '{type(salt).__name__}'. "
                "Salt must be a string or bytes of at least "
                f"{MIN_SALT_LENGTH} bytes (128 bits), "
                "or omitted to generate a random salt."
            )
        # Ensure salt is bytes
        if isinstance(salt, str):
            salt = salt.encode()
        # Validate salt is not empty and meets minimum length (16 bytes / 128 bits)
        if len(salt) == 0:
            raise InvalidParamError(
                "Salt parameter cannot be empty. Either omit the salt parameter "
                "to auto-generate a random salt, or provide a salt of at least "
                f"{MIN_SALT_LENGTH} bytes (128 bits)."
            )
        if len(salt) < MIN_SALT_LENGTH:
            raise InvalidParamError(
                f"Salt must be at least {MIN_SALT_LENGTH} bytes (128 bits). "
                f"Provided salt is {len(salt)} bytes."
            )
        return salt

    def operator_name(self) -> str:
        """Return operator name."""
        return "hash"

    def _get_hash_type_or_default(self, params: Dict = None):
        return params.get(self.HASH_TYPE, self.SHA256)

    def operator_type(self) -> OperatorType:
        """Return operator type."""
        return OperatorType.Anonymize
