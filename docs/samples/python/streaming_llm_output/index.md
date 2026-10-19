# Anonymizing streamed LLM output

LLM APIs usually stream a response as small text deltas. The split points are chosen by the model's tokenizer and the network, so an email address, phone number or name can arrive in two or more deltas.

This sample shows how to anonymize a stream with Presidio without letting part of an entity through, and how to test that.

## Why per-delta analysis leaks

Calling the analyzer on each delta on its own:

```python
deltas = [
    "Sure. You can reach Jane at jane.d",
    "oe@example.com or on 212-55",
    "5-0147.\nAnything else?",
]
for delta in deltas:
    results = analyzer.analyze(text=delta, language="en")
    send(anonymizer.anonymize(text=delta, analyzer_results=results).text)
```

sends:

```text
Sure. You can reach <PERSON> at jane.d<EMAIL_ADDRESS> or on 212-555-0147.
Anything else?
```

The phone number is sent in full, because neither half looks like a phone number on its own. The email address is detected only in the second delta, after `jane.d` was already sent.

Two fixes are often tried and both still leak:

- **Prepend the last few characters of the previous delta** and analyze the joined text. The entity is now detected, but its first part was already sent with the previous delta. Masking the rest cannot take it back.
- **Hold back a fixed number of characters.** Some entities have no maximum length, so any fixed window can be crossed.

The rule that works: do not send text until no entity could still extend into it.

## Hold back to a segment boundary

[`streaming_anonymizer.py`](https://github.com/data-privacy-stack/presidio/blob/main/docs/samples/python/streaming_llm_output/streaming_anonymizer.py) keeps a hold-back: the text after the last segment boundary, which is the only part of the stream that could still be the start of an entity. By default a boundary is a newline, or whitespace after `.`, `!` or `?`. Each time a delta arrives, every complete segment before the hold-back is analyzed, anonymized and returned; the hold-back stays until the next boundary arrives. At the end of the stream, `flush()` analyzes and returns what is left.

```python
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from streaming_anonymizer import StreamingAnonymizer

streaming = StreamingAnonymizer(AnalyzerEngine(), AnonymizerEngine())

# llm_stream yields text deltas from your LLM client.
for delta in llm_stream:
    # feed returns the anonymized text that is safe to send now.
    send(streaming.feed(delta))
# flush returns the held tail when the stream ends.
send(streaming.flush())
```

The same deltas produce:

```text
Sure. You can reach <PERSON> at <EMAIL_ADDRESS> or on <PHONE_NUMBER>.
Anything else?
```

Things to know:

- **Each segment is analyzed on its own.** Segment boundaries depend only on the text, so the output is the same however the stream was split. It can differ slightly from analyzing the whole response at once, because context words in an earlier segment are not seen.
- **Pick a boundary your entities cannot contain.** The default splits `Dr. Jane Doe` into `Dr. ` and `Jane Doe`, and splits a multi-line postal address. If that matters for your data, use a newline-only boundary (`re.compile(r"\n")`) and accept a longer hold-back.
- **Latency.** Text is sent a sentence at a time rather than a token at a time.

## How much to hold back

The hold-back must be at least as long as the longest entity a recognizer can match. If every recognizer had a maximum match length, holding back that many characters would be enough. Presidio's default recognizers do not: the spaCy NER recognizer matches names and locations of any length, and patterns such as URLs have no fixed cap. A fixed window can always be crossed, so the sample holds back to a natural boundary instead. That makes the hold-back as long as a sentence or a line, which is why it needs a limit:

- **Long segments fail closed.** A segment longer than `max_segment_chars` (2,000 by default) raises `SegmentTooLongError` instead of being sent unanalyzed. Catch it and end the response with an error. The limit also bounds memory: a single delta larger than the limit is taken in pieces, so the held text never grows past it.

If you restrict `entities` to pattern recognizers with a known maximum length, a fixed hold-back of that length is a valid boundary and gives lower latency.

## Testing at every split

Checking that the reassembled output contains no raw values is not enough. In the example above it catches the phone number but not the email: `oe@example.com` is itself a valid email address and gets masked, so the full address never appears in the output, yet `jane.d` was sent.

The property to test is that the output does not depend on where the stream was split, so run the text through the anonymizer split at every position and compare with the unsplit output:

```python
def run(deltas):
    streaming = StreamingAnonymizer(analyzer, anonymizer)
    return "".join(streaming.feed(d) for d in deltas) + streaming.flush()

text = "Sure. You can reach Jane Doe at jane.doe@example.com or on 212-555-0147.\nAnything else?"
expected = run([text])
for i in range(1, len(text)):
    assert run([text[:i], text[i:]]) == expected, i
```

[`test_streaming_anonymizer.py`](https://github.com/data-privacy-stack/presidio/blob/main/docs/samples/python/streaming_llm_output/test_streaming_anonymizer.py) runs this check over every two-part split and every fixed delta size, and shows that analyzing each delta on its own fails it. Use the same test for any streaming wrapper you write around Presidio.

## Running the sample

```bash
pip install presidio-analyzer presidio-anonymizer pytest
python -m spacy download en_core_web_lg
cd docs/samples/python/streaming_llm_output
python streaming_anonymizer.py
pytest test_streaming_anonymizer.py
```

Output of `python streaming_anonymizer.py` with `presidio-analyzer` 2.2.364 and `en_core_web_lg` 3.8.0:

```text
StreamingAnonymizer: 'Sure. You can reach <PERSON> at <EMAIL_ADDRESS> or on <PHONE_NUMBER>.\nAnything else?'
Each delta on its own gives the same output: False
```

## Further reading

- Split-Boundary Leaks in Streaming Guardrails, [doi:10.5281/zenodo.22909585](https://doi.org/10.5281/zenodo.22909585): the same defect in several LLM gateways and agent frameworks, and why the two common fixes leak.
