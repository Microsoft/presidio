import base64
import os

from cryptography.hazmat.primitives import hashes, hmac, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


class AESCipher:
    """Advanced Encryption Standard (aka Rijndael) en/decryption in CBC mode."""

    @staticmethod
    def encrypt(key: bytes, text: str, deterministic: bool = False) -> str:
        """
        Encrypts a text using AES cypher in CBC mode.

        Uses padding and, by default, a random IV.
        :param key: AES encryption key in bytes.
        :param text: The text for encryption.
        :param deterministic: Whether to derive the IV from the key and the text
                              instead of drawing it at random, so that the same
                              text always encrypts to the same value. This is an
                              opt-in trade-off: it enables referential integrity
                              across a dataset, but it reveals which values
                              are equal and how often each occurs, since
                              identical values become identical ciphertexts.
        :returns: The encrypted text.
        """
        encoded_text = text.encode("utf-8")
        padder = padding.PKCS7(algorithms.AES.block_size).padder()
        padded_text = padder.update(encoded_text) + padder.finalize()
        if deterministic:
            iv = AESCipher._derive_iv(key, encoded_text)
        else:
            iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        encryptor = cipher.encryptor()
        encrypted_text = base64.urlsafe_b64encode(
            iv + encryptor.update(padded_text) + encryptor.finalize()
        )
        return encrypted_text.decode()

    @staticmethod
    def decrypt(key: bytes, text: str) -> str:
        """
        Decrypts a previously AES-CBC encrypted text.

        :param key: AES encryption key in bytes.
        :param text: The text for decryption.
        :returns: The decrypted text.
        """
        decoded_text = base64.urlsafe_b64decode(text)
        iv = decoded_text[:16]
        ct = decoded_text[16:]
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        unpadder = padding.PKCS7(128).unpadder()
        decrypted_text = decryptor.update(ct) + decryptor.finalize()
        return (unpadder.update(decrypted_text) + unpadder.finalize()).decode("utf-8")

    _IV_DERIVATION_LABEL = b"presidio-anonymizer/deterministic-iv"

    @staticmethod
    def _derive_iv(key: bytes, encoded_text: bytes) -> bytes:
        """
        Derive a synthetic IV (SIV) from the encryption key and the text.

        The IV is keyed rather than a bare hash of the plaintext: an unkeyed
        digest would be reproducible by anyone, so an attacker could confirm a
        guessed value straight from the IV, without holding the key.

        The key that keys it is a separate one, derived from the encryption key
        under a fixed label, so that the key driving AES is not also used to
        produce a value published in the clear. RFC 5297 separates the two keys
        of SIV mode for the same reason.

        What a deterministic ciphertext still reveals is which values are equal,
        and so how often each value occurs, on top of the approximate length
        CBC padding reveals either way.
        :param key: AES encryption key in bytes.
        :param encoded_text: The UTF-8 encoded text for encryption.
        :returns: A 16 byte IV, identical for the same key and text.
        """
        iv_key = AESCipher._hmac_sha256(key, AESCipher._IV_DERIVATION_LABEL)
        return AESCipher._hmac_sha256(iv_key, encoded_text)[:16]

    @staticmethod
    def _hmac_sha256(key: bytes, message: bytes) -> bytes:
        mac = hmac.HMAC(key, hashes.SHA256())
        mac.update(message)
        return mac.finalize()

    @staticmethod
    def is_valid_key_size(key: bytes) -> bool:
        """
        Validate key size for AES.

        :param key: AES encryption key in bytes.
        :returns: True if the key is of valid size, False otherwise.
        """
        return len(key) * 8 in algorithms.AES.key_sizes
