from typing import Generator, Optional, Union

from presidio_analyzer import RecognizerResult

from presidio_cli.config import PresidioCLIConfig


class Line(object):
    """Represents a line of text source."""

    def __init__(self, line_no: int, buffer: str, start: int, end: int) -> None:
        self.line_no = line_no
        self.start = start
        self.end = end
        self.buffer = buffer

    @property
    def content(self):
        """
        Get the content of the line.

        :returns: The encrypted text.
        """

        return self.buffer[self.start : self.end]


def line_generator(buffer: str) -> Generator[Line, None, None]:
    """Generate Line objects from text source. Returns a generator of Line objects.

    :param buffer: str, string to read from
    """
    line_no = 1
    cur = 0
    next = buffer.find("\n")
    while next != -1:
        if next > 0 and buffer[next - 1] == "\r":
            yield Line(line_no, buffer, start=cur, end=next - 1)
        else:
            yield Line(line_no, buffer, start=cur, end=next)
        cur = next + 1
        next = buffer.find("\n", cur)
        line_no += 1

    yield Line(line_no, buffer, start=cur, end=len(buffer))


class PIIProblem(object):
    """Represents a PII problem found by presidio-cli."""

    def __init__(self, line: int, recognizer_result: RecognizerResult) -> None:
        assert isinstance(recognizer_result, RecognizerResult)
        self.recognizer_result = recognizer_result.to_dict()
        #: Line on which the problem was found (starting at 1)
        self.line = line
        #: Column on which the problem was found (starting at 1)
        self.column = self.recognizer_result["start"] + 1
        #: Human-readable description of the problem
        self.explanation = self.recognizer_result["analysis_explanation"]
        #: Identifier of the rule that detected the problem
        self.type = self.recognizer_result["entity_type"]
        # Score as a probability determined by the model
        self.score = self.recognizer_result["score"]
        #: Severity: "error" for a full-confidence finding, "warning" otherwise
        self.level = "error" if self.score >= 1.0 else "warning"


def _analyze(
    buffer: str, conf: "PresidioCLIConfig"
) -> Generator["PIIProblem", None, None]:
    """Analyze a text source. Returns a generator of PIIProblem objects.

    :param buffer: str, string to read from
    :param conf: presidio_cli configuration object
    """
    assert hasattr(buffer, "__getitem__"), (
        "_run() argument must be a buffer, not a stream"
    )

    for line in line_generator(buffer):
        for result in conf.analyzer.analyze(
            text=line.content,
            entities=conf.entities,
            language=conf.language,
            allow_list=conf.allow_list,
        ):
            p = PIIProblem(line.line_no, result)
            if p.score >= conf.threshold:
                yield p


def analyze(
    input: str, conf: "PresidioCLIConfig", filepath: Optional[str] = None
) -> Union[tuple, Generator["PIIProblem", None, None], None]:
    """Analyze a text source. Returns a generator of PIIProblem objects.

    :param input: buffer, string or stream to read from
    :param conf: presidio_cli configuration object
    :param filepath: string, string with path to file
    """

    if conf.is_file_ignored(filepath):
        return tuple()
    if isinstance(input, (bytes, str)):
        return _analyze(input, conf)
    elif hasattr(input, "read"):  # Python 2's file or Python 3's io.IOBase
        # We need to have everything in memory to parse correctly
        content = input.read()
        return _analyze(content, conf)
    else:
        raise TypeError("input should be a string or a stream")
