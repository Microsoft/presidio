# ruff: noqa: D103,D200,D205,E501,F841,I001

import copy
import functools
import inspect
import re
from pathlib import Path
from typing import Dict, List

import presidio_analyzer.predefined_recognizers as predefined
import pytest
import yaml
from presidio_analyzer import EntityRecognizer, Pattern, PatternRecognizer
from presidio_analyzer.predefined_recognizers import (
    CreditCardRecognizer,
    UsSsnRecognizer,
)
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider
from presidio_analyzer.recognizer_registry.recognizers_loader_utils import (
    RecognizerConfigurationLoader,
    RecognizerListLoader,
)

# The component root, i.e. the directory that contains the ``presidio_analyzer``
# package. Some shipped entries carry a ``config_path`` that the recognizer
# resolves relative to the current working directory, so the load test below runs
# from here -- the same working directory CI uses -- rather than catching the
# resulting error. Catching it would turn a genuinely missing shipped file into a
# passing skip.
PACKAGE_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_CONF = PACKAGE_ROOT / "presidio_analyzer" / "conf" / "default_recognizers.yaml"

# Parsed once at import. The shipped-configuration tests below are parametrized
# over every entry, so re-reading the file per invocation would parse it a few
# dozen times to retrieve the same keys.
DEFAULT_CONF_DATA = yaml.safe_load(DEFAULT_CONF.read_text(encoding="utf-8"))
GLOBAL_REGEX_FLAGS = DEFAULT_CONF_DATA["global_regex_flags"]


def create_mock_pattern_recognizer(lang, entity, name):
    return PatternRecognizer(
        supported_entity=entity,
        supported_language=lang,
        name=name,
        patterns=[Pattern("pat", regex="REGEX", score=1.0)],
    )


class NoKwargsPlural:
    """Mock class that accepts only supported_entities (plural)."""

    def __init__(self, supported_entities=None):
        pass


class NoKwargsSingular:
    """Mock class that accepts only supported_entity (singular)."""

    def __init__(self, supported_entity=None):
        pass


class VarKwargsOnly:
    """Mock class that accepts only **kwargs."""

    def __init__(self, **kwargs):
        pass


class NoKwargsNone:
    """Mock class that accepts neither supported_entity nor supported_entities."""

    def __init__(self):
        pass


class Uninspectable:
    """Mock class where signature inspection fails."""

    __init__ = 123


class StrictParent:
    """Parent class that accepts only supported_entities (no **kwargs)."""

    def __init__(self, supported_entities=None):
        pass


class ChildForwardsKwargs(StrictParent):
    """Child class that accepts **kwargs and forwards to parent."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


# Helper: partial to avoid passing empty lang_conf every time
prepare = functools.partial(
    RecognizerListLoader._prepare_recognizer_kwargs, language_conf={}
)


def load_recognizers(recognizers, languages=("en",)):
    return list(RecognizerListLoader.get(recognizers, languages, 26))


def test_predefined_score_thresholds_attach_without_mutating_config():
    config = [
        {
            "name": "CreditCardRecognizer",
            "type": "predefined",
            "supported_language": "en",
            "score_thresholds": {"default": 0.4, "CREDIT_CARD": 0.7},
        }
    ]
    original = copy.deepcopy(config)

    recognizers = load_recognizers(config)

    assert recognizers[0].score_thresholds == {
        "default": 0.4,
        "CREDIT_CARD": 0.7,
    }
    assert config == original


def test_custom_multilanguage_score_thresholds_attach_to_each_instance():
    config = [
        {
            "name": "custom_thresholds",
            "type": "custom",
            "supported_entity": "CUSTOM",
            "supported_languages": [{"language": "en"}, {"language": "es"}],
            "patterns": [{"name": "custom", "regex": "x", "score": 0.5}],
            "score_thresholds": {"default": 0.4, "CUSTOM": 0.6},
        }
    ]
    original = copy.deepcopy(config)

    recognizers = load_recognizers(config, ("en", "es"))

    assert {recognizer.supported_language for recognizer in recognizers} == {"en", "es"}
    assert all(
        recognizer.score_thresholds == {"default": 0.4, "CUSTOM": 0.6}
        for recognizer in recognizers
    )
    assert config == original


@pytest.mark.parametrize("score_thresholds", [None, {}])
def test_loader_missing_or_empty_score_thresholds_default_to_empty(score_thresholds):
    config = {
        "name": "CreditCardRecognizer",
        "type": "predefined",
        "supported_language": "en",
    }
    if score_thresholds is not None:
        config["score_thresholds"] = score_thresholds

    recognizer = load_recognizers([config])[0]

    assert recognizer.score_thresholds == {}


def test_loader_explicit_none_score_thresholds_defaults_to_empty():
    recognizer = load_recognizers(
        [
            {
                "name": "CreditCardRecognizer",
                "type": "predefined",
                "supported_language": "en",
                "score_thresholds": None,
            }
        ]
    )[0]

    assert recognizer.score_thresholds == {}


@pytest.mark.parametrize("score_thresholds", [False, 0, "", []])
def test_loader_rejects_falsey_non_mapping_score_thresholds(score_thresholds):
    config = [
        {
            "name": "CreditCardRecognizer",
            "type": "predefined",
            "supported_language": "en",
            "score_thresholds": score_thresholds,
        }
    ]

    with pytest.raises(ValueError, match="must be a mapping"):
        load_recognizers(config)


def test_same_name_and_language_entries_keep_distinct_thresholds_and_ids():
    config = [
        {
            "name": "CreditCardRecognizer",
            "type": "predefined",
            "supported_language": "en",
            "score_thresholds": {"default": threshold},
        }
        for threshold in (0.4, 0.8)
    ]

    recognizers = load_recognizers(config)

    assert [recognizer.score_thresholds for recognizer in recognizers] == [
        {"default": 0.4},
        {"default": 0.8},
    ]
    assert recognizers[0].name == recognizers[1].name
    assert recognizers[0].supported_language == recognizers[1].supported_language
    assert recognizers[0].id != recognizers[1].id


def test_cleanup_none_removes_entity_keys():
    """Test that explicit None values for entity keys are removed."""
    kwargs = prepare(
        recognizer_conf={"supported_entity": None, "supported_entities": None},
        recognizer_cls=NoKwargsNone,
    )
    assert "supported_entity" not in kwargs
    assert "supported_entities" not in kwargs


def test_plural_only_signature_keeps_plural_and_drops_singular():
    """Test that plural kept, singular dropped for plural-only class."""
    kwargs = prepare(
        recognizer_conf={"supported_entities": ["ENT"], "supported_entity": "X"},
        recognizer_cls=NoKwargsPlural,
    )
    assert kwargs["supported_entities"] == ["ENT"]
    assert "supported_entity" not in kwargs


def test_singular_only_signature_converts_plural_to_singular():
    """Test that plural key is converted to singular for singular-only class."""
    kwargs = prepare(
        recognizer_conf={"supported_entities": ["ENT"]}, recognizer_cls=NoKwargsSingular
    )
    assert kwargs["supported_entity"] == "ENT"
    assert "supported_entities" not in kwargs


def test_singular_only_signature_keeps_singular_if_provided():
    """Test that singular key is preserved if provided for singular-only class."""
    kwargs = prepare(
        recognizer_conf={"supported_entity": "ENT_S"}, recognizer_cls=NoKwargsSingular
    )
    assert kwargs["supported_entity"] == "ENT_S"
    assert "supported_entities" not in kwargs


def test_no_kwargs_signature_removes_both():
    """Test that both entity keys are removed if class accepts neither."""
    kwargs = prepare(
        recognizer_conf={"supported_entities": ["ENT"], "supported_entity": "X"},
        recognizer_cls=NoKwargsNone,
    )
    assert "supported_entities" not in kwargs
    assert "supported_entity" not in kwargs


def test_var_kwargs_preserves_plural_but_drops_singular_for_safety():
    """Test that plural is kept (compat) but singular is dropped (safety)."""
    kwargs = prepare(
        recognizer_conf={"supported_entities": ["ENT"], "supported_entity": "X"},
        recognizer_cls=VarKwargsOnly,
    )
    assert kwargs["supported_entities"] == ["ENT"]
    assert "supported_entity" not in kwargs


def test_uninspectable_signature_drops_entity_keys():
    """Test that entity keys are dropped if signature inspection fails."""
    kwargs = prepare(
        recognizer_conf={"supported_entities": ["ENT"], "supported_entity": "X"},
        recognizer_cls=Uninspectable,
    )
    assert "supported_entities" not in kwargs
    assert "supported_entity" not in kwargs


def test_inheritance_forwarding_does_not_crash():
    """Test that inheritance forwarding to strict parent does not crash."""
    # Verify both:
    # 1. dangerous 'supported_entity' (singular) is removed to prevent crash.
    # 2. valid 'supported_entities' (plural) is preserved for compatibility.
    input_kwargs = {"supported_entity": "BAD", "supported_entities": ["ENT"]}
    kwargs = prepare(recognizer_conf=input_kwargs, recognizer_cls=ChildForwardsKwargs)

    # This ensures it doesn't crash when instantiated
    ChildForwardsKwargs(**kwargs)

    assert "supported_entity" not in kwargs
    assert kwargs["supported_entities"] == ["ENT"]


def test_configuration_loader_bad_yaml_raises_value_error(tmp_path):
    """Test that invalid YAML content raises a ValueError."""
    # Create a dummy file with invalid YAML
    f = tmp_path / "bad.yaml"
    f.write_text("invalid: [unclosed_list_without_bracket", encoding="utf-8")

    # Check for the filename part and the error prefix.
    match_pattern = rf"Failed to parse file.*{re.escape(f.name)}"
    with pytest.raises(ValueError, match=match_pattern):
        RecognizerConfigurationLoader.get(conf_file=str(f))


def test_convert_supported_entities_to_entity_uses_first_item():
    """Test that supported_entities list is converted to single supported_entity."""
    conf = {"supported_entities": ["ENT1", "ENT2"]}
    RecognizerListLoader._convert_supported_entities_to_entity(conf)

    assert "supported_entities" not in conf
    assert conf["supported_entity"] == "ENT1"


# ---------------------------------------------------------------------------
# Country filtering and YAML country_code loader utilities
# ---------------------------------------------------------------------------


def test_country_filter_includes_tagged_custom_recognizer():
    """A custom recognizer that opts in via class-level ``COUNTRY_CODE`` is
    included when the filter is loaded with the matching country.
    """
    class _BrCpfRecognizer(PatternRecognizer):
        COUNTRY_CODE = "br"

        def __init__(self):
            super().__init__(
                supported_entity="BR_CPF",
                name="BR CPF Recognizer",
                patterns=[Pattern("p", regex="REGEX", score=1.0)],
            )

    class _XUsRecognizer(PatternRecognizer):
        COUNTRY_CODE = "us"

        def __init__(self):
            super().__init__(
                supported_entity="X_US_THING",
                name="X US Recognizer",
                patterns=[Pattern("p", regex="REGEX", score=1.0)],
            )

    br_recognizer = _BrCpfRecognizer()
    us_recognizer = _XUsRecognizer()
    agnostic = create_mock_pattern_recognizer("en", "AGNOSTIC", "Agnostic")

    filtered = RecognizerListLoader.filter_by_countries(
        [br_recognizer, us_recognizer, agnostic], ["br"]
    )

    assert br_recognizer in filtered
    assert us_recognizer not in filtered
    # Locale-agnostic recognizers always survive the filter.
    assert agnostic in filtered


def test_country_filter_warns_on_unknown_country(caplog):
    """When a requested country has no matching recognizer in the input
    list, a WARNING is logged so silent zero-result filters are easier to
    debug.
    """
    class _XUsRecognizer(PatternRecognizer):
        COUNTRY_CODE = "us"

        def __init__(self):
            super().__init__(
                supported_entity="X_US_THING",
                patterns=[Pattern("p", regex="REGEX", score=1.0)],
            )

    us_recognizer = _XUsRecognizer()

    with caplog.at_level("WARNING", logger="presidio-analyzer"):
        RecognizerListLoader.filter_by_countries([us_recognizer], ["br"])

    warning_messages = [
        r.getMessage() for r in caplog.records if r.levelname == "WARNING"
    ]
    assert any("'br'" in m and "country_code" in m for m in warning_messages), (
        f"expected a country-filter WARNING mentioning 'br' and country_code, "
        f"got {warning_messages!r}"
    )


def test_supported_countries_via_loader_kwarg():
    """``RecognizerListLoader.get(supported_countries=...)`` applies the
    country filter inline alongside the language filter, mirroring how
    ``supported_languages`` is threaded through. This is what allows the
    same filter to be driven from a top-level YAML field with no extra
    plumbing in ``RecognizerRegistry``.
    """
    configuration = RecognizerConfigurationLoader.get(
        registry_configuration={"global_regex_flags": 0}
    )
    recognizers = list(
        RecognizerListLoader.get(**configuration, supported_countries=["us"])
    )
    names = {type(rec).__name__ for rec in recognizers}

    assert "UsSsnRecognizer" in names
    assert "UkNinoRecognizer" not in names
    # Locale-agnostic recognizers survive the filter.
    assert "CreditCardRecognizer" in names


def test_custom_yaml_country_code_flows_through_to_filter(tmp_path):
    """A YAML ``type: custom`` entry with ``country_code:`` is filtered by country.

    End-to-end check: the YAML field flows through
    ``RecognizerListLoader._create_custom_recognizers`` → ``from_dict``
    → ``PatternRecognizer.__init__`` → ``EntityRecognizer.__init__``,
    landing on the instance via ``self._country_code``. The country
    filter then keeps or drops the instance based on the requested set.
    """
    yaml_doc = {
        "supported_languages": ["en"],
        "global_regex_flags": 26,
        "recognizers": [
            {
                "name": "AmNationalIdRecognizer",
                "type": "custom",
                "supported_entity": "AM_NATIONAL_ID",
                "supported_languages": [{"language": "en"}],
                "country_code": "am",
                "patterns": [
                    {"name": "AM 10-digit", "regex": r"\b\d{10}\b", "score": 0.5}
                ],
            }
        ],
    }
    conf_path = tmp_path / "custom_recognizers.yaml"
    conf_path.write_text(yaml.safe_dump(yaml_doc))

    configuration = RecognizerConfigurationLoader.get(conf_file=str(conf_path))
    instances = list(
        RecognizerListLoader.get(**configuration, supported_countries=["am"])
    )

    am = [r for r in instances if getattr(r, "name", None) == "AmNationalIdRecognizer"]
    assert len(am) == 1, (
        "expected the custom AM recognizer to survive the country filter, got "
        f"{[type(r).__name__ for r in instances]}"
    )
    assert am[0].country_code() == "am"

    # The same registry, filtered to a different country, drops it.
    instances_uk = list(
        RecognizerListLoader.get(**configuration, supported_countries=["uk"])
    )
    assert not [
        r for r in instances_uk if getattr(r, "name", None) == "AmNationalIdRecognizer"
    ]


def test_filter_by_countries_rejects_bare_string():
    """A bare ``str`` raises ``TypeError`` rather than silently matching nothing.

    ``countries="us"`` is the most common footgun: it would otherwise
    iterate over characters and match nothing.
    """
    rec = create_mock_pattern_recognizer("en", "FOO", "rec")
    with pytest.raises(TypeError, match="iterable of strings"):
        RecognizerListLoader.filter_by_countries([rec], "us")


def test_filter_by_countries_rejects_non_iterable():
    """Non-iterable scalars raise ``TypeError`` early.

    e.g. ``filter_by_countries([rec], 7)`` rather than failing later
    with an opaque error.
    """
    rec = create_mock_pattern_recognizer("en", "FOO", "rec")
    with pytest.raises(TypeError, match="iterable of strings"):
        RecognizerListLoader.filter_by_countries([rec], 7)


def test_filter_by_countries_rejects_non_string_element():
    """Each element must be a string; ``[1, 2]`` raises ``TypeError``."""
    rec = create_mock_pattern_recognizer("en", "FOO", "rec")
    with pytest.raises(TypeError, match="must be a string"):
        RecognizerListLoader.filter_by_countries([rec], ["us", 2])


def test_filter_by_countries_rejects_blank_element():
    """Empty / whitespace-only codes raise ``ValueError``."""
    rec = create_mock_pattern_recognizer("en", "FOO", "rec")
    with pytest.raises(ValueError, match="non-empty"):
        RecognizerListLoader.filter_by_countries([rec], ["us", " "])


def test_filter_by_countries_normalizes_case_and_whitespace():
    """Whitespace is stripped and codes are lower-cased.

    ``" US "`` matches a ``COUNTRY_CODE = "us"`` recognizer.
    """
    class TaggedRecognizer(PatternRecognizer):
        COUNTRY_CODE = "us"

        def __init__(self):
            super().__init__(
                supported_entity="FOO",
                supported_language="en",
                name="TaggedRecognizer",
                patterns=[Pattern("p", regex="REGEX", score=1.0)],
            )

    tagged = TaggedRecognizer()
    agnostic = create_mock_pattern_recognizer("en", "BAR", "agnostic")

    filtered = RecognizerListLoader.filter_by_countries([tagged, agnostic], ["  US  "])
    names = {type(rec).__name__ for rec in filtered}
    assert "TaggedRecognizer" in names
    # Untagged recognizers are always kept regardless of the filter.
    assert any(getattr(rec, "name", None) == "agnostic" for rec in filtered)


def test_default_recognizers_yaml_country_code_matches_class():
    """Every YAML ``country_code`` matches the class ``COUNTRY_CODE``.

    Sanity check on the shipped ``default_recognizers.yaml``: protects
    against the YAML and the code drifting silently — the loader will
    refuse to load on mismatch.
    """
    declared = [
        r
        for r in DEFAULT_CONF_DATA.get("recognizers", [])
        if isinstance(r, dict) and "country_code" in r
    ]
    assert declared, "expected at least one country_code: entry in YAML"

    for entry in declared:
        name = entry["name"]
        cls = RecognizerListLoader.get_existing_recognizer_cls(recognizer_name=name)
        # Should not raise — declared YAML matches class.
        RecognizerListLoader._validate_yaml_country_code(
            recognizer_conf=entry,
            recognizer_cls=cls,
            recognizer_name=name,
        )


def test_yaml_country_code_mismatch_raises():
    """YAML/class disagreement on ``country_code`` raises ``ValueError``.

    The error names both values so the misconfiguration is fixable from
    the error message alone.
    """
    with pytest.raises(ValueError, match="disagrees with class-level"):
        RecognizerListLoader._validate_yaml_country_code(
            recognizer_conf={"name": "UsSsnRecognizer", "country_code": "uk"},
            recognizer_cls=UsSsnRecognizer,
            recognizer_name="UsSsnRecognizer",
        )


def test_yaml_country_code_on_locale_agnostic_class_raises():
    """YAML ``country_code`` on a class without ``COUNTRY_CODE`` raises.

    The filter has no class-level fact to anchor on. The error message
    points at the fix (set ``COUNTRY_CODE`` on the class, or remove the
    YAML field).
    """
    with pytest.raises(ValueError, match="no ``COUNTRY_CODE`` attribute"):
        RecognizerListLoader._validate_yaml_country_code(
            recognizer_conf={"name": "CreditCardRecognizer", "country_code": "us"},
            recognizer_cls=CreditCardRecognizer,
            recognizer_name="CreditCardRecognizer",
        )


def test_yaml_country_code_blank_value_raises():
    """A blank / non-string YAML ``country_code`` is rejected up-front."""
    with pytest.raises(ValueError, match="non-empty string"):
        RecognizerListLoader._validate_yaml_country_code(
            recognizer_conf={"name": "UsSsnRecognizer", "country_code": "   "},
            recognizer_cls=UsSsnRecognizer,
            recognizer_name="UsSsnRecognizer",
        )


# ---------------------------------------------------------------------------
# Contract between the loader and the predefined recognizers it builds
#
# ``RecognizerListLoader`` builds predefined recognizers from YAML by passing the
# entry's keys as constructor kwargs. That makes the constructor signature part
# of a contract which nothing else enforces: a recognizer can satisfy every one
# of its own unit tests -- which instantiate it directly -- and still be
# impossible to load from a registry configuration.
#
# The gap is specifically in the *disabled* entries. Most of what
# ``default_recognizers.yaml`` ships is ``enabled: false``, and no other test
# constructs those, so a broken constructor stays invisible until a user flips
# the switch. The tests below construct every one of them.
# ---------------------------------------------------------------------------

# Kwargs ``RecognizerListLoader`` passes to every predefined recognizer it
# builds: ``name`` comes from the YAML entry (or its ``class_name`` alias) and
# ``supported_language`` from the resolved per-language configuration.
LOADER_KWARGS = ("name", "supported_language")

# Entries that cannot load from their shipped configuration even with every
# dependency installed, so the load test below cannot cover them. Empty today:
# ``HuggingFaceNerRecognizer`` used to sit here because ``load()`` raised when the
# shipped entry supplied no ``model_name``. It now defers loading instead, so the
# load test covers it like every other entry.
NOT_LOADABLE_FROM_SHIPPED_ENTRY: set[str] = set()

# Entries gated behind an optional dependency, for which refusing to load with an
# actionable ImportError is the intended behavior. The skip is scoped to these
# names rather than to the exception type, so an ImportError from any other entry
# stays a failure instead of a green skip.
OPTIONAL_DEPENDENCY_ENTRIES = {"BasicLangExtractRecognizer"}


def _pattern_recognizer_classes() -> Dict[str, type]:
    """Predefined ``PatternRecognizer`` subclasses, which the YAML loader builds.

    Swept from the package rather than from the YAML, so that a class is checked
    *before* it is listed anywhere. That is the direction the defect actually
    travelled: ``KrPassportRecognizer`` was added in #1814 without ``name`` and
    consequently could not be added to ``default_recognizers.yaml`` at all, so no
    YAML-driven check could ever have named it.

    Non-pattern recognizers (NER/LLM/remote wrappers) are not swept here: several
    are not registrable from ``default_recognizers.yaml`` and some deliberately
    fix their own display name. The ones that *are* listed come back in via
    ``_yaml_listed_classes`` below.
    """
    classes = {}
    for attr in dir(predefined):
        obj = getattr(predefined, attr)
        if not isinstance(obj, type) or not issubclass(obj, EntityRecognizer):
            continue
        if obj in (EntityRecognizer, PatternRecognizer):
            continue
        if issubclass(obj, PatternRecognizer):
            classes[attr] = obj
    return classes


def _yaml_entries() -> List[Dict]:
    """Normalize the shipped recognizer list to dict entries."""
    entries = []
    for entry in DEFAULT_CONF_DATA["recognizers"]:
        entries.append({"name": entry} if isinstance(entry, str) else dict(entry))
    return entries


def _entry_languages(entry: Dict) -> List[str]:
    """Languages an entry declares, in either supported YAML shape."""
    languages = entry.get("supported_languages")
    if not languages:
        return ["en"]
    if isinstance(languages[0], str):
        return list(languages)
    return [item["language"] for item in languages]


def _entry_id(entry: Dict) -> str:
    return entry.get("class_name") or entry["name"]


PATTERN_CLASSES = _pattern_recognizer_classes()
YAML_ENTRIES = _yaml_entries()
LOADABLE_YAML_ENTRIES = [
    entry
    for entry in YAML_ENTRIES
    if _entry_id(entry) not in NOT_LOADABLE_FROM_SHIPPED_ENTRY
]


def _yaml_listed_classes() -> Dict[str, type]:
    """Classes named by a shipped entry, resolved the way the loader resolves them.

    Adds the entries the package sweep skips because they are not
    ``PatternRecognizer`` subclasses -- ``PhoneRecognizer``, the two ``Za*``
    ones, and the NER/LLM wrappers. Being listed is what makes them fair game:
    the loader passes the kwargs to whatever the YAML names, whatever its base
    class.

    Most of these are covered more strongly by the load test below, which
    constructs them outright. The one this reaches that nothing else does is an
    entry in ``NOT_LOADABLE_FROM_SHIPPED_ENTRY``: excluded from the load test and
    not a ``PatternRecognizer``, its constructor would otherwise go unchecked.

    An entry that does not resolve is dropped rather than raised on, so a bad
    entry is reported by ``test_yaml_entry_class_resolves`` as one named failure
    instead of breaking collection for this whole module.
    """
    classes = {}
    for entry in YAML_ENTRIES:
        entry_id = _entry_id(entry)
        try:
            cls = RecognizerListLoader.get_existing_recognizer_cls(
                recognizer_name=entry_id
            )
        except Exception:  # noqa: BLE001 - reported by the resolve test
            continue
        if isinstance(cls, type) and issubclass(cls, EntityRecognizer):
            classes[entry_id] = cls
    return classes


# Every class the loader may be asked to build: swept from the package (catches a
# class before it reaches the YAML) and from the shipped YAML (catches a listed
# class the package sweep skips). Neither source subsumes the other.
LOADER_BUILT_CLASSES = {**PATTERN_CLASSES, **_yaml_listed_classes()}


def test_default_conf_has_entries():
    """Guard the fixtures themselves: an empty parse would pass everything."""
    assert PATTERN_CLASSES, "no predefined PatternRecognizer subclasses found"
    assert YAML_ENTRIES, "no recognizers parsed from default_recognizers.yaml"
    assert LOADER_BUILT_CLASSES.keys() >= PATTERN_CLASSES.keys(), (
        "the YAML-listed classes did not resolve, so the union collapsed to less "
        "than the package sweep alone"
    )


@pytest.mark.parametrize(
    "entry_id",
    sorted(NOT_LOADABLE_FROM_SHIPPED_ENTRY | OPTIONAL_DEPENDENCY_ENTRIES),
)
def test_exclusion_names_a_real_entry(entry_id):
    """An exclusion must still match a shipped entry.

    Keeps the two lists above from rotting: if an entry is renamed, removed, or
    fixed, the stale exclusion fails here instead of silently narrowing
    coverage.
    """
    assert entry_id in {_entry_id(entry) for entry in YAML_ENTRIES}


CONFIG_PATH_ENTRIES = [entry for entry in YAML_ENTRIES if entry.get("config_path")]


@pytest.mark.parametrize("entry", CONFIG_PATH_ENTRIES, ids=_entry_id)
def test_yaml_entry_config_path_points_at_a_shipped_file(entry):
    """A ``config_path`` in a shipped entry must point at a file that ships.

    Asserted directly rather than left to the load test, which skips the entry
    when its optional dependency is absent. A deleted or renamed config file is
    a regression that must fail even in an environment that cannot construct the
    recognizer at all.
    """
    config_path = Path(entry["config_path"])
    resolved = config_path if config_path.is_absolute() else PACKAGE_ROOT / config_path
    assert resolved.is_file(), (
        f"{_entry_id(entry)} declares config_path {entry['config_path']!r}, "
        f"which does not resolve to a file ({resolved})"
    )


@pytest.mark.parametrize("class_name", sorted(LOADER_BUILT_CLASSES))
def test_recognizer_accepts_loader_kwargs(class_name):
    """Constructor must accept every kwarg the YAML loader passes.

    Signature-level on purpose, so it holds for recognizers that cannot be
    constructed in a test at all -- an ML entry needing configuration, or one
    whose dependencies are absent -- which the load test below has to exclude or
    skip. It also catches the defect before the recognizer reaches the YAML: a
    class added without ``name`` passes its own unit tests and only fails once
    someone tries to register it.
    """
    parameters = inspect.signature(LOADER_BUILT_CLASSES[class_name].__init__).parameters
    if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in parameters.values()):
        pytest.skip(
            f"{class_name}.__init__ takes **kwargs, so the signature cannot show "
            f"which kwargs it honors. Reported as a skip rather than a silent "
            f"pass so the gap in coverage stays visible."
        )
    missing = [kwarg for kwarg in LOADER_KWARGS if kwarg not in parameters]
    assert not missing, (
        f"{class_name}.__init__ does not accept {missing}, which "
        f"RecognizerListLoader passes to every predefined recognizer. "
        f"Loading it from a registry YAML raises TypeError."
    )


@pytest.mark.parametrize("entry", YAML_ENTRIES, ids=_entry_id)
def test_yaml_entry_class_resolves(entry):
    """Every shipped entry must name a real recognizer class.

    The resolved object is asserted to be a recognizer class rather than left to
    the lookup raising, so an entry that resolves to some unrelated module
    attribute fails here instead of downstream.
    """
    recognizer_cls = RecognizerListLoader.get_existing_recognizer_cls(
        recognizer_name=_entry_id(entry)
    )
    assert isinstance(recognizer_cls, type) and issubclass(
        recognizer_cls, EntityRecognizer
    ), f"{_entry_id(entry)} resolves to {recognizer_cls!r}, not a recognizer class"


@pytest.mark.parametrize("entry", LOADABLE_YAML_ENTRIES, ids=_entry_id)
def test_yaml_entry_loads_when_enabled(entry, monkeypatch):
    """Every shipped entry must load once ``enabled`` is true.

    ``enabled: false`` is an opt-in switch, not a disclaimer -- an entry that
    cannot be turned on should not be listed.

    Driven through ``RecognizerRegistryProvider`` rather than
    ``RecognizerListLoader.get`` directly, so that the configuration validation
    a real user's entry passes through is covered too: an entry that the loader
    could build but the validator rejects is just as unusable.

    Runs from ``PACKAGE_ROOT`` so that a ``config_path`` the recognizer resolves
    against the working directory behaves as it does in CI. A FileNotFoundError
    is therefore a real missing shipped file and is left to fail.
    """
    entry_id = _entry_id(entry)
    languages = _entry_languages(entry)
    entry = dict(entry, enabled=True)
    monkeypatch.chdir(PACKAGE_ROOT)
    configuration = {
        "global_regex_flags": GLOBAL_REGEX_FLAGS,
        "supported_languages": languages,
        "recognizers": [entry],
    }

    try:
        registry = RecognizerRegistryProvider(
            registry_configuration=configuration
        ).create_recognizer_registry()
    except ImportError as exc:
        if entry_id not in OPTIONAL_DEPENDENCY_ENTRIES:
            raise
        pytest.skip(f"{entry_id} needs an optional dependency: {exc}")

    # Asserted on the class rather than on ``registry.recognizers`` being
    # non-empty: the loader drops a recognizer whose language the registry does
    # not support with a log warning and no exception, so a merely non-empty
    # registry would not prove that *this* entry is what loaded.
    loaded = [type(r).__name__ for r in registry.recognizers]
    assert entry_id in loaded, (
        f"{entry_id} is listed in default_recognizers.yaml but loaded "
        f"nothing for languages {languages} (registry holds {loaded})"
    )


def test_yaml_entry_can_be_renamed_via_class_name():
    """``class_name`` + ``name`` must give the instance the configured name.

    This is the documented reason the loader passes ``name`` at all (see
    ``RecognizerListLoader.get_recognizer_name``), so it is the behavior that
    makes the kwarg contract above load-bearing rather than incidental.
    """
    configuration = {
        "global_regex_flags": 26,
        "supported_languages": ["en"],
        "recognizers": [
            {
                "class_name": "UsSsnRecognizer",
                "name": "MyRenamedSsnRecognizer",
                "supported_languages": ["en"],
                "type": "predefined",
                "country_code": "us",
            }
        ],
    }
    registry = RecognizerRegistryProvider(
        registry_configuration=configuration
    ).create_recognizer_registry()

    assert [r.name for r in registry.recognizers] == ["MyRenamedSsnRecognizer"]
