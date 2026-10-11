import pytest

from tests import assert_result
from presidio_analyzer.predefined_recognizers import CryptoRecognizer


@pytest.fixture(scope="module")
def recognizer():
    return CryptoRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["CRYPTO"]


# Generate random address https://www.bitaddress.org/
@pytest.mark.parametrize(
    "text, expected_len, expected_positions",
    [
        # fmt: off
        ## Match
        # Test with valid P2PKH address that starts with 1 and 33 base58 characters
        ("16Yeky6GMjeNkAiNcBY7ZhrLoMSgg1BoyZ", 1, ((0, 34),),),        
        # Test with valid P2SH address that starts with 3 and 33 base58 characters
        ("3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy", 1, ((0, 34),),),
        # Test with valid Bech32 address that starts with bc1 and 39 base58 characters
        ("bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq", 1, ((0, 42),),),
        # Test with valid Bech32m address that starts with bc1 and 59 base58 characters
        ("bc1p5d7rjq7g6rdk2yhzks9smlaqtedr4dekq08ge8ztwac72sfr9rusxg3297", 1, ((0, 62),),),
        # Test with multiple valid addresses
        ("16Yeky6GMjeNkAiNcBY7ZhrLoMSgg1BoyZ 3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy", 2, ((0, 34), (35, 69)),),
        # Test with valid address in a sentence
        ("my wallet address is: 16Yeky6GMjeNkAiNcBY7ZhrLoMSgg1BoyZ", 1, ((22, 56),),),
        pytest.param("bc1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3qccfmv3", 1, ((0, 62),), id="p2wsh"),
        pytest.param("BC1QAR0SRRR7XFKVY5L643LYDNW9RE59GTZZWF5MDQ", 1, ((0, 42),), id="uppercase-p2wpkh"),
        pytest.param("BC1P5D7RJQ7G6RDK2YHZKS9SMLAQTEDR4DEKQ08GE8ZTWAC72SFR9RUSXG3297", 1, ((0, 62),), id="uppercase-p2tr"),

        ## No match
        # Test with invalid address
        ("16Yeky6GMjeNkAiNcBY7ZhrLoMSgg1BoyZ2", 0, ()),
        # Test with invalid address in a sentence
        ("my wallet address is: 16Yeky6GMjeNkAiNcBY7ZhrLoMSgg1BoyZ2", 0, ()),
        pytest.param("bc1qar0srrr7xfkvy5l643lydnw9re59gtzzm4yhgz", 0, (), id="v0-with-bech32m-checksum"),
        pytest.param("bc1p0xlxvlhemja6c4dqv22uapctqupfhlxm9h8z3k2e72q4k9hcz7vqh2y7hd", 0, (), id="v1-with-bech32-checksum"),
        pytest.param("bc1qar0srrr7xfkvy5l643lydnw9rcf5tga4", 0, (), id="v0-16-byte-program"),
        pytest.param("bc1qar0srrr7xfkvy5l643lydnw9re59gtzzqt0uyrt", 0, (), id="excess-padding"),
        pytest.param("Bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq", 0, (), id="mixed-case"),
        # Test with empty string
        ("", 0, (),),
        ("8f953371d3e85eddb89b05ed6b9e680791055315c73e1025ab5dba7bb2aee189", 0, (),),
        # fmt: on
    ],
)
def test_when_all_cryptos_then_succeed(
    text, expected_len, expected_positions, recognizer, entities, max_score
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos) in zip(results, expected_positions):
        assert_result(res, entities[0], st_pos, fn_pos, max_score)


@pytest.mark.parametrize(
    "address, expected",
    [
        pytest.param("bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq", (0, 20), id="p2wpkh"),
        pytest.param(
            "BC1QAR0SRRR7XFKVY5L643LYDNW9RE59GTZZWF5MDQ", (0, 20), id="uppercase-p2wpkh"
        ),
        pytest.param(
            "bc1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3qccfmv3",
            (0, 32),
            id="p2wsh",
        ),
        pytest.param(
            "bc1p5d7rjq7g6rdk2yhzks9smlaqtedr4dekq08ge8ztwac72sfr9rusxg3297",
            (1, 32),
            id="p2tr",
        ),
        pytest.param(
            "bc1pqypqxpq9qcrsszg2pvxq6rs0zqg3yyc5z5kxkvra", (1, 21), id="v1-21-byte"
        ),
        pytest.param(
            "bc1pw508d6qejxtdg4y5r3zarvary0c5xw7kw508d6qejxtdg4y5r3zarvary0c5xw7kt5nd6y",
            (1, 40),
            id="v1-40-byte",
        ),
        pytest.param(
            "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzm4yhgz",
            None,
            id="v0-with-bech32m-checksum",
        ),
        pytest.param(
            "bc1p0xlxvlhemja6c4dqv22uapctqupfhlxm9h8z3k2e72q4k9hcz7vqh2y7hd",
            None,
            id="v1-with-bech32-checksum",
        ),
        pytest.param(
            "bc1qar0srrr7xfkvy5l643lydnw9rcf5tga4", None, id="v0-16-byte-program"
        ),
        pytest.param(
            "tb1qqypqxpq9qcrsszg2pvxq6rs0zqg3yyc5r7fxez", None, id="testnet-hrp"
        ),
        pytest.param(
            "bc13qypqxpq9qcrsszg2pvxq6rs0zqg3yyc5rkyx9v", None, id="version-17"
        ),
        pytest.param(
            "bc1pqqqsyqcyq5rqwzqfpg9scrgwpugpzysnzs23v9ccrydpk8qarc0jqgfzyvjz2f389q02am2l",
            None,
            id="41-byte-program",
        ),
        pytest.param("bc1pqystr2wj", None, id="1-byte-program"),
        pytest.param(
            "bc1pqypqxpq9qcrsszg2pvxq6rs0zqg3yyc5z4tsze70", None, id="nonzero-padding"
        ),
        pytest.param(
            "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzqt0uyrt", None, id="excess-padding"
        ),
        pytest.param(
            "Bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq", None, id="mixed-case"
        ),
    ],
)
def test_decode_segwit_address_enforces_bip173_and_bip350(address, expected):
    decoded = CryptoRecognizer.decode_segwit_address("bc", address)
    if expected is None:
        assert decoded is None
    else:
        version, program = decoded
        assert (version, len(program)) == expected
