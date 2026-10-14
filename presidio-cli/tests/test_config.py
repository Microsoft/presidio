import os
import pytest

from presidio_cli import config


def test_parse_config():
    new = config.PresidioCLIConfig(
        "entities:\n" "  - PERSON\n" "  - IP_ADDRESS\n" "  - CREDIT_CARD\n" "threshold: 1.0\n" "locale: en_US.UTF-8\n"
    )

    assert new.entities == ["PERSON", "IP_ADDRESS", "CREDIT_CARD"]


def test_invalid_conf():
    with pytest.raises(config.PresidioCLIConfigError):
        config.PresidioCLIConfig("not: valid: yaml")


def test_invalid_extend_conf(temp_workspace):
    with open(os.path.join(temp_workspace, "notvalid.yml"), "w") as f:
        f.write("not: valid: yaml")
    with pytest.raises(config.PresidioCLIConfigError):
        config.PresidioCLIConfig(os.path.join(temp_workspace, "notvalid.yml"))


def test_not_dict():
    with pytest.raises(config.PresidioCLIConfigError):
        config.PresidioCLIConfig("example")


def test_unknown_entity():
    with pytest.raises(config.PresidioCLIConfigError) as excinfo:
        config.PresidioCLIConfig("entities:\n" "  - NOTEXISTS\n")
    assert "invalid config: no such entity NOTEXISTS" in str(excinfo.value)


def test_is_file(temp_workspace, config):
    for f in [
        os.path.join(temp_workspace, "empty.txt"),
        os.path.join(temp_workspace, "sub", "directory.txt", "empty.txt"),
        os.path.join(temp_workspace, "non-ascii", "éçäγλνπ¥", "utf-8"),
        os.path.join(temp_workspace, "dos.yml"),
        os.path.join(temp_workspace, *["s"] * 15, "file"),
    ]:
        assert config.is_text_file(f)

    assert not config.is_text_file(os.path.join(temp_workspace, "binary_file"))


def test_invalid_value(temp_workspace):
    with pytest.raises(config.PresidioCLIConfigError):
        config.PresidioCLIConfig("ignore: 1\n")

    with pytest.raises(config.PresidioCLIConfigError):
        config.PresidioCLIConfig("locale: 1\n")


def test_run_with_ignored_path(temp_workspace):
    new = config.PresidioCLIConfig("ignore: |\n" "  .git\n" "  s/*\n" "  dos.yml\n")
    assert new.is_file_ignored("./dos.yml")
    assert new.is_file_ignored("./.git/hooks/README.sample")
    assert not new.is_file_ignored("notignored")


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("5", "Invalid threshold value: 5. Threshold must be between 0 and 1"),
        ("-0.1", "Invalid threshold value: -0.1. Threshold must be between 0 and 1"),
        (".nan", "Invalid threshold value: nan. Threshold must be between 0 and 1"),
        ("abc", "Invalid threshold value: abc. Threshold must be a number"),
        ("[]", "Invalid threshold value: []. Threshold must be a number"),
        ("true", "Invalid threshold value: True. Threshold must be a number"),
        pytest.param(
            "1" + "0" * 400,
            f"Invalid threshold value: 1{'0' * 400}. Threshold must be a number",
            id="int-too-large-for-float",
        ),
    ],
)
def test_invalid_threshold_raises_config_error(value, message):
    with pytest.raises(config.PresidioCLIConfigError) as excinfo:
        config.PresidioCLIConfig(f"threshold: {value}\n")
    assert str(excinfo.value) == message


@pytest.mark.parametrize(("value", "expected"), [("0", 0.0), ("0.7", 0.7), ("1", 1.0)])
def test_threshold_is_read_from_config(value, expected):
    assert config.PresidioCLIConfig(f"threshold: {value}\n").threshold == expected
