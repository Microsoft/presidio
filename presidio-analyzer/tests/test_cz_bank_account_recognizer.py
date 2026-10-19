"""
Tests for CzBankAccountRecognizer (Czech domestic bank account numbers).

All test numbers are fictitious. Valid numbers satisfy the weighted mod 11
check of vyhláška ČNB č. 169/2011 Sb. (weights 1, 2, 4, 8, 5, 10, 9, 7, 3, 6
applied from the rightmost digit, on both the prefix and the account number).
"""
import pytest

from tests import assert_result
from presidio_analyzer.predefined_recognizers import CzBankAccountRecognizer

# Pattern score from CzBankAccountRecognizer.PATTERNS. A failed checksum
# returns None from validate_result, keeping this score so that context
# words decide.
_PATTERN_SCORE = 0.4


@pytest.fixture(scope="module")
def recognizer():
    return CzBankAccountRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["CZ_BANK_ACCOUNT"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_fn",
    [
        # fmt: off
        # Valid prefix and account checksum -> MAX_SCORE
        ("19-2000145399/0800", 1, ((0, 18),), lambda max_score: max_score),
        ("2000145399/0800", 1, ((0, 15),), lambda max_score: max_score),
        ("123456788/0100", 1, ((0, 14),), lambda max_score: max_score),
        ("č. ú. 19-2000145399/0800", 1, ((6, 24),), lambda max_score: max_score),
        # Account number fails the weighted mod 11 -> pattern score
        ("19-123456789/0800", 1, ((0, 17),), lambda max_score: _PATTERN_SCORE),
        # Prefix fails the weighted mod 11 -> pattern score
        ("18-2000145399/0800", 1, ((0, 18),), lambda max_score: _PATTERN_SCORE),
        # Bank code 0000 does not exist -> dropped by validation
        ("2000145399/0000", 0, (), None),
        # All-zero account number -> dropped by validation
        ("000000/0800", 0, (), None),
        # Date-like fragments are invalidated (dd/yyyy with 19xx/20xx)
        ("04/2023", 0, (), None),
        ("31/1999", 0, (), None),
        # Czech legal citations (zákon č. NNN/YYYY Sb.) are invalidated,
        # even when the numerator passes the mod 11 checksum (262 does)
        ("262/2006", 0, (), None),
        ("115/2010", 0, (), None),
        ("zákon č. 262/2006 Sb., zákoník práce", 0, (), None),
        ("89/2012", 0, (), None),
        # Accounts at banks whose real ČNB code is year-like (Fio banka,
        # 2010) still validate fully: numerators exceed law numbers
        ("2000145399/2010", 1, ((0, 15),), lambda max_score: max_score),
        # Embedded in a longer digit run -> no match
        ("119-123456789/08001", 0, (), None),
        # fmt: on
    ],
)
def test_when_all_cz_bank_accounts_then_succeed(
    text, expected_len, expected_positions, expected_score_fn,
    recognizer, entities, max_score,
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos) in zip(results, expected_positions):
        assert_result(
            res, entities[0], st_pos, fn_pos, expected_score_fn(max_score)
        )


@pytest.mark.parametrize(
    "number, expected",
    [
        # Valid prefix + account combinations
        ("19-2000145399/0800", True),
        ("2000145399/0800", True),
        ("35-123456788/0300", True),
        # Failing account or prefix checksum -> None (context decides)
        ("19-123456789/0800", None),
        ("18-2000145399/0800", None),
        ("850412/0003", None),
        # Checksum passes but the year-like "bank code" was never issued
        # by the ČNB -> None (no MAX_SCORE promotion)
        ("262/2006", None),
        ("123456788/2006", None),
        # Year-like code actually issued by the ČNB (Fio banka) -> True
        ("2000145399/2010", True),
        # Structurally impossible -> False
        ("2000145399/0000", False),
        ("000000/0800", False),
        ("2000145399/800", False),
        ("2000145399/08000", False),
    ],
)
def test_when_cz_bank_account_validated_then_checksum_result_is_correct(
    number, expected, recognizer
):
    assert recognizer.validate_result(number) == expected


@pytest.mark.parametrize(
    "number, expected",
    [
        # Date-like fragments and legal citations are invalidated
        ("04/2023", True),
        ("31/1999", True),
        ("262/2006", True),
        ("115/2010", True),
        ("89/2012", True),
        ("169/2011", True),
        # Real account shapes are not
        ("19-2000145399/0800", None),
        ("2000145399/0800", None),
        ("2345678/2010", None),  # long numerator at Fio banka (2010)
    ],
)
def test_when_cz_bank_account_invalidated_then_result_is_correct(
    number, expected, recognizer
):
    assert recognizer.invalidate_result(number) == expected
