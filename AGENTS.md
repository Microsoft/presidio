# Presidio — Agent Guidelines

Presidio is a Python SDK for detecting (presidio-analyzer) and anonymizing
(presidio-anonymizer) PII in text and images, plus CLI, structured-data, and
image-redaction components. It is a widely used **library**: users depend on
current detection behavior, and configuration files written years ago must keep
working. Correctness and backward compatibility outrank cleverness.

The review-side versions of these rules — which the Copilot PR review agent
also enforces — live in `.github/copilot-instructions.md` and
`.github/instructions/*.instructions.md`. Follow them at authoring time so the
review finds nothing.

## Working in this repo

```bash
cd presidio-analyzer            # or presidio-anonymizer, presidio-cli, ...
uv sync --locked --all-extras --group dev
uv run python -m spacy download en_core_web_lg   # analyzer/CLI only
uv run pytest -xvv
uv run ruff check . && uv run ruff format .
```

- Python `>=3.10,<3.15`; code must run on every version in range.
- Dependencies are managed with **uv**, not pip/Poetry. If you touch a
  package's `pyproject.toml` dependencies, run `uv lock` in that package and
  commit the updated `uv.lock` in the same change — CI fails on drift.
- Do not edit `CHANGELOG.md`; release entries are generated from merged PRs.
- Never log PII values (`entity.text`) — only entity types and positions.
- Modules that process records are stateless; do not add state.
- Terminology: "threshold", not "cutoff"; ISO 639-1 language codes everywhere.

## Adding a PII recognizer

The full rulebook — score bands, context-word rules, validation-hook
semantics, the configuration-path test template, and the test-quality bar —
is `.github/instructions/recognizers.instructions.md`. **Read it before
starting**; those rules apply at authoring time, not just in review. The
workflow, in order:

1. **Place and name it** under `predefined_recognizers/`: full lowercase
   country name for new country directories (`south_africa`, not `za`;
   don't imitate the pre-existing short forms `us`/`uk`/`thai`), or
   `generic/`, `nlp_engine_recognizers/`, `ner/`, `third_party/` as
   appropriate.
2. **Use ISO 639-1 language codes** (`ko` for Korean, never `kr`) — a
   mismatch loads nothing, silently.
3. **Make the constructor loader-compatible**: accept the YAML loader's
   kwargs (`name`, `supported_entity`, `context`, ...) and forward them to
   the base class, or the recognizer crashes the whole registry the moment a
   user enables it.
4. **Design the pattern for accuracy first** — this is the top review
   priority: as specific as the format allows, score calibrated to the
   pattern alone, unambiguous context words, the correct checksum if one
   exists (and none invented if it doesn't), and the pattern's source
   documented in the docstring, preferably an official specification.
5. **Register it everywhere**: exports in `predefined_recognizers/__init__.py`
   *and* the country/category `__init__.py`; an entry in
   `conf/default_recognizers.yaml` (country-specific ships `enabled: false`);
   a row in `docs/supported_entities.md`.
6. **Write the configuration-path test** — the most-missed step and the one
   that matters most: enable the recognizer in a YAML config, load it through
   `RecognizerRegistryProvider`, and assert detection (template in the
   instructions file). Non-English recognizers must set the top-level
   `supported_languages` in the test config — it defaults to `["en"]` and
   silently filters everything else.

When **modifying** an existing recognizer: changed patterns, scores, or context
change detection results for existing users — state that in the PR description,
and never change an existing recognizer as a side effect of adding a new one.

## Changing the YAML configuration layer

The rulebook for the pydantic models in `presidio_analyzer/input_validation/`
is `.github/instructions/yaml-config.instructions.md` — **read it before
touching the layer**. The short version:

- Constructor parameters and schema fields must never drift apart: a
  YAML-settable kwarg without a matching pydantic field is silently dropped
  today. Model-specific kwargs need a dedicated config model registered in
  `CONFIG_MODEL_MAP`.
- Choose `extra` deliberately (`forbid` fails fast, `allow` passes through);
  pass-through models dump with `exclude_none=True` so YAML omissions keep
  constructor defaults.
- Validate at parse time with actionable messages, and never break existing
  YAML — legacy singular fields, bare-string entries, and inferred `type` all
  stay supported.
- Test through `RecognizerRegistryProvider`, not just the pydantic model:
  prove new fields reach the constructed object and assert error *messages*
  for invalid YAML.

## General engineering rules

- **Declare behavior changes.** Any edit outside a brand-new file needs the PR
  description to say what existing behavior changes. Defaults on shared base
  classes, properties on abstract interfaces, and anything altering returned
  entities or scores all count, even with no signature change.
- **Explainability**: anything that changes how a score is derived must be
  reflected in `AnalysisExplanation`.
- **Component boundaries**: data flows Analyzer → Anonymizer → Output; import
  public interfaces, never another component's internals; shared models
  (`RecognizerResult`, `OperatorConfig`) are contracts — update all consumers
  in the same changeset.
- **Anonymizer operators**: non-reversible by default — no deterministic
  hashing (rainbow tables), unpredictable replacement values, no preserved PII
  characteristics. Deterministic or format-preserving output is sometimes a
  hard requirement (e.g. referential integrity across a dataset); support it as
  an explicit, documented opt-in, never as the default behavior.
- **Security**: never log PII values; validate untrusted inputs before use
  (user-supplied regexes before compilation, file paths, API payloads); no
  hardcoded secrets; no unsafe deserialization of untrusted models or pickles.
- **Performance**: no catastrophic regex backtracking (test long adversarial
  inputs); cache compiled regexes; batch NLP with `nlp.pipe`.
- **Docs move with code**: `docs/supported_entities.md` for entities,
  `docs/api-docs/api-docs.yml` for API changes, reST docstrings on public
  APIs, samples for complex features.
