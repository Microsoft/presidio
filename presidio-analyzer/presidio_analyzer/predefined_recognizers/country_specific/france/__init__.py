"""France-specific recognizers package."""

from .fr_siren_recognizer import FrSirenRecognizer
from .fr_siret_recognizer import FrSiretRecognizer

__all__ = [
    "FrSirenRecognizer",
    "FrSiretRecognizer",
]
