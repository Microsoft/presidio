from pathlib import Path
from typing import Dict, Iterable, List, Optional

import regex as re

from presidio_analyzer import Pattern, PatternRecognizer

TLD_FILE = Path(__file__).parent / "tlds.txt"

# Sentinel key marking a complete TLD inside the prefix tree built by
# ``tlds_to_regex``. The empty string can never be a trie edge, since edges are
# single characters.
_TERMINAL = ""


def load_tlds(path: Path = TLD_FILE) -> List[str]:
    """
    Read the vendored IANA root zone TLD list.

    :param path: File holding one lowercase TLD per line, ``#`` for comments
    :return: The list of TLDs, in file order
    """
    with open(path, encoding="utf-8") as tld_file:
        return [
            line.strip().lower()
            for line in tld_file
            if line.strip() and not line.startswith("#")
        ]


def tlds_to_regex(tlds: Iterable[str]) -> str:
    """
    Compress a list of TLDs into a prefix-tree (trie) regex alternation.

    A flat ``(?:aaa)|(?:aarp)|...`` alternation over the whole root zone forces
    the engine to retry every branch at the same position. Sharing common
    prefixes instead - ``bar(?:c(?:elona|lay(?:card|s))|efoot|gains)?`` - keeps
    the pattern smaller and lets the engine discard whole subtrees on a single
    character.

    :param tlds: TLDs to match, case-insensitively
    :return: A non-capturing regex group matching exactly those TLDs
    """
    root: Dict = {}
    for tld in tlds:
        node = root
        for char in tld.lower():
            node = node.setdefault(char, {})
        node[_TERMINAL] = None

    return _branch_to_regex(root)


def _branch_to_regex(node: Dict) -> str:
    """
    Render a single trie node as a regex fragment.

    :param node: Trie node to render
    :return: Regex fragment, or an empty string for a leaf node
    """
    edges = sorted(char for char in node if char != _TERMINAL)
    if not edges:
        return ""

    # Edges leading straight to a leaf collapse into one character class.
    alternatives = []
    leaf_chars = []
    for char in edges:
        suffix = _branch_to_regex(node[char])
        if suffix:
            alternatives.append(re.escape(char) + suffix)
        else:
            leaf_chars.append(char)
    if leaf_chars:
        alternatives.append(_to_char_class(leaf_chars))

    # A node that is both terminal and has edges (e.g. `bar` and `barclays`)
    # must stay optional, so it always needs the enclosing group.
    if len(alternatives) == 1 and _TERMINAL not in node:
        return alternatives[0]
    closing = ")?" if _TERMINAL in node else ")"
    return "(?:" + "|".join(alternatives) + closing


def _to_char_class(chars: List[str]) -> str:
    """
    Turn single characters into a character class, or a literal if there is one.

    :param chars: Characters to match
    :return: Regex fragment matching any one of them
    """
    if len(chars) == 1:
        return re.escape(chars[0])
    return "[" + "".join(re.escape(char) for char in chars) + "]"


class UrlRecognizer(PatternRecognizer):
    """
    Recognize urls using regex.

    This application uses Open Source components:
    Project: CommonRegex https://github.com/madisonmay/CommonRegex
    Copyright (c) 2014 Madison May
    License (MIT)  https://github.com/madisonmay/CommonRegex/blob/master/LICENSE

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    TLDS = load_tlds()

    BASE_URL_REGEX = (
        r"((www\d{0,3}[.])?[a-z0-9.\-]{1,253}[.]"
        + tlds_to_regex(TLDS)
        # Require the TLD to end the host. Without this the engine happily
        # stops on a shorter TLD that merely prefixes the real one.
        + r"(?![a-z0-9\-])"
        + r"(?:/[^\s()<>\"']*)?)"
    )

    PATTERNS = [
        Pattern("Standard Url", "(?i)(?:https?://)" + BASE_URL_REGEX, 0.6),
        Pattern("Non schema URL", "(?i)" + BASE_URL_REGEX, 0.5),
        Pattern("Quoted URL", r'(?i)["\'](https?://' + BASE_URL_REGEX + r')["\']', 0.6),
        Pattern(
            "Quoted Non-schema URL", r'(?i)["\'](' + BASE_URL_REGEX + r')["\']', 0.5
        ),
    ]

    CONTEXT = ["url", "website", "link"]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "URL",
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
