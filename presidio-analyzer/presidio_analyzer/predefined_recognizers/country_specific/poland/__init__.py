"""Poland-specific recognizers."""

from .pl_nip_recognizer import PlNipRecognizer
from .pl_pesel_recognizer import PlPeselRecognizer

__all__ = [
    "PlNipRecognizer",
    "PlPeselRecognizer",
]
