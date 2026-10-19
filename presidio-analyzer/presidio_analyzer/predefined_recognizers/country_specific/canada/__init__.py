"""Canada-specific recognizers package."""

from .ca_bn_recognizer import CaBnRecognizer
from .ca_postal_code_recognizer import CaPostalCodeRecognizer
from .ca_sin_recognizer import CaSinRecognizer

__all__ = [
    "CaBnRecognizer",
    "CaPostalCodeRecognizer",
    "CaSinRecognizer",
]
