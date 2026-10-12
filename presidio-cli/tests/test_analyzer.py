import pytest
from presidio_analyzer import RecognizerResult
from presidio_cli.analyzer import PIIProblem, analyze, line_generator


def test_line_generator():
    e = list(line_generator(""))
    assert len(e) == 1
    assert e[0].line_no == 1
    assert e[0].start == 0
    assert e[0].end == 0

    e = list(line_generator("\n"))
    assert len(e) == 2

    e = list(line_generator(" \n"))
    assert len(e) == 2
    assert e[0].line_no == 1
    assert e[0].start == 0
    assert e[0].end == 1

    e = list(line_generator("\n\n"))
    assert len(e) == 3

    e = list(line_generator("---\n" "this is line 1\n" "line 2\n" "\n" "3\n"))
    assert len(e) == 6
    assert e[0].line_no == 1
    assert e[0].content == "---"
    assert e[2].content == "line 2"
    assert e[3].content == ""
    assert e[5].line_no == 6

    e = list(line_generator("test with\n" "no newline\n" "at the end"))
    assert len(e) == 3
    assert e[2].line_no == 3
    assert e[2].content == "at the end"


def test_analyze(en_core_web_lg, config):
    result = list(
        analyze(
            "His name is Mr. Jones and his phone number is 212-555-5555\n"
            "Hi my name is Charles Darwin and\n"
            "my email is cdarwin@hmsbeagle.org\n",
            config,
        )
    )

    assert len(result) == 5


def test_analyze_with_allow_list(en_core_web_lg, config, config_with_allow_list):
    result_without_allow_list = list(analyze("John Sample\n" "example@example.com", config))

    result_with_allow_list = list(analyze("John Sample\n" "example@example.com", config_with_allow_list))

    assert len(result_without_allow_list) - len(result_with_allow_list) == 3


def test_analyze_type_error(en_core_web_lg, config):
    with pytest.raises(TypeError):
        analyze({}, config)


@pytest.mark.parametrize(
    ("score", "level"),
    [(1.0, "error"), (0.99, "warning"), (0.85, "warning"), (0.0, "warning")],
)
def test_pii_problem_level_is_error_only_for_full_confidence(score, level):
    problem = PIIProblem(1, RecognizerResult("PERSON", 0, 5, score))

    assert problem.level == level
