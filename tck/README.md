# Presidio TCK (Technology Compatibility Kit)

Portable test suite for Presidio PII recognizers. Extracts test data from
`@pytest.mark.parametrize` annotations in `presidio-analyzer/tests/` and
produces YAML files that any compatible implementation can validate against.

## Quick start

```bash
cd tck
uv sync --group dev
uv run python extract_tck.py    # generate YAML from Python tests
uv run python validate_tck.py   # validate YAML against live Presidio
```

## How it works

**Source of truth** stays in the Python test files. The YAML is a derived
artifact, regenerated on demand.

```
presidio-analyzer/tests/test_*_recognizer.py
        |
        |  extract_tck.py (pytest import + AST + tokenize)
        v
tck/data/*.yaml  (one file per recognizer, with comments)
        |
        |  validate_tck.py (instantiate recognizer, run test cases)
        v
pass / fail
```

- `extract_tck.py` imports each test module via pytest to resolve
  `@pytest.mark.parametrize` data (handles computed values, f-strings,
  list multiplication). Comments are extracted from source via AST + regex.
- `validate_tck.py` loads each YAML file, instantiates the named recognizer,
  and runs every test case against the live Presidio implementation.
- Both scripts are **idempotent** — safe to run repeatedly.

## YAML format

```yaml
recognizer: AuAbnRecognizer
entity_type: AU_ABN
language: en
country_code: au

test_cases:
  # Valid formatting and valid ABNs
  - input: "51 824 753 556"
    expected:
      - start: 0
        end: 14
        score: 1.0

  # Valid formatting but invalid ABNs
  - input: "52 824 753 556"
    expected: []  # should NOT match
```

See `schema/tck-recognizer-tests.schema.json` for the full JSON Schema.

## Implementing validation in another language

Download the TCK data from a GitHub release (or generate it with `extract_tck.py`)
and validate your recognizer implementation against each YAML file. The algorithm
is the same regardless of language:

```
for each YAML file:
  instantiate the recognizer named in `recognizer`
  for each test_case:
    run the recognizer on test_case.input for entity_type
    sort results by start position

    if test_case has `expected_count`:
      assert len(results) == expected_count
    else:
      assert len(results) == len(expected)
      for each (result, exp) pair:
        assert result.start == exp.start
        assert result.end   == exp.end
        if exp has `score`:     assert result.score == exp.score
        if exp has `score_min`: assert result.score >= exp.score_min
        if exp has `score_max`: assert result.score <= exp.score_max
```

A failing test should report the file, test index, what was expected vs. what the
recognizer returned, and the input text. For example:

```
FAIL [0]: span[0]: got (0,16), expected (0,10) | '4012888888881881 ...'
```

See `validate_tck.py` for a complete Python reference implementation.

## CI integration

```yaml
- name: Generate and validate TCK
  run: |
    python tck/extract_tck.py
    python tck/validate_tck.py
```

The generated `data/` directory is gitignored — it is a build artifact,
not committed. On releases it can be packaged as a `presidio-tck.tar.gz`.

## Scope

**Included** (~74 recognizers, ~1478 test cases):
all deterministic `PatternRecognizer` subclasses (regex, checksum, deny-list)
across 19 countries.

**Excluded** (16 test files):
NLP/ML model-dependent recognizers (spaCy, Stanza, Transformers, GLiNER,
HuggingFace NER), remote/LLM services (Azure AI, LangExtract), and
phone recognizers requiring NLP artifacts or custom config.
