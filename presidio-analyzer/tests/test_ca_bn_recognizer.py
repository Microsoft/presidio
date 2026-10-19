import pytest

from tests import assert_result_within_score_range
from presidio_analyzer.predefined_recognizers import CaBnRecognizer


@pytest.fixture(scope="module")
def recognizer():
    return CaBnRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["CA_BN"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off
        # --- Valid 9-digit BNs (weak) ---
        ("123456782", 1, ((0, 9),), ((0.0, 0.3),),),
        ("130692544", 1, ((0, 9),), ((0.0, 0.3),),),
        ("764584124", 1, ((0, 9),), ((0.0, 0.3),),),

        # --- Valid program account numbers (medium) ---
        ("130692544 RT 0001", 1, ((0, 17),), ((0.5, 0.81),),),
        ("123456782RT0001", 1, ((0, 15),), ((0.5, 0.81),),),
        ("764584124 RP0001", 1, ((0, 16),), ((0.5, 0.81),),),
        ("123456782 RR 0001", 1, ((0, 17),), ((0.5, 0.81),),),

        # --- Valid BN with context ---
        ("Business Number: 123456782", 1, ((17, 26),), ((0.0, 0.3),),),
        ("Numéro d'entreprise : 123456782 RT 0001", 1, ((22, 39),), ((0.5, 0.81),),),  # noqa: E501

        # --- Malformed reference number falls back to the bare BN ---
        ("123456782 RT 001", 1, ((0, 9),), ((0.0, 0.3),),),

        # --- Invalid: checksum failure ---
        ("123456789", 0, (), (),),
        ("123456789 RT 0001", 0, (), (),),
        ("130692545", 0, (), (),),

        # --- Invalid: all same digit ---
        ("000000000", 0, (), (),),
        ("111111111", 0, (), (),),

        # --- Invalid: unknown program identifier ---
        ("123456782 XX 0001", 1, ((0, 9),), ((0.0, 0.3),),),

        # --- Invalid: wrong length ---
        ("12345678", 0, (), (),),
        ("1234567820", 0, (), (),),

        # --- Invalid: joined to a larger token by . / - ---
        ("0.123456782", 0, (), (),),
        ("123456782.5", 0, (), (),),
        ("PO-123456782", 0, (), (),),
        ("INV/123456782", 0, (), (),),
        ("123456782-A", 0, (), (),),

        # --- Punctuation that is not part of the number is fine ---
        ("(123456782)", 1, ((1, 10),), ((0.0, 0.3),),),
        ("BN is 123456782.", 1, ((6, 15),), ((0.0, 0.3),),),
        # fmt: on
    ],
)
def test_when_bn_in_text_then_all_ca_bns_are_found(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
    max_score,
):
    results = recognizer.analyze(text, entities)
    results = sorted(results, key=lambda x: x.start)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos), (st_score, fn_score) in zip(
        results, expected_positions, expected_score_ranges
    ):
        if fn_score == "max":
            fn_score = max_score
        assert_result_within_score_range(
            res, entities[0], st_pos, fn_pos, st_score, fn_score
        )
