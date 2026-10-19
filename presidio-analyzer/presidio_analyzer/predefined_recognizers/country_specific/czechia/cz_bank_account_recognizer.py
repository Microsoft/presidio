from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class CzBankAccountRecognizer(PatternRecognizer):
    """
    Recognizes Czech domestic bank account numbers.

    Czech account numbers use the national format
    ``[prefix-]number/bank_code``: an optional prefix of up to 6 digits,
    an account number of 2-10 digits and a mandatory 4-digit bank code
    (e.g. 0800 Česká spořitelna, 0100 Komerční banka).

    Legal basis: vyhláška ČNB č. 169/2011 Sb., o pravidlech tvorby čísla
    účtu v platebním styku. Data protection: GDPR Art. 4 Nr. 1,
    zákon č. 110/2019 Sb.

    Format:
        - Prefix (optional): 2-6 digits followed by a hyphen
        - Account number: 2-10 digits
        - Slash and a 4-digit bank code

    Checksum: both the prefix and the account number carry a weighted
    mod 11 check (weights 1, 2, 4, 8, 5, 10, 9, 7, 3, 6 applied from the
    rightmost digit). A full checksum pass promotes the match to
    MAX_SCORE; a failure keeps the base pattern score so that context
    words ("účet", "účtu", ...) drive the final confidence.

    Czech legal citations (zákon č. 262/2006 Sb., 115/2010 Sb., ...)
    share the ``NNN/YYYY`` shape with prefix-less accounts and are very
    common in legal and public-administration text, so two guards apply:

    - ``invalidate_result`` drops prefix-less matches whose numerator
      has at most 3 digits (Czech laws are numbered up to ~500 per
      year) and whose "bank code" is a year-like 1900-2099 value —
      even when the numerator passes the checksum (262 does).
    - A checksum pass with a year-like bank code that the ČNB never
      issued is not promoted to MAX_SCORE; it keeps the pattern score.
      Codes 2010 (Fio banka), 2060 (Citfin) and
      2070 (TRINITY BANK) fall inside the year range but are real,
      so accounts at those banks still validate fully.

    Examples (fictitious): 19-2000145399/0800, 2000145399/0800

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "cz"

    # Weights from vyhláška č. 169/2011 Sb., applied right-to-left.
    _WEIGHTS = (1, 2, 4, 8, 5, 10, 9, 7, 3, 6)

    # Bank codes issued by the ČNB ("Číselník kódů platebního
    # styku") that fall inside the year-like 1900-2099 range: Fio banka,
    # Citfin and TRINITY BANK. Any other year-like code makes
    # a legal-citation or date reading at least as likely as an account.
    _YEAR_LIKE_ISSUED_BANK_CODES = frozenset({"2010", "2060", "2070"})

    PATTERNS = [
        Pattern(
            "Czech bank account (prefix-number/bank code)",
            r"(?<![\w/-])(?:\d{2,6}-)?\d{2,10}/\d{4}(?![\w/-])",
            0.4,
        ),
    ]

    CONTEXT = [
        "účet",
        "účtu",
        "účtem",
        "účtě",
        "bankovní",
        "banka",
        "banky",
        "bance",
        "sporožiro",
        "platba",
        "platby",
        "ucet",
        "uctu",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "cs",
        supported_entity: str = "CZ_BANK_ACCOUNT",
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

    def _mod11(self, digits: str) -> bool:
        total = sum(
            int(digit) * weight
            for digit, weight in zip(reversed(digits), self._WEIGHTS)
        )
        return total % 11 == 0

    def validate_result(self, pattern_text: str) -> Optional[bool]:
        """
        Validate the account number using the ČNB weighted mod 11 check.

        Both the optional prefix and the account number must pass the
        weighted checksum for the match to be promoted to MAX_SCORE. A
        checksum failure returns ``None`` (keep the pattern score and let
        context words decide) because typos and formatted fragments are
        common in free text; only structurally impossible values
        (all-zero account, bank code 0000) return ``False``.

        :param pattern_text: the text to validate (prefix-number/bank code)
        :return: True if all checksums pass, False if structurally
                 invalid, None to fall back to the pattern score
        """
        pattern_text = pattern_text.strip()

        account_part, _, bank_code = pattern_text.partition("/")
        if len(bank_code) != 4 or not bank_code.isdigit():
            return False
        if bank_code == "0000":
            return False

        prefix, _, number = account_part.rpartition("-")
        if not number.isdigit() or (prefix and not prefix.isdigit()):
            return False

        # An account number of all zeros is never assigned.
        if number.lstrip("0") == "":
            return False

        if self._mod11(number) and (not prefix or self._mod11(prefix)):
            if self._is_unissued_year_like_code(bank_code):
                # A checksum-passing numerator over a year-like bank code
                # that the ČNB never issued (e.g. 12345/2006) is at least
                # as likely a citation or date as an account; keep the
                # pattern score and let context words decide instead of
                # promoting to MAX_SCORE.
                return None
            return True

        return None

    def _is_unissued_year_like_code(self, bank_code: str) -> bool:
        return (
            1900 <= int(bank_code) <= 2099
            and bank_code not in self._YEAR_LIKE_ISSUED_BANK_CODES
        )

    def invalidate_result(self, pattern_text: str) -> Optional[bool]:
        """
        Invalidate matches that are far more likely dates or legal citations.

        Czech legal references (``262/2006 Sb.``, ``115/2010 Sb.``) and
        date fragments (``04/2023``) share the ``N{1,3}/YYYY`` shape with
        prefix-less account numbers, and citations are ubiquitous in the
        legal/public-administration text this recognizer targets. Czech
        laws are numbered with at most three digits per year, so a
        prefix-less match whose numerator has up to 3 digits and whose
        "bank code" is a year-like 1900-2099 value is treated as a
        citation or date — even when the numerator happens to pass the
        mod 11 checksum (``262/2006``, the Labour Code, does). Accounts
        at banks whose real code falls in that range (e.g. Fio banka,
        2010) are in practice written with longer account numbers, so
        they are unaffected.

        :param pattern_text: the text to check
        :return: True if the match should be invalidated, None otherwise
        """
        account_part, _, bank_code = pattern_text.partition("/")
        if (
            "-" not in account_part
            and len(account_part) <= 3
            and account_part.isdigit()
            and bank_code.isdigit()
            and 1900 <= int(bank_code) <= 2099
        ):
            return True
        return None
