# Recognizing answers to prompts in call and chat transcripts

In a call or chat transcript, the words that say what a number *is* are
often in the **previous speaker's turn**, not next to the number:

```text
AGENT: Okay, what is the number on the card?
CUSTOMER: four five three nine, one four eight eight,
AGENT: mm-hmm
CUSTOMER: oh three four three, six four six seven.
BOT: Please enter your nine digit Social Security number.
CUSTOMER: 512437788#
```

The built-in recognizers miss these, for three reasons:

- Presidio's context enhancement only looks for context words around the
  match in the same text, so it cannot use the agent's question.
- A pattern recognizer does not read "four five three nine".
- A card number split across two turns matches no pattern at all.

This is the situation described in
[issue #1939](https://github.com/data-privacy-stack/presidio/issues/1939).

This sample adds `ConversationalPromptRecognizer`, which needs no NLP model:

1. It splits the transcript into turns: one `SPEAKER: text` per line.
2. When an agent or bot turn asks for an entity (a prompt phrase matches),
   it marks the **next customer turn** as that entity. A prompt applies to
   one answer only.
3. It normalizes the answer: spoken digits, "oh", "double" and "triple",
   fillers, separators, and a trailing keypad `#`. It keeps an offset map,
   so results point at the original words.
4. It joins an answer split across consecutive customer turns, skipping a
   backchannel ("mm-hmm") from the agent.
5. It gives a high score when the answer passes the entity's check (Luhn
   for a card, the SSA structure rules for an SSN), and a low score when it
   does not. A prompted answer is sensitive whatever its shape; the score
   lets a threshold decide.

## Usage

```python
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NoOpNlpEngine

from conversational_prompt_recognizer import ConversationalPromptRecognizer

registry = RecognizerRegistry()
registry.add_recognizer(ConversationalPromptRecognizer())
analyzer = AnalyzerEngine(
    registry=registry,
    nlp_engine=NoOpNlpEngine(models=[{"lang_code": "en", "model_name": "none"}]),
)

transcript = (
    "BOT: Please enter your credit card number, then press pound.\n"
    "CUSTOMER: 5555666677778888#"
)
for r in analyzer.analyze(transcript, language="en"):
    print(r.entity_type, r.score, transcript[r.start : r.end])
# CREDIT_CARD 0.3 5555666677778888   <- prompted, but fails Luhn: low score
```

Run the sample itself to see a split, spoken card number and a keyed SSN:

```sh
python conversational_prompt_recognizer.py
```

The recognizer can sit next to the built-in ones in the same registry. They
find values that carry their own context, and this recognizer finds the
answers.

## Customizing

- **`prompts`**: the entities a prompt can ask for. Each has its phrases
  (regular expressions, matched case-insensitively), its digit range and its
  check. The defaults cover `US_SSN` and `CREDIT_CARD`.
- **`asking_speakers` and `answering_speakers`**: the speaker labels in your
  transcripts.
- **`valid_score` and `invalid_score`**: scores for answers that pass or fail
  their check.
- **`max_joined_turns`**: how many turns one answer may span.

## Limitations

- The transcript must have one `SPEAKER: text` turn per line.
- An answer is the first digit run in each customer turn. A correction
  ("sorry, it's actually 5-6-7-7") is not tracked.
- Prompt phrases are English.

## Source

The sample comes from
[txp-labs/sensitive-data-scanner](https://github.com/txp-labs/sensitive-data-scanner),
which uses the same approach with a declarative spec. There, a
TypeScript implementation for live redaction and the Presidio runner are
tested against a shared set of synthetic transcript cases. All values here
are synthetic.
