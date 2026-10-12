---
applyTo: "presidio-analyzer/presidio_analyzer/input_validation/**,presidio-analyzer/presidio_analyzer/recognizer_registry/**,presidio-analyzer/presidio_analyzer/conf/**,presidio-analyzer/presidio_analyzer/nlp_engine/ner_model_configuration.py,presidio-analyzer/tests/test_yaml_recognizer_models.py,presidio-analyzer/tests/test_recognizer_registry_provider.py,presidio-analyzer/tests/test_configuration_validator.py,presidio-analyzer/tests/test_config_loader.py,presidio-analyzer/tests/test_recognizer_registry.py,presidio-analyzer/tests/test_ner_model_configuration.py"
---

# YAML configuration & pydantic validation layer

Rules for the layer that translates YAML configuration into Presidio instances:
the pydantic models in `presidio_analyzer/input_validation/`
(`yaml_recognizer_models.py`, `schemas.py`), the loaders in
`recognizer_registry/`, and the shipped configs in `conf/`.

This layer is a public contract. YAML files written by users years ago must keep
parsing, and every field a user can write must actually reach the object it
configures. When reviewing, lead with:

1. A YAML-reachable field that silently goes nowhere (schema/constructor drift).
2. A change that makes existing YAML files stop parsing or change meaning.
3. A validation failure surfacing as a distant `TypeError` instead of a parse-time
   error with an actionable message.

## Schema/constructor sync

Every constructor parameter that should be settable from YAML needs a matching
pydantic field. In every contribution, check that constructor parameters and
schema fields have not drifted apart — a mismatch means a value a user writes
in YAML never reaches the object, or reaches it unvalidated. As of today the
consequence is silent: `PredefinedRecognizerConfig` ignores unknown YAML keys,
so a constructor kwarg without a schema field is dropped without any error and
the recognizer falls back to its defaults (the failure
`LangExtractRecognizerConfig` exists to prevent; see its docstring). Even if
that `extra` behavior changes, the no-mismatch rule stands.

- A recognizer whose constructor takes model-specific kwargs needs a dedicated
  config model registered in `CONFIG_MODEL_MAP` (keyed by `class_name` or
  `name`), following `HuggingFaceRecognizerConfig` / `GLiNERRecognizerConfig` /
  `LangExtractRecognizerConfig`.
- When a PR adds a constructor parameter to a recognizer that already has a
  config model, require the matching field in that model — otherwise YAML users
  cannot set it and get no error telling them so.

## `extra` must be a deliberate choice

- `extra="forbid"` for closed configs (`TextChunkerConfig`,
  `RecognizerRegistryConfig`): typos fail fast at parse time with a clear
  message.
- `extra="allow"` for pass-through configs whose kwargs flow to a constructor
  (HuggingFace, GLiNER, LangExtract).
- Flag a new model that leaves pydantic's default (`extra="ignore"`) without
  justification — silent ignoring is almost never the intended behavior.

## `exclude_none` discipline on kwargs models

Models whose dump is passed to a constructor override `model_dump` with
`exclude_none=True`, so a field omitted in YAML preserves the constructor
default instead of overriding it with an explicit `None`. Any new pass-through
config model must do the same; flag one that doesn't — it silently clobbers
constructor defaults, which is this layer's sneakiest backward-compatibility
trap.

## Fail early, with actionable messages

Validation belongs at parse time, in the pydantic model, phrased so the user
knows how to fix their YAML — not as a distant `TypeError` during registry
construction. House style to hold new code to:

- Class existence checked at parse time
  (`validate_predefined_recognizer_exists` → "Predefined recognizer 'X' not
  found"), and custom/predefined name conflicts rejected with the fix spelled
  out ("Either use type: 'predefined' or choose a different name").
- Mutually exclusive fields enforced in a `model_validator` naming both fields
  ("Cannot specify both 'supported_language' and 'supported_languages'"), with
  an example of the correct form where the fix isn't obvious (see the global
  context validator).
- Parameters checked against the selected mode (`TextChunkerConfig` rejects
  `max_tokens` on a character chunker by name, listing the allowed fields).
- Prefer warnings over exceptions when the caller cannot fix the condition;
  raising on a config the user didn't write turns a degraded result into a hard
  failure.

## Backward compatibility of the schema

Existing user YAML must keep working. Each of these is a breaking change and
must be called out explicitly in the PR description:

- A new **required** field, a renamed field, or a removed field.
- A tightened validator that rejects previously-accepted YAML.
- A changed default (including a changed `enabled`, score, or language default).
- Dropping support for the legacy singular forms. `supported_language` /
  `supported_languages` and `supported_entity` / `supported_entities` both stay
  supported, with mutual exclusivity enforced — do not remove the legacy form.
- Removing accepted input shapes: bare-string recognizer entries and dict
  entries with inferred `type` (`patterns`/`deny_list` ⇒ custom) are all valid
  today and must remain so.

## Required tests for changes in this layer

- **Round-trip through the provider**: load a config through
  `RecognizerRegistryProvider` and assert on the constructed registry — not
  only on the validated pydantic model. Model-level tests miss dump/loader
  drift.
- The shipped `conf/default_recognizers.yaml` must validate against the models;
  a change to either side needs `test_recognizer_registry_provider.py` /
  `test_yaml_recognizer_models.py` updated in the same PR.
- New validators need both directions tested: valid YAML passes, invalid YAML
  fails **with the expected message** (assert on the message — it is part of
  the user experience).
- A new schema field needs a test proving the value actually reaches the
  constructed object, not just that validation accepts it.
