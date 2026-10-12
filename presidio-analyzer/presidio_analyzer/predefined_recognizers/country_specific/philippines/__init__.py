"""Philippines-specific recognizers."""

from .ph_passport_recognizer import PhPassportRecognizer
from .ph_tin_recognizer import PhTinRecognizer
from .ph_umid_recognizer import PhUmidRecognizer

__all__ = [
    "PhPassportRecognizer",
    "PhTinRecognizer",
    "PhTinRecognizer",
    "PhUmidRecognizer",
]
