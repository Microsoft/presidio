from hashlib import sha256
from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer

# This class includes references to addresses validation algorithms.
# The original implementation of the P2PKH and P2SH address validation
# algorithm can be found at:
# http://rosettacode.org/wiki/Bitcoin/address_validation#Python
# The Bech32/Bech32m address validation algorithm by Pieter Wuille can be found
# at: https://github.com/sipa/bech32/blob/master/ref/python/segwit_addr.py

# Constants for encoding types
BECH32 = 1
BECH32M = 2

CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
BECH32M_CONST = 0x2BC830A3


class CryptoRecognizer(PatternRecognizer):
    """Recognize common crypto account numbers using regex + checksum.

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    PATTERNS = [
        Pattern("Crypto (Medium)", r"(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,59}", 0.5),
    ]

    CONTEXT = ["wallet", "btc", "bitcoin", "crypto"]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "CRYPTO",
        name: Optional[str] = None,
    ):
        patterns = patterns if patterns else self.PATTERNS
        context = context if context else self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name=name,
        )

    def validate_result(self, pattern_text: str) -> bool:
        """Validate the Bitcoin address using checksum.

        :param pattern_text: The cryptocurrency address to validate.
        :return: True if the address is valid according to its respective
        format, False otherwise.
        """
        if pattern_text.startswith("1") or pattern_text.startswith("3"):
            # P2PKH or P2SH address validation
            try:
                bcbytes = self.__decode_base58(str.encode(pattern_text))
                checksum = sha256(sha256(bcbytes[:-4]).digest()).digest()[:4]
                return bcbytes[-4:] == checksum
            except ValueError:
                return False
        elif pattern_text.lower().startswith("bc1"):
            # Bech32 or Bech32m address validation
            return (
                CryptoRecognizer.decode_segwit_address("bc", pattern_text) is not None
            )
        return False

    @staticmethod
    def __decode_base58(bc: bytes) -> bytes:
        digits58 = b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        origlen = len(bc)
        bc = bc.lstrip(digits58[0:1])

        n = 0
        for char in bc:
            n = n * 58 + digits58.index(char)
        return n.to_bytes(origlen - len(bc) + (n.bit_length() + 7) // 8, "big")

    @staticmethod
    def bech32_polymod(values):
        """Compute the Bech32 checksum."""
        generator = [0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3]
        chk = 1
        for value in values:
            top = chk >> 25
            chk = (chk & 0x1FFFFFF) << 5 ^ value
            for i in range(5):
                chk ^= generator[i] if ((top >> i) & 1) else 0
        return chk

    @staticmethod
    def bech32_hrp_expand(hrp):
        """Expand the HRP into values for checksum computation."""
        return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]

    @staticmethod
    def bech32_verify_checksum(hrp, data):
        """Verify a checksum given HRP and converted data characters."""
        const = CryptoRecognizer.bech32_polymod(
            CryptoRecognizer.bech32_hrp_expand(hrp) + data
        )
        if const == 1:
            return BECH32
        if const == BECH32M_CONST:
            return BECH32M
        return None

    @staticmethod
    def bech32_decode(bech):
        """Validate a Bech32/Bech32m string, and determine HRP and data."""
        if (any(ord(x) < 33 or ord(x) > 126 for x in bech)) or (
            bech.lower() != bech and bech.upper() != bech
        ):
            return (None, None, None)
        bech = bech.lower()
        pos = bech.rfind("1")
        if pos < 1 or pos + 7 > len(bech) or len(bech) > 90:
            return (None, None, None)
        if not all(x in CHARSET for x in bech[pos + 1 :]):
            return (None, None, None)
        hrp = bech[:pos]
        data = [CHARSET.find(x) for x in bech[pos + 1 :]]
        spec = CryptoRecognizer.bech32_verify_checksum(hrp, data)
        if spec is None:
            return (None, None, None)
        return (hrp, data[:-6], spec)

    @staticmethod
    def convertbits(data, frombits, tobits):
        """Regroup bits without padding, as required for witness programs."""
        acc = 0
        bits = 0
        ret = []
        maxv = (1 << tobits) - 1
        max_acc = (1 << (frombits + tobits - 1)) - 1
        for value in data:
            acc = ((acc << frombits) | value) & max_acc
            bits += frombits
            while bits >= tobits:
                bits -= tobits
                ret.append((acc >> bits) & maxv)
        if bits >= frombits or ((acc << (tobits - bits)) & maxv):
            return None
        return ret

    @staticmethod
    def decode_segwit_address(hrp, address):
        """Decode a segwit address, enforcing the BIP173 and BIP350 rules."""
        hrpgot, data, spec = CryptoRecognizer.bech32_decode(address)
        if hrpgot != hrp:
            return None
        program = CryptoRecognizer.convertbits(data[1:], 5, 8)
        if program is None or len(program) < 2 or len(program) > 40:
            return None
        version = data[0]
        if version > 16:
            return None
        if version == 0 and len(program) not in (20, 32):
            return None
        if spec != (BECH32 if version == 0 else BECH32M):
            return None
        return version, program

    @staticmethod
    def validate_bech32_address(address):
        """Validate a Bech32 or Bech32m address."""
        hrp, data, spec = CryptoRecognizer.bech32_decode(address)
        if hrp is not None and data is not None:
            return True, spec
        return False, None
