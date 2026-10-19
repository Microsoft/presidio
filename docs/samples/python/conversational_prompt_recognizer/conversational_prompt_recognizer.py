"""A question-then-answer recognizer for call and chat transcripts.

In a transcript, the words that say what a number *is* are often in the
previous speaker's turn:

    AGENT: Okay, what is the number on the card?
    CUSTOMER: four five three nine, one four eight eight, ...

or in an IVR, keyed after a prompt:

    BOT: Please enter your nine digit Social Security number.
    CUSTOMER: 512437788#

Presidio's context enhancement looks for context words around the match in
the same text, so it cannot use the agent's question, and a pattern
recognizer cannot read "four five three nine". This sample recognizer:

1. splits a transcript into speaker turns (``SPEAKER: text``, one per line);
2. when an agent or bot turn asks for an entity (a prompt phrase matches),
   marks the **next customer turn** as that entity;
3. normalizes the customer's answer (spoken digits, "oh", "double",
   "triple", fillers, separators, a trailing keypad ``#``) with an offset map
   back to the original text;
4. joins an answer split across consecutive customer turns;
5. reports the answer with a high score when it passes the entity's check
   (Luhn for a card, the SSA structure rules for an SSN) and a low score when
   it does not. A prompted answer is sensitive whatever its shape, and the
   score lets a threshold decide.

It needs no NLP model. All values in this file are synthetic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from presidio_analyzer import AnalysisExplanation, EntityRecognizer, RecognizerResult
from presidio_analyzer.nlp_engine import NlpArtifacts

DIGIT_WORDS = {
    "zero": "0",
    "oh": "0",
    "o": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
}
MULTIPLIERS = {"double": 2, "triple": 3}
FILLERS = {"uh", "um", "umm", "er", "erm", "ah", "hmm", "mm"}
SEPARATORS = " -.,"


def normalize_spoken_digits(text: str) -> Tuple[str, List[Tuple[int, int]]]:
    """Normalize spoken and keyed digits, keeping a map back to the original text.

    "four five three nine" becomes "4539", "one oh double five" becomes
    "1055", "512 43 7788#" becomes "512437788". "oh" and "o" are zero only
    next to another digit ("oh, it's one two" keeps its "oh").

    :param text: One turn of a transcript.
    :return: The normalized text, and for each of its characters the
        ``(start, end)`` range of the original text it came from.
    """
    tokens = [
        (m.start(), m.end(), m.group()) for m in re.finditer(r"[A-Za-z]+|.", text, re.S)
    ]
    out: List[Tuple[str, int, int]] = []

    def next_word(i: int) -> Optional[str]:
        for _, _, tok in tokens[i + 1 :]:
            if tok.isspace():
                continue
            return tok.lower()
        return None

    i = 0
    while i < len(tokens):
        start, end, tok = tokens[i]
        word = tok.lower()
        if word in MULTIPLIERS:
            j = i + 1
            while j < len(tokens) and tokens[j][2].isspace():
                j += 1
            if j < len(tokens):
                nxt = tokens[j][2].lower()
                digit = DIGIT_WORDS.get(nxt) or (nxt if nxt.isdigit() else None)
                if digit:
                    out.extend(
                        (digit, start, tokens[j][1]) for _ in range(MULTIPLIERS[word])
                    )
                    i = j + 1
                    continue
        if word in DIGIT_WORDS:
            if word in ("oh", "o"):
                before = "".join(c for c, _, _ in out).rstrip()
                after = next_word(i)
                if not (
                    before[-1:].isdigit()
                    or (after and (after in DIGIT_WORDS or after.isdigit()))
                ):
                    out.extend((c, start + k, start + k + 1) for k, c in enumerate(tok))
                    i += 1
                    continue
            out.append((DIGIT_WORDS[word], start, end))
            i += 1
            continue
        out.extend((c, start + k, start + k + 1) for k, c in enumerate(tok))
        i += 1

    # Drop fillers between digits, separators between digits and a keypad "#".
    text2 = "".join(c for c, _, _ in out)
    keep = [True] * len(out)
    for m in re.finditer(
        r"(?<=[0-9])(?:[ \-.,]|\b(?:%s)\b)+(?=[0-9])" % "|".join(FILLERS), text2, re.I
    ):
        for k in range(m.start(), m.end()):
            keep[k] = False
    for m in re.finditer(r"(?<=[0-9])[#*](?![A-Za-z0-9])", text2):
        keep[m.start()] = False
    kept = [ch for ch, k in zip(out, keep) if k]
    return "".join(c for c, _, _ in kept), [(s, e) for _, s, e in kept]


def luhn_valid(digits: str) -> bool:
    """Luhn (mod 10) check, per ISO/IEC 7812-1."""
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
    return total % 10 == 0


def ssn_structure_valid(digits: str) -> bool:
    """US SSN structure: area not 000, 666 or 900-999; group not 00; serial not 0000."""
    area = int(digits[:3])
    return (
        area not in (0, 666)
        and area < 900
        and digits[3:5] != "00"
        and digits[5:] != "0000"
    )


@dataclass(frozen=True)
class PromptedEntity:
    """What a prompt asks for, and how to tell a well-formed answer."""

    entity: str
    phrases: Tuple[str, ...]
    min_digits: int
    max_digits: int
    check: Callable[[str], bool]


DEFAULT_PROMPTS = (
    PromptedEntity(
        "US_SSN",
        (r"social security number", r"\bssn\b"),
        9,
        9,
        lambda d: len(d) == 9 and ssn_structure_valid(d),
    ),
    PromptedEntity(
        "CREDIT_CARD",
        (r"credit card number", r"card number", r"debit card", r"number on the card"),
        13,
        19,
        lambda d: 13 <= len(d) <= 19 and luhn_valid(d),
    ),
)

TURN = re.compile(r"^\s*([A-Za-z][A-Za-z _-]{0,30}):\s?(.*)$")


class ConversationalPromptRecognizer(EntityRecognizer):
    """Recognize the answer to a question asked in the previous speaker's turn.

    :param prompts: The entities a prompt can ask for, with their phrases
        (regular expressions, matched case-insensitively) and checks.
    :param asking_speakers: Speaker labels whose turns can ask (upper case).
    :param answering_speakers: Speaker labels whose turns answer.
    :param valid_score: The score of an answer that passes its check.
    :param invalid_score: The score of an answer that does not.
    :param max_joined_turns: How many consecutive answering turns can hold one
        answer ("5 1 2" then "4 3" then "7 7 8 8").
    """

    def __init__(
        self,
        prompts: Tuple[PromptedEntity, ...] = DEFAULT_PROMPTS,
        asking_speakers: Tuple[str, ...] = (
            "AGENT",
            "BOT",
            "EMPLOYEE",
            "SYSTEM",
            "IVR",
        ),
        answering_speakers: Tuple[str, ...] = ("CUSTOMER", "CALLER", "USER"),
        valid_score: float = 0.85,
        invalid_score: float = 0.3,
        max_joined_turns: int = 4,
        supported_language: str = "en",
        name: Optional[str] = None,
    ):
        self.prompts = prompts
        self.asking = {s.upper() for s in asking_speakers}
        self.answering = {s.upper() for s in answering_speakers}
        self.valid_score = valid_score
        self.invalid_score = invalid_score
        self.max_joined_turns = max_joined_turns
        self._phrases = [
            (p, re.compile(phrase, re.I)) for p in prompts for phrase in p.phrases
        ]
        super().__init__(
            supported_entities=sorted({p.entity for p in prompts}),
            supported_language=supported_language,
            name=name or "ConversationalPromptRecognizer",
        )

    def load(self) -> None:  # noqa: D102
        pass

    def _asked(self, utterance: str) -> Optional[PromptedEntity]:
        best: Optional[Tuple[int, PromptedEntity]] = None
        for prompted, rx in self._phrases:
            for m in rx.finditer(utterance):
                if best is None or m.end() - m.start() > best[0]:
                    best = (m.end() - m.start(), prompted)
        return best[1] if best else None

    def analyze(
        self, text: str, entities: List[str], nlp_artifacts: NlpArtifacts = None
    ) -> List[RecognizerResult]:
        """Find answers to prompts in a transcript: one ``SPEAKER: text`` per line."""
        turns = []  # (speaker, utterance, offset of the utterance in `text`)
        pos = 0
        for line in text.split("\n"):
            m = TURN.match(line)
            if m:
                turns.append((m.group(1).strip().upper(), m.group(2), pos + m.start(2)))
            pos += len(line) + 1

        results: List[RecognizerResult] = []
        armed: Optional[PromptedEntity] = None
        i = 0
        while i < len(turns):
            speaker, utterance, _ = turns[i]
            if speaker in self.asking:
                asked = self._asked(utterance)
                if asked:
                    armed = asked
                i += 1
                continue
            if speaker not in self.answering or armed is None:
                i += 1
                continue
            prompted, armed = armed, None
            if entities and prompted.entity not in entities:
                i += 1
                continue
            # Read the answer: digit runs from this turn, then from the next
            # customer turns while the answer is still too short.
            digits = ""
            spans: Dict[int, Tuple[int, int]] = {}
            j = i
            while j < len(turns) and j - i < self.max_joined_turns:
                sp, utt, offset = turns[j]
                if sp in self.asking and self._asked(utt):
                    break
                if sp not in self.answering:
                    j += 1  # a backchannel from the agent ("mm-hmm") in between
                    continue
                norm, mapping = normalize_spoken_digits(utt)
                run = re.search(r"[0-9]+", norm)
                if run is None:
                    break
                digits += run.group()
                spans[j] = (
                    offset + mapping[run.start()][0],
                    offset + mapping[run.end() - 1][1],
                )
                j += 1
                if len(digits) >= prompted.min_digits:
                    break
            if digits:
                valid = prompted.check(digits)
                score = self.valid_score if valid else self.invalid_score
                why = (
                    f"Answer to a prompt for {prompted.entity} in the previous turn; "
                    + ("passes its check." if valid else "does not pass its check.")
                )
                for start, end in spans.values():
                    results.append(
                        RecognizerResult(
                            entity_type=prompted.entity,
                            start=start,
                            end=end,
                            score=score,
                            analysis_explanation=AnalysisExplanation(
                                recognizer=self.name,
                                original_score=score,
                                textual_explanation=why,
                            ),
                            recognition_metadata={
                                RecognizerResult.RECOGNIZER_NAME_KEY: self.name,
                                RecognizerResult.RECOGNIZER_IDENTIFIER_KEY: self.id,
                            },
                        )
                    )
                i = max(j, i + 1)
                continue
            i += 1
        return results


if __name__ == "__main__":
    from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
    from presidio_analyzer.nlp_engine import NoOpNlpEngine

    registry = RecognizerRegistry()
    registry.add_recognizer(ConversationalPromptRecognizer())
    analyzer = AnalyzerEngine(
        registry=registry,
        nlp_engine=NoOpNlpEngine(models=[{"lang_code": "en", "model_name": "none"}]),
    )

    # Synthetic values only.
    transcript = "\n".join(
        [
            "EMPLOYEE: If you'd like we can move on to the payment.",
            "CUSTOMER: Yes, I'd like to pay with my credit card.",
            "EMPLOYEE: Okay, what is the number on the card?",
            "CUSTOMER: four five three nine, one four eight eight,",
            "EMPLOYEE: mm-hmm",
            "CUSTOMER: oh three four three, six four six seven.",
            "BOT: Please enter your nine digit Social Security number.",
            "CUSTOMER: 512437788#",
        ]
    )
    for r in analyzer.analyze(transcript, language="en"):
        print(r.entity_type, round(r.score, 2), repr(transcript[r.start : r.end]))
