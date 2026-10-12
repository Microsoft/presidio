---
applyTo: "presidio-analyzer/presidio_analyzer/predefined_recognizers/**,presidio-analyzer/presidio_analyzer/conf/default_recognizers.yaml,presidio-analyzer/tests/test_*recognizer*.py,docs/supported_entities.md"
---

# Recognizer changes

Rules for adding or modifying PII recognizers. When reviewing, lead with the
highest-impact gaps in this order:

1. **Pattern accuracy.** The pattern is as specific as the format allows, the
   score is calibrated to the pattern alone, the context words are the right
   ones, the checksum is correct where one exists (and none is invented where
   it doesn't — `validate_result` must not promote weak matches to 1.0), and
   the logic's source is documented, preferably an official specification.
2. **Proper testing.** A configuration-path test through
   `RecognizerRegistryProvider` (the load-bearing rule below), exact-score
   assertions rather than ranges, a lookalike negative, and
   context-enhancement coverage.
3. Construction paths that disagree (direct vs. `add_recognizer()` vs. YAML).
4. Changes to an *existing* recognizer's patterns, scores, or context made as a
   side effect of adding a new one — users depend on current detection behavior.
5. Language/country-code mismatch; missing exports, YAML entry, or docs row.

Give specific, actionable feedback: cite the file and line and propose the
concrete fix. Do not comment on formatting — Ruff and CI own that.

## The load-bearing rule: test the configuration path

Most predefined recognizers ship `enabled: false`, so the default test run never
constructs them from configuration. Users, however, reach them exactly one way:
flipping `enabled: true` in a registry YAML. A recognizer that works when built
in Python can still be unreachable — or crash — when enabled in YAML.

**Every new or changed recognizer needs at least one test that loads it through
`RecognizerRegistryProvider` and asserts detection:**

```python
def test_recognizer_loads_and_detects_when_enabled_in_yaml(tmp_path):
    """Detection must work through the path users actually configure."""
    conf = tmp_path / "recognizers.yaml"
    conf.write_text(
        """
supported_languages:
  - en
recognizers:
  - name: MyRecognizer
    supported_languages:
      - en
    type: predefined
    enabled: true
    country_code: us
"""
    )
    registry = RecognizerRegistryProvider(conf_file=conf).create_recognizer_registry()
    analyzer = AnalyzerEngine(registry=registry, nlp_engine=nlp_engine)

    results = analyzer.analyze("Member ID ABC123456", language="en")

    assert [result.entity_type for result in results] == ["MY_ENTITY"]
```

This catches, at minimum:

- Constructor signatures incompatible with the keys the loader passes (`name`,
  `supported_entity`, `context`) — e.g.
  `TypeError: __init__() got an unexpected keyword argument 'name'`, which takes
  down construction of the whole registry the moment the recognizer is enabled.
- Class name typos and missing `__init__.py` exports.
- `country_code` mismatches between the class attribute and the YAML entry.
- Class-level defaults (thresholds, context) that configuration silently discards.
- A recognizer whose declared languages are excluded by the top-level
  `supported_languages` filter, which loads nothing and reports no error.

**Non-English recognizers:** the top-level `supported_languages` key acts as a
global filter and the shipped default is `["en"]`. A recognizer supporting only
`de` will not load from that config — silently. The test config and the PR
description must state the required top-level languages.

**Construction paths must agree.** Building the recognizer directly, adding it
via `registry.add_recognizer()`, and loading it from configuration must all
produce the same recognizer. Flag defaulting or validation logic applied on one
path but not the others.

## Placement and naming

- Country-specific: `predefined_recognizers/country_specific/{country}/`;
  generic patterns: `predefined_recognizers/generic/`; NLP/ML-based:
  `nlp_engine_recognizers/` or `ner/`; third-party: `third_party/`.
- New country directories use the full lowercase country name (`south_africa`,
  `philippines`, `canada`). Some pre-existing directories use short forms
  (`us`, `uk`, `thai`); do not imitate them.
- `supported_language` and the YAML `supported_languages` key take **ISO 639-1
  language codes** (`ko` for Korean), not country codes (`kr`). A mismatch
  produces a recognizer that never loads, with no error.

## Pattern scores

The base score must reflect how much the pattern *alone* narrows the space,
independent of any downstream threshold:

| Score | Use when | Name the pattern |
| --- | --- | --- |
| 0.05–0.1 | Bare digit or alphanumeric runs, no structure | `"(very weak)"` |
| 0.1–0.3 | Some structure: delimiters, a prefix, a length constraint | `"(weak)"` |
| 0.3–0.5 | Distinctive format, no validation | `"(medium)"` |
| 0.5+ | Distinctive format | `"(strong)"` |

Compare against existing recognizers before accepting a score
(`UsPassportRecognizer` uses 0.05 for nine bare digits). A 0.3 on a pattern that
also matches `covid19` or `sha256` is overstated. Coincidental matches at a low
score are the mechanism working as designed — a threshold filters them, and
context or validation raises the real ones.

Suppress low-confidence matches with `score_thresholds`, not by requiring
context: `presidio-structured` has no surrounding text to draw context from.

## Context words

`LemmaContextAwareEnhancer` defaults to `context_matching_mode="substring"`, so
short context words fire on unrelated tokens: `member` matches `remember`,
`auth` matches `author` and `OAuth`. Prefer context long enough to be
unambiguous (`member id`, `subscriber`, `prior authorization`).

Context is prefix-only by default (`context_prefix_count=5`,
`context_suffix_count=0`), so a context word *after* the match does not boost
the score. Tests should cover both placements.

## Validation and invalidation hooks

| Hook | Return | Effect on the result |
| --- | --- | --- |
| `validate_result` | `True` | Score replaced with `MAX_SCORE` (1.0) |
| `validate_result` | `False` | Score set to `MIN_SCORE` and result dropped |
| `validate_result` | `None` | Pattern score stands unchanged |
| `invalidate_result` | `True` | Score set to `MIN_SCORE` and result dropped |

- **`True` is a jump to full confidence, not a nudge.** Ask what fraction of
  arbitrary same-shape tokens would pass: a mod-11 check on a 17-character token
  passes ~9% of the time, sending ~9% of coincidental matches to 1.0 where no
  threshold can filter them. Only promote where the check is genuinely mandatory
  for that value.
- **Return `None`, never `False`, when the check does not apply.** `False` means
  "definitely not the entity" and discards the result.
- **No checksum is fine.** About 40% of predefined recognizers do not override
  `validate_result`; the base score plus a threshold is a valid design. Do not
  request an invented validator — but do flag one that promotes weak matches.
- Well-known sample values and reserved ranges belong in `invalidate_result`,
  not buried in the regex.

## Enabled by default or not

Global (non-country-specific) recognizers — credit card, email, IBAN, IP, URL —
generally ship `enabled: true`, provided their false-positive rate is low.
Country-specific recognizers default to `enabled: false`. In both cases the
deciding question is whether the recognizer can produce **high-confidence false
positives**; shipping enabled requires justification in the PR description and
both of:

- The base score is calibrated to the pattern's specificity (bands above).
- Nothing promotes a coincidental match to a score the user cannot filter.

## Test quality

- **Assert exact scores, not ranges.** `assert 0.5 <= score <= 1.0` still
  passes when checksum promotion or context enhancement breaks entirely. Pin it:
  `assert result.score == pytest.approx(EntityRecognizer.MAX_SCORE)`.
- **Include a lookalike negative** — a plausible non-PII token of the same shape
  (a 17-character order ID for a VIN, a legal citation for a bank account
  number) asserted as *not* flagged. This is the actual false-positive surface.
- **Exercise context enhancement.** A recognizer defining `CONTEXT` needs a test
  showing the score differs between text with and without a context word.
- **Assert entity boundaries** (exact start/end), not just entity type — and
  include values embedded in surrounding text.
- **Use example values the recognizer actually accepts.** Well-known samples
  like `123-45-6789` are denylisted by `UsSsnRecognizer`: as a true positive the
  test fails, and as a false-positive case it passes for the wrong reason.

## Required companion updates

A new recognizer needs all of:

1. Export in `presidio_analyzer/predefined_recognizers/__init__.py` **and** the
   country/category `__init__.py`.
2. An entry in `presidio_analyzer/conf/default_recognizers.yaml` (normally
   `enabled: false`).
3. A row in `docs/supported_entities.md`.
4. A docstring citing the pattern's source: the official standard, government
   specification, or authoritative reference the format comes from, plus the
   validation algorithm if any (e.g. "Luhn checksum per ISO/IEC 7812").
