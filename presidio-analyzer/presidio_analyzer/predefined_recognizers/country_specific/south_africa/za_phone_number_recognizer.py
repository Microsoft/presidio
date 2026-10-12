from typing import List, Literal, Optional

import phonenumbers
from phonenumbers import PhoneNumberType

from presidio_analyzer import EntityRecognizer
from presidio_analyzer.nlp_engine import NlpArtifacts
from presidio_analyzer.predefined_recognizers.generic.phone_recognizer import (
    PhoneRecognizer,
)

LineClassification = Literal["mobile", "telephone"]


class ZaPhoneNumberRecognizer(PhoneRecognizer):
    """
    Base recognizer for South African phone numbers using python-phonenumbers.

    Splits detection into mobile and telephone line types. Subclasses set
    ``target_classification`` to return only one category.

    Reference:
    https://en.wikipedia.org/wiki/Telephone_numbers_in_South_Africa

    :param supported_entity: The entity this recognizer can detect
    :param target_classification: ``mobile`` or ``telephone`` filter to apply
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param leniency: Phone number matcher strictness (0–3)
    :param name: Optional recognizer instance name
    """

    COUNTRY_CODE = "za"
    REGION = "ZA"

    MOBILE_TYPES = frozenset(
        {
            PhoneNumberType.MOBILE,
            PhoneNumberType.FIXED_LINE_OR_MOBILE,
        }
    )
    TELEPHONE_TYPES = frozenset(
        {
            PhoneNumberType.FIXED_LINE,
            PhoneNumberType.TOLL_FREE,
            PhoneNumberType.PREMIUM_RATE,
            PhoneNumberType.VOIP,
            PhoneNumberType.SHARED_COST,
            PhoneNumberType.PERSONAL_NUMBER,
            PhoneNumberType.UAN,
            PhoneNumberType.PAGER,
        }
    )

    CONTEXT = PhoneRecognizer.CONTEXT + [
        "cellular",
        "handset",
        "contact number",
        "landline",
        "tel",
        "home number",
        "work number",
        "office number",
        "sms",
        "whatsapp",
    ]

    def __init__(
        self,
        supported_entity: str,
        target_classification: LineClassification,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        leniency: Optional[int] = 1,
        name: Optional[str] = None,
    ):
        self.target_classification = target_classification
        context = self.CONTEXT if context is None else context
        super().__init__(
            context=context,
            supported_language=supported_language,
            supported_entity=supported_entity,
            supported_regions=(self.REGION,),
            leniency=leniency,
            name=name,
        )

    def analyze(  # noqa: D102
        self, text: str, entities: List[str], nlp_artifacts: NlpArtifacts = None
    ):
        results = []
        for match in phonenumbers.PhoneNumberMatcher(
            text, self.REGION, leniency=self.leniency
        ):
            parsed_number = match.number

            if phonenumbers.region_code_for_number(parsed_number) != self.REGION:
                continue

            classification = self._classify(parsed_number)
            if classification != self.target_classification:
                continue

            results.append(
                self._get_recognizer_result(match, text, self.REGION, nlp_artifacts)
            )

        return EntityRecognizer.remove_duplicates(results)

    def _classify(self, parsed_number: phonenumbers.PhoneNumber) -> Optional[str]:
        number_type = phonenumbers.number_type(parsed_number)
        if number_type in self.MOBILE_TYPES:
            return "mobile"
        if number_type in self.TELEPHONE_TYPES:
            return "telephone"
        if number_type != PhoneNumberType.UNKNOWN:
            return None
        return self._classify_by_nsn_prefix(str(parsed_number.national_number))

    @staticmethod
    def _classify_by_nsn_prefix(nsn: str) -> Optional[LineClassification]:
        if not nsn:
            return None
        first_digit = nsn[0]
        if first_digit in "67":
            return "mobile"
        if nsn.startswith("80") or nsn.startswith(("86", "87")):
            return "telephone"
        if first_digit == "8":
            return "mobile"
        if first_digit in "123459":
            return "telephone"
        return None


class ZaMobileNumberRecognizer(ZaPhoneNumberRecognizer):
    """
    Recognize South African mobile (cellular) numbers.

    Covers national, international, and common formatted variants for
    ICASA cellular ranges (primarily ``06x``, ``07x``, and cellular ``08x``).

    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param leniency: Phone number matcher strictness (0–3)
    :param name: Optional recognizer instance name
    """

    def __init__(
        self,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "ZA_MOBILE_NUMBER",
        leniency: Optional[int] = 1,
        name: Optional[str] = None,
    ):
        super().__init__(
            supported_entity=supported_entity,
            target_classification="mobile",
            context=context,
            supported_language=supported_language,
            leniency=leniency,
            name=name,
        )


class ZaTelephoneNumberRecognizer(ZaPhoneNumberRecognizer):
    """
    Recognize South African telephone numbers.

    Covers geographic landlines (``01x``–``05x``) and non-mobile service
    lines such as toll-free (``080``), sharecall (``086``), and VoIP (``087``).

    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param leniency: Phone number matcher strictness (0–3)
    :param name: Optional recognizer instance name
    """

    def __init__(
        self,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "ZA_TELEPHONE_NUMBER",
        leniency: Optional[int] = 1,
        name: Optional[str] = None,
    ):
        super().__init__(
            supported_entity=supported_entity,
            target_classification="telephone",
            context=context,
            supported_language=supported_language,
            leniency=leniency,
            name=name,
        )
