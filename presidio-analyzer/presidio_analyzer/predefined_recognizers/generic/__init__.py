"""Generic recognizers package."""

from .credit_card_recognizer import CreditCardRecognizer
from .crypto_recognizer import CryptoRecognizer
from .email_recognizer import EmailRecognizer
from .iban_recognizer import IbanRecognizer
from .imei_recognizer import ImeiRecognizer
from .ip_recognizer import IpRecognizer
from .mac_recognizer import MacAddressRecognizer
from .phone_recognizer import PhoneRecognizer
from .url_recognizer import UrlRecognizer
from .uuid_recognizer import UuidRecognizer
from .vin_recognizer import VinRecognizer

__all__ = [
    "CreditCardRecognizer",
    "CryptoRecognizer",
    "EmailRecognizer",
    "IbanRecognizer",
    "ImeiRecognizer",
    "IpRecognizer",
    "PhoneRecognizer",
    "UrlRecognizer",
    "MacAddressRecognizer",
    "UuidRecognizer",
    "VinRecognizer",
]
