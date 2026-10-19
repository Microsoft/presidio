"""Turkey-specific recognizers."""

from .tr_license_plate_recognizer import TrLicensePlateRecognizer
from .tr_national_id_recognizer import TrNationalIdRecognizer
from .tr_tax_id_recognizer import TrTaxIdRecognizer

__all__ = [
    "TrLicensePlateRecognizer",
    "TrNationalIdRecognizer",
    "TrTaxIdRecognizer",
]
