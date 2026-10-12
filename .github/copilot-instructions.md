# Presidio Development & Review Instructions

Presidio is a Python-based data protection and de-identification SDK with
multiple components for detecting and anonymizing PII (Personally Identifiable
Information) in text and images.

Domain-specific rules live in path-scoped instruction files and apply on top of
this file when a change touches the matching paths:

- `.github/instructions/recognizers.instructions.md` — adding or modifying PII
  recognizers.
- `.github/instructions/yaml-config.instructions.md` — the pydantic layer that
  translates YAML configuration into Presidio instances.

## Core Philosophy

**Data privacy is paramount.** This is a PII detection and anonymization system
used in sensitive contexts; security and correctness are non-negotiable.

- **Accuracy first**: false negatives (missed PII) and false positives
  (incorrect detections) both damage trust.
- **Security by default**: never log PII values, use non-reversible
  anonymization, validate all inputs.
- **Presidio is a library**: changes to shared code alter results for users who
  wrote no new code. Backward compatibility is the prime directive.
- **Stateless design**: modules that process records are stateless for
  scalability — avoid adding state.
- **Cross-component awareness**: Presidio is a multi-component system; changes
  ripple across boundaries.
- **Documentation integrity**: code and docs must stay synchronized — outdated
  docs are dangerous.

## Backward Compatibility

Before changing anything outside a brand-new file, the PR description must
state what existing behavior changes. These count as behavior changes even
without a signature change:

- Default values on shared base classes (`None` to `[]` changes truthiness for
  every subclass).
- Properties on abstract interfaces — custom implementations inherit the new
  default and may break.
- Anything altering which entities are returned, or their scores, for text that
  previously worked.

Prefer additive changes: new parameters get defaults preserving current
behavior; public APIs are never broken without a deprecation path.

**Surface new scoring inputs in explainability.** Anything that changes how a
score is derived (context, negative context, thresholds) must be reflected in
`AnalysisExplanation`, or users cannot tell why a result scored as it did.

**Prefer warnings over exceptions when the caller cannot fix the condition.**
Raising on a configuration a user did not write turns a degraded result into a
hard failure. Where a lookup falls back to a default, add a debug log so the
fallback is discoverable.

**Prefer a property on the base class over a maintained list of class names.**
Lists drift as classes are added, and users installing from PyPI cannot extend
them.

## Cross-Component Changes

Data flows one way: Analyzer → Anonymizer → Output. Downstream components
(CLI, structured, image-redactor) consume analyzer/anonymizer, never the
reverse.

- Shared data models (`RecognizerResult`, `OperatorConfig`) are contracts —
  changes require coordinated updates across all consumers, in the same
  changeset.
- Reuse by importing from shared modules, not by copying code across
  components. If multiple components need a feature, extract it to a common
  location.
- Respect boundaries: a component imports another's public interface, never its
  internals (e.g. the anonymizer must not import
  `presidio_analyzer.predefined_recognizers`).
- Registry and provider patterns exist to decouple components — bypassing them
  creates hidden dependencies.
- Test the complete integration path (unit, integration, and e2e), not just
  isolated components.

## Security & Privacy

Always flag:

- **PII leakage in logs, errors, or debug output** — log entity types and
  positions, never `entity.text`.
- **Reversible or weak anonymization** — deterministic hashing is reversible
  via rainbow tables; use random/unpredictable replacement values that don't
  preserve PII characteristics.
- Regex injection: user-provided patterns must be validated before compilation.
- Hardcoded secrets or credentials; unsafe deserialization (pickle, untrusted
  models); command injection; path traversal; missing input validation on API
  endpoints (including unbounded input sizes).

## Performance

- Avoid catastrophic regex backtracking (`(a+)+b` is O(2^n) on `aaaa...b`);
  test patterns against long adversarial strings.
- Cache compiled regexes; don't recompile per call.
- Batch NLP processing (`nlp.pipe`) instead of per-text calls; load models
  once and reuse.
- Flag O(n²) where O(n) exists, blocking I/O on API paths, and loading entire
  datasets into memory.

## Testing Standards

- Test names describe behavior:
  `test_when_invalid_checksum_then_no_match`, not `test_case2`.
- Assert exact expected values, not ranges — a range assertion passes even when
  the logic producing the value breaks.
- Cover true positives, true negatives, edge cases, and values embedded in
  surrounding text; validate exact boundaries, not just types.
- Fix random seeds for non-deterministic NLP/ML tests.
- Test behavior, not implementation details.

## Documentation

When adding features, update all that apply: `docs/supported_entities.md` (new
entity types), `docs/api-docs/api-docs.yml` (API changes), `README.md` (major
features), docstrings (all public classes/methods, reST format — `:param:`,
`:return:`, `:raises:`), and `docs/samples/` (complex features).

Do not update `CHANGELOG.md` in a PR: current-release entries are generated
from merged PRs before each version bump, and per-PR edits create merge
conflicts.

Terminology: use "threshold", not "cutoff"; use ISO 639-1 language codes in
docs and configuration examples.

## Code Review Guidelines

- Only comment with HIGH CONFIDENCE (>80%) that an issue exists; be concise and
  actionable — cite the line and propose the concrete fix.
- Check for existing patterns and helpers in the codebase before suggesting new
  approaches.
- Severity: 🔴 security/PII leakage and correctness → 🟡 performance,
  cross-component breaks, missing tests → 💡 code quality.

**Do not flag** (automated tools own these): formatting, line length, import
order (Ruff); type-hint style (`List[str]` vs `list[str]`); style preferences
or speculative abstractions that don't fix bugs or improve accuracy.

## Repository Context

- **Python** `>=3.10,<3.15` — code must run on every version in range.
- **uv** for dependency management (not pip/Poetry); each package commits a
  `uv.lock`. Whenever a package's `pyproject.toml` dependencies change,
  regenerate and commit that package's `uv.lock` in the same change
  (`cd <package> && uv lock`) — CI installs with `uv sync --locked` and fails
  on drift.
- **Ruff** for linting and formatting; **spaCy** as the default NLP engine
  (swappable via provider pattern); **Docker** images on
  `ghcr.io/data-privacy-stack`.

```bash
# Setup and test (per package)
cd presidio-analyzer
uv sync --locked --all-extras --group dev
uv run python -m spacy download en_core_web_lg  # analyzer/CLI only
uv run pytest -xvv
uv run ruff check . && uv run ruff format .

# E2E
docker compose up --build -d && cd e2e-tests && pytest -v
```

Reference docs: `CONTRIBUTING.md`, `docs/development.md`,
`docs/analyzer/adding_recognizers.md`, `docs/analyzer/developing_recognizers.md`,
`docs/anonymizer/adding_operators.md`.
