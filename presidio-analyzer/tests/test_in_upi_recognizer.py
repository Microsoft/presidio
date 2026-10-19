import pytest
from tests import assert_result
from presidio_analyzer.predefined_recognizers import InUpiRecognizer


@pytest.fixture(scope="module")
def recognizer():
    return InUpiRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["IN_UPI"]


@pytest.mark.parametrize(
    "text, expected_len, expected_position, expected_score",
    [
        # fmt: off
        # Valid UPI IDs with known handles (High confidence)
        ("shaurya@okicici", 1, (0, 15), 0.7),
        ("9876543210@paytm", 1, (0, 16), 0.7),
        ("john.doe@okhdfcbank", 1, (0, 19), 0.7),
        ("user123@ybl", 1, (0, 11), 0.7),
        # Invalid UPI IDs
        ("notaupiid", 0, (), ()),
        ("@okicici", 0, (), ()),
        ("john.doe@gmail.com", 0, (), ()),
        ("admin@localhost", 0, (), ()),
        ("user@company.com", 0, (), ()),

        # Valid UPI IDs with unknown handles (Medium confidence)
        ("myname@somebank", 1, (0, 15), 0.4),

        

        # UPI in sentence
        ("Please pay to shaurya@okicici for the order", 1, (14, 29), 0.7),
        # fmt: on
    ],
)
def test_when_upi_in_text_then_all_upis_found(
    text,
    expected_len,
    expected_position,
    expected_score,
    recognizer,
    entities,
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    if results:
        assert_result(
            results[0],
            entities[0],
            expected_position[0],
            expected_position[1],
            expected_score,
        )
