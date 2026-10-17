import argparse
import os
import pytest
from io import StringIO
from presidio_analyzer import RecognizerResult
from presidio_cli import cli
from presidio_cli.analyzer import PIIProblem
from presidio_cli.config import PresidioCLIConfig as RealPresidioCLIConfig


@pytest.fixture()
def problems():
    problem1 = PIIProblem(1, RecognizerResult("CREDIT_CARD", 6, 25, 1.0))
    problem2 = PIIProblem(2, RecognizerResult("PERSON", 16, 26, 0.85))
    # The analyzer only returns explanations when asked for its decision
    # process, so set one here to exercise the formatters' explanation branch.
    problem2.explanation = "some example"
    return [problem1, problem2]


def make_args(**overrides):
    args = {
        "stdin": False,
        "config_data": None,
        "config_file": None,
        "files": ("tests/",),
        "format": "auto",
        "no_warnings": False,
        "threshold": None,
    }
    args.update(overrides)
    return args


def make_conf(mocker, threshold=0.25):
    conf = mocker.Mock()
    conf.threshold = threshold
    conf.locale = None
    return conf


def test_find_files_recursively(temp_workspace, config):
    assert sorted(cli.find_files_recursively([temp_workspace], config)) == [
        os.path.join(temp_workspace, "dos.yml"),
        os.path.join(temp_workspace, "empty.txt"),
        os.path.join(temp_workspace, "errorfile"),
        os.path.join(temp_workspace, "non-ascii", "éçäγλνπ¥", "utf-8"),
        os.path.join(temp_workspace, *["s"] * 15, "file"),
        os.path.join(temp_workspace, "sub", "directory.txt", "empty.txt"),
    ]


@pytest.mark.parametrize(
    "arg_format",
    [
        "auto",
        "standard",
        "colored",
        "github",
        "parsable",
    ],
)
def test_show_problems(arg_format, problems):
    filepath = "./example.txt"

    rc = cli.show_problems(problems, filepath, arg_format, False)
    assert rc == 2


@pytest.mark.parametrize("arg_format", ["standard", "colored", "github", "parsable"])
def test_show_problems_no_warnings_outputs_only_errors(arg_format, problems, capsys):
    rc = cli.show_problems(problems, "example.txt", arg_format, True)

    out = capsys.readouterr().out
    assert rc == 1
    assert "CREDIT_CARD" in out
    assert "PERSON" not in out


def test_show_problems_no_warnings_without_errors_returns_zero(problems, capsys):
    rc = cli.show_problems(problems[1:], "example.txt", "standard", True)

    assert rc == 0
    assert capsys.readouterr().out == ""


def test_standard_color_marks_errors_red_and_warnings_yellow(problems):
    error, warning = problems

    assert "\033[31m1.0\033[0m" in cli.Format.standard_color(error)
    assert "\033[33m0.85\033[0m" in cli.Format.standard_color(warning)


def test_github_format_emits_annotation_commands(problems, capsys):
    cli.show_problems(problems, "dir/a,b:c%.txt", "github", False)

    assert capsys.readouterr().out.splitlines() == [
        "::group::dir/a,b:c%25.txt",
        "::error file=dir/a%2Cb%3Ac%25.txt,line=1,col=7::1:7 [CREDIT_CARD] score=1.0",
        "::warning file=dir/a%2Cb%3Ac%25.txt,line=2,col=17::"
        "2:17 [PERSON] score=0.85 (some example)",
        "::endgroup::",
        "",
    ]


def test_github_format_escapes_message_data():
    problem = PIIProblem(1, RecognizerResult("PERSON", 0, 5, 0.5))
    problem.explanation = "50%\r\nsure"

    assert cli.Format.github(problem, "a\nb.txt") == (
        "::warning file=a%0Ab.txt,line=1,col=1::"
        "1:1 [PERSON] score=0.5 (50%25%0D%0Asure)"
    )


@pytest.mark.parametrize("filename", ["./example.txt", ".\\example.txt"])
def test_github_format_drops_current_dir_prefix(problems, filename):
    assert cli.Format.github(problems[0], filename).startswith(
        "::error file=example.txt,line=1,col=7::"
    )


def test_show_problems_auto_gh(problems, monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_WORKFLOW", "true")

    filepath = "./example.txt"
    rc = cli.show_problems(problems, filepath, "auto", False)
    assert rc == 2


def test_show_problems_auto_color(problems, monkeypatch, mocker):
    monkeypatch.setenv("TERM", "xterm-256color")
    mocker.patch("sys.stdout")
    filepath = "./example.txt"
    rc = cli.show_problems(problems, filepath, "auto", False)
    assert rc == 2


def test_run_current_dir(temp_workspace, mocker):
    os.chdir(temp_workspace)
    mocker.patch("sys.argv", ["", "."])
    ec = mocker.patch("sys.exit")
    cli.run()
    ec.assert_called_once_with(1)


def test_run_with_config(temp_workspace, mocker):
    with open(os.path.join(temp_workspace, ".presidiocli"), "w") as f:
        f.write("extends: default\n")

    os.chdir(temp_workspace)
    mocker.patch("sys.argv", ["-c", ".presidiocli", "."])
    ec = mocker.patch("sys.exit")
    cli.run()
    ec.assert_called_once_with(1)


def test_run_no_warnings_reports_only_errors(
    temp_workspace, mocker, monkeypatch, capsys
):
    monkeypatch.chdir(temp_workspace)
    mocker.patch("sys.argv", ["", "--no-warnings", "-f", "standard", "."])
    ec = mocker.patch("sys.exit")

    cli.run()

    out = capsys.readouterr().out
    assert "CREDIT_CARD" in out
    assert "PERSON" not in out
    ec.assert_called_once_with(1)


def test_run_exit_code_counts_problems_in_every_file(
    mocker, problems, tmp_path, monkeypatch
):
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "b.txt").write_text("b")
    monkeypatch.chdir(tmp_path)
    mocked_args = mocker.Mock(**make_args(files=("a.txt", "b.txt"), format="standard"))
    mocker.patch("presidio_cli.cli.PresidioCLIConfig", return_value=make_conf(mocker))
    mocker.patch(
        "presidio_cli.cli.find_files_recursively", return_value=["a.txt", "b.txt"]
    )
    mocker.patch("presidio_cli.cli.analyze", side_effect=[problems, []])
    mocker.patch("argparse.ArgumentParser.parse_args", return_value=mocked_args)
    ec = mocker.patch("sys.exit")

    cli.run()

    ec.assert_called_once_with(1)


@pytest.mark.parametrize(("no_warnings", "exit_code"), [(False, 1), (True, 0)])
def test_run_exit_code_ignores_problems_hidden_by_no_warnings(
    mocker, problems, tmp_path, monkeypatch, no_warnings, exit_code
):
    (tmp_path / "a.txt").write_text("a")
    monkeypatch.chdir(tmp_path)
    mocked_args = mocker.Mock(
        **make_args(files=("a.txt",), format="standard", no_warnings=no_warnings)
    )
    mocker.patch("presidio_cli.cli.PresidioCLIConfig", return_value=make_conf(mocker))
    mocker.patch("presidio_cli.cli.find_files_recursively", return_value=["a.txt"])
    mocker.patch("presidio_cli.cli.analyze", return_value=problems[1:])
    mocker.patch("argparse.ArgumentParser.parse_args", return_value=mocked_args)
    ec = mocker.patch("sys.exit")

    cli.run()

    ec.assert_called_once_with(exit_code)


def test_run_preserves_config_threshold_when_flag_is_omitted(mocker):
    mocked_args = mocker.Mock(**make_args())
    conf = make_conf(mocker)
    config = mocker.patch("presidio_cli.cli.PresidioCLIConfig", return_value=conf)
    mocker.patch("presidio_cli.cli.find_files_recursively", return_value=[])
    mocker.patch("os.path.isfile", return_value=False)
    mocker.patch("argparse.ArgumentParser.parse_args", return_value=mocked_args)
    ec = mocker.patch("sys.exit")

    cli.run()

    config.assert_called_once_with(content="extends: default")
    assert conf.threshold == 0.25
    ec.assert_called_once_with(0)


def test_run_overrides_loaded_config_threshold(mocker, tmp_path):
    config_file = tmp_path / "config.yml"
    config_file.write_text("threshold: 0.25\n")

    mocked_args = mocker.Mock(**make_args(config_file=str(config_file), threshold=0.7))
    loaded_thresholds = []
    captured = {}

    def build_config(*args, **kwargs):
        conf = RealPresidioCLIConfig(*args, **kwargs)
        loaded_thresholds.append(conf.threshold)
        captured["conf"] = conf
        return conf

    mocker.patch("presidio_cli.cli.PresidioCLIConfig", side_effect=build_config)
    mocker.patch("presidio_cli.cli.find_files_recursively", return_value=[])
    mocker.patch("argparse.ArgumentParser.parse_args", return_value=mocked_args)
    ec = mocker.patch("sys.exit")

    cli.run()

    assert loaded_thresholds == [0.25]
    assert captured["conf"].threshold == 0.7
    ec.assert_called_once_with(0)


def test_run_respects_config_selection_before_threshold_override(mocker):
    mocked_args = mocker.Mock(
        **make_args(config_data="extends: limited", config_file="custom.yaml")
    )
    conf = make_conf(mocker)
    config = mocker.patch("presidio_cli.cli.PresidioCLIConfig", return_value=conf)
    mocker.patch("presidio_cli.cli.find_files_recursively", return_value=[])
    mocker.patch("os.path.isfile", return_value=False)
    mocker.patch("argparse.ArgumentParser.parse_args", return_value=mocked_args)
    ec = mocker.patch("sys.exit")

    cli.run()

    config.assert_called_once_with(content="extends: limited")
    assert conf.threshold == 0.25
    ec.assert_called_once_with(0)


def test_run_accepts_explicit_zero_threshold(mocker):
    mocked_args = mocker.Mock(**make_args(threshold=0.0))
    conf = make_conf(mocker)
    config = mocker.patch("presidio_cli.cli.PresidioCLIConfig", return_value=conf)
    mocker.patch("presidio_cli.cli.find_files_recursively", return_value=[])
    mocker.patch("os.path.isfile", return_value=False)
    mocker.patch("argparse.ArgumentParser.parse_args", return_value=mocked_args)
    ec = mocker.patch("sys.exit")

    cli.run()

    config.assert_called_once_with(content="extends: default")
    assert conf.threshold == 0.0
    ec.assert_called_once_with(0)


@pytest.mark.parametrize("value", ["-0.1", "1.1", "not-a-number"])
def test_threshold_value_rejects_invalid_values(value):
    with pytest.raises(argparse.ArgumentTypeError):
        cli.threshold_value(value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [("0", 0.0), ("0.7", 0.7), ("1", 1.0)],
)
def test_threshold_value_accepts_valid_values(value, expected):
    assert cli.threshold_value(value) == expected


def test_run_with_stdin(mocker):
    mocked_args = mocker.Mock(**make_args(stdin=True, files=()))
    conf = make_conf(mocker)
    mocker.patch("presidio_cli.cli.PresidioCLIConfig", return_value=conf)
    mocker.patch("presidio_cli.cli.find_files_recursively", return_value=[])
    mocker.patch("presidio_cli.cli.analyze", return_value=[])
    mocker.patch("argparse.ArgumentParser.parse_args", return_value=mocked_args)
    mocker.patch("sys.stdin", StringIO("Example input"))
    ec = mocker.patch("sys.exit")
    cli.run()
    ec.assert_called_once_with(0)


def test_run_with_stdin_exits_with_one_when_problems_are_found(mocker, problems):
    mocked_args = mocker.Mock(**make_args(stdin=True, files=(), format="standard"))
    mocker.patch("presidio_cli.cli.PresidioCLIConfig", return_value=make_conf(mocker))
    mocker.patch("presidio_cli.cli.find_files_recursively", return_value=[])
    mocker.patch("presidio_cli.cli.analyze", return_value=problems)
    mocker.patch("argparse.ArgumentParser.parse_args", return_value=mocked_args)
    mocker.patch("sys.stdin", StringIO("Example input"))
    ec = mocker.patch("sys.exit")
    cli.run()
    ec.assert_called_once_with(1)
