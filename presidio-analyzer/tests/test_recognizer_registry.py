# ruff: noqa: D103,D205,E501,F841,I001

from pathlib import Path

import pytest
import yaml
import regex as re
from presidio_analyzer import (
    AnalyzerEngine,
    EntityRecognizer,
    Pattern,
    PatternRecognizer,
    RecognizerRegistry,
)
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider
from presidio_analyzer.recognizer_registry.recognizers_loader_utils import (
    RecognizerListLoader,
)
from presidio_analyzer.predefined_recognizers import SpacyRecognizer, UsSsnRecognizer


def create_mock_pattern_recognizer(lang, entity, name):
    return PatternRecognizer(
        supported_entity=entity,
        supported_language=lang,
        name=name,
        patterns=[Pattern("pat", regex="REGEX", score=1.0)],
    )


def create_mock_custom_recognizer(lang, entities, name):
    return EntityRecognizer(
        supported_entities=entities, name=name, supported_language=lang
    )


@pytest.fixture(scope="function")
def mock_recognizer_registry():
    pattern_recognizer1 = create_mock_pattern_recognizer("en", "PERSON", "1")
    pattern_recognizer2 = create_mock_pattern_recognizer("de", "PERSON", "2")
    pattern_recognizer3 = create_mock_pattern_recognizer("de", "ADDRESS", "3")
    pattern_recognizer4 = create_mock_pattern_recognizer("he", "ADDRESS", "4")
    pattern_recognizer5 = create_mock_custom_recognizer(
        "he", ["PERSON", "ADDRESS"], "5"
    )
    return RecognizerRegistry(
        [
            pattern_recognizer1,
            pattern_recognizer2,
            pattern_recognizer3,
            pattern_recognizer4,
            pattern_recognizer5,
        ],
    )


def test_when_get_recognizers_then_all_recognizers_returned(mock_recognizer_registry):
    registry = mock_recognizer_registry
    count_before_loading = len(registry.get_recognizers(language="en", all_fields=True))
    registry.load_predefined_recognizers()
    recognizers = registry.get_recognizers(language="en", all_fields=True)

    # Loading predefined recognizers should add EN recognizers, and the new
    # UuidRecognizer should be among them. Avoid asserting an exact count,
    # since that count changes whenever a recognizer is added or removed.
    assert len(recognizers) > count_before_loading
    assert any(type(rec).__name__ == "UuidRecognizer" for rec in recognizers)


def test_when_get_recognizers_then_return_all_fields(mock_recognizer_registry):
    registry = mock_recognizer_registry
    recognizers = registry.get_recognizers(language="de", all_fields=True)
    assert len(recognizers) == 2


def test_when_get_recognizers_one_language_then_return_one_entity(
    mock_recognizer_registry,
    caplog,
):
    registry = mock_recognizer_registry
    recognizers = registry.get_recognizers(language="de", entities=["PERSON"])
    assert recognizers == [registry.recognizers[1]]
    assert not any(
        "Ignoring unsupported entities" in record.message for record in caplog.records
    )


def test_when_get_recognizers_unsupported_language_then_return(
    mock_recognizer_registry,
):
    with pytest.raises(ValueError):
        registry = mock_recognizer_registry
        registry.get_recognizers(language="brrrr", entities=["PERSON"])


@pytest.mark.parametrize("unsupported_entity", ["UNSUPPORTED_ENTITY", "ADDRESS"])
def test_when_get_recognizers_with_unsupported_entity_then_warn_and_return_supported(
    mock_recognizer_registry,
    caplog,
    unsupported_entity,
):
    registry = mock_recognizer_registry
    with caplog.at_level("WARNING", logger="presidio-analyzer"):
        recognizers = registry.get_recognizers(
            language="en", entities=["PERSON", unsupported_entity]
        )

    assert recognizers == [registry.recognizers[0]]
    warnings = [
        record.message for record in caplog.records if record.levelname == "WARNING"
    ]
    assert len(warnings) == 1
    assert unsupported_entity in warnings[0]
    assert "language : en" in warnings[0]
    assert "deprecated" in warnings[0]
    assert "future version" in warnings[0]
    assert "raise" in warnings[0]
    assert "get_supported_entities" in warnings[0]


@pytest.mark.parametrize("entity", ["ADDRESS", "UNSUPPORTED_ENTITY"])
def test_when_get_recognizers_without_matching_entities_then_raise(
    mock_recognizer_registry,
    entity,
):
    registry = mock_recognizer_registry
    with pytest.raises(ValueError) as err:
        registry.get_recognizers(language="en", entities=[entity])

    assert str(err.value) == "No matching recognizers were found to serve the request."


def test_when_get_recognizers_with_ad_hoc_recognizer_then_no_error(
    mock_recognizer_registry,
    caplog,
):
    registry = mock_recognizer_registry
    ad_hoc_recognizer = create_mock_pattern_recognizer(
        "en", "UNSUPPORTED_ENTITY", "ad hoc"
    )
    recognizers = registry.get_recognizers(
        language="en",
        entities=["UNSUPPORTED_ENTITY"],
        ad_hoc_recognizers=[ad_hoc_recognizer],
    )

    assert recognizers == [ad_hoc_recognizer]
    assert not any(
        "Ignoring unsupported entities" in record.message for record in caplog.records
    )


def test_when_get_recognizers_specific_language_and_entity_then_return_one_result(
    mock_recognizer_registry,
):
    registry = mock_recognizer_registry
    recognizers = registry.get_recognizers(language="he", entities=["PERSON"])
    assert len(recognizers) == 1


def test_when_multiple_entities_from_same_recognizer_only_one_is_returned():
    registry = RecognizerRegistry()

    recognizer_supporting_two_ents = EntityRecognizer(
        supported_entities=["A", "B"], name="MyReco"
    )
    registry.add_recognizer(recognizer_supporting_two_ents)
    recognizers = registry.get_recognizers(
        language="en", entities=["A", "B"], all_fields=False
    )

    assert len(recognizers) == 1
    assert recognizers[0].name == "MyReco"


def test_when_add_pattern_recognizer_then_item_added():
    pattern = Pattern("rocket pattern", r"\W*(rocket)\W*", 0.8)
    pattern_recognizer = PatternRecognizer(
        "ROCKET", name="Rocket recognizer", patterns=[pattern]
    )

    # Create an empty recognizer registry
    recognizer_registry = RecognizerRegistry(recognizers=[])
    assert len(recognizer_registry.recognizers) == 0

    # Add a new recognizer for the word "rocket" (case insensitive)
    recognizer_registry.add_recognizer(pattern_recognizer)

    assert len(recognizer_registry.recognizers) == 1
    assert recognizer_registry.recognizers[0].patterns[0].name == "rocket pattern"
    assert recognizer_registry.recognizers[0].name == "Rocket recognizer"


def test_when_remove_pattern_recognizer_then_item_removed():
    pattern = Pattern("spaceship pattern", r"\W*(spaceship)\W*", 0.8)
    pattern_recognizer = PatternRecognizer(
        "SPACESHIP", name="Spaceship recognizer", patterns=[pattern]
    )
    # Create an empty recognizer registry
    recognizer_registry = RecognizerRegistry(recognizers=[])
    assert len(recognizer_registry.recognizers) == 0

    # Add a new recognizer for the word "rocket" (case insensitive)
    recognizer_registry.add_recognizer(pattern_recognizer)

    # Expects one custom recognizer
    assert len(recognizer_registry.recognizers) == 1

    # Remove recognizer
    recognizer_registry.remove_recognizer("Spaceship recognizer")

    # Expects zero custom recognizers
    assert len(recognizer_registry.recognizers) == 0


def test_add_recognizer_from_dict():
    registry = RecognizerRegistry()
    recognizer = {
        "name": "Zip code Recognizer",
        "supported_language": "de",
        "patterns": [
            {
                "name": "zip code (weak)",
                "regex": "(\\b\\d{5}(?:\\-\\d{4})?\\b)",
                "score": 0.01,
            }
        ],
        "context": ["zip", "code"],
        "supported_entity": "ZIP",
    }
    registry.add_pattern_recognizer_from_dict(recognizer)

    assert len(registry.recognizers) == 1
    assert registry.recognizers[0].name == "Zip code Recognizer"


def test_add_recognizer_from_dict_attaches_thresholds_without_mutating_input(
    monkeypatch,
):
    registry = RecognizerRegistry()
    recognizer = {
        "name": "Zip code Recognizer",
        "supported_language": "de",
        "patterns": [{"name": "zip", "regex": r"\d{5}", "score": 0.5}],
        "supported_entity": "ZIP",
        "score_thresholds": {"default": 0.4, "ZIP": 0.7},
    }
    original = recognizer.copy()
    received = {}
    from_dict = PatternRecognizer.from_dict

    def capture_from_dict(config):
        received.update(config)
        return from_dict(config)

    monkeypatch.setattr(PatternRecognizer, "from_dict", capture_from_dict)

    registry.add_pattern_recognizer_from_dict(recognizer)

    assert "score_thresholds" not in received
    assert recognizer == original
    assert registry.recognizers[0].score_thresholds == {
        "default": 0.4,
        "ZIP": 0.7,
    }


def test_add_recognizers_from_yaml_attaches_thresholds(tmp_path):
    yaml_path = tmp_path / "recognizers.yaml"
    yaml_path.write_text(
        """recognizers:
- name: Zip code Recognizer
  supported_language: de
  supported_entity: ZIP
  patterns:
    - name: zip
      regex: '\\d{5}'
      score: 0.5
  score_thresholds:
    default: 0.4
    ZIP: 0.7
"""
    )
    registry = RecognizerRegistry()

    registry.add_recognizers_from_yaml(yaml_path)

    assert registry.recognizers[0].score_thresholds == {
        "default": 0.4,
        "ZIP": 0.7,
    }


@pytest.mark.parametrize("score_thresholds", [False, 0, "", []])
def test_add_recognizer_from_dict_rejects_falsey_non_mapping_thresholds(
    score_thresholds,
):
    recognizer = {
        "name": "Zip code Recognizer",
        "supported_language": "de",
        "patterns": [{"name": "zip", "regex": r"\d{5}", "score": 0.5}],
        "supported_entity": "ZIP",
        "score_thresholds": score_thresholds,
    }

    with pytest.raises(ValueError, match="must be a mapping"):
        RecognizerRegistry().add_pattern_recognizer_from_dict(recognizer)


def test_recognizer_registry_add_from_yaml_file():
    this_path = Path(__file__).parent.absolute()
    test_yaml = Path(this_path, "conf/recognizers.yaml")

    registry = RecognizerRegistry()
    registry.add_recognizers_from_yaml(test_yaml)

    assert len(registry.recognizers) == 2
    zip_recogizer: PatternRecognizer = registry.get_recognizers(
        language="de", entities=["ZIP"]
    )[0]
    assert zip_recogizer.name == "Zip code Recognizer"
    assert zip_recogizer.supported_language == "de"
    assert zip_recogizer.supported_entities == ["ZIP"]
    assert len(zip_recogizer.patterns) == 1

    titles_recogizer: PatternRecognizer = registry.get_recognizers(
        language="en", entities=["TITLE"]
    )[0]
    assert titles_recogizer.name == "Titles recognizer"
    assert titles_recogizer.supported_language == "en"
    assert titles_recogizer.supported_entities == ["TITLE"]
    assert len(titles_recogizer.patterns) == 1  # deny-list turns into a pattern
    assert len(titles_recogizer.deny_list) == 6


def test_recognizer_registry_exception_missing_yaml_file():
    test_yaml = Path("missing.yaml")
    with pytest.raises(IOError):
        registry = RecognizerRegistry()
        registry.add_recognizers_from_yaml(test_yaml)


def test_recognizer_registry_exception_erroneous_yaml():
    this_path = Path(__file__).parent.absolute()
    test_yaml = Path(this_path, "conf/recognizers_error.yaml")

    with pytest.raises(TypeError):
        registry = RecognizerRegistry()
        registry.add_recognizers_from_yaml(test_yaml)


def test_predefined_pattern_recognizers_have_the_right_regex_flags():
    registry = RecognizerRegistry(global_regex_flags=re.DOTALL)
    registry.load_predefined_recognizers()
    for rec in registry.recognizers:
        if isinstance(rec, PatternRecognizer):
            assert rec.global_regex_flags == re.DOTALL


def test_recognizer_removed_and_returned_entities_are_correct():
    registry = RecognizerRegistry()
    registry.load_predefined_recognizers()
    registry.remove_recognizer("SpacyRecognizer")
    sr = SpacyRecognizer(supported_entities=["DATE_TIME", "NRP"])
    registry.add_recognizer(sr)

    supported_entities = registry.get_supported_entities(languages=["en"])

    assert "DATE_TIME" in supported_entities
    assert "PERSON" not in supported_entities

    analyzer = AnalyzerEngine(registry=registry, supported_languages=["en"])

    analyzer.analyze("My name is David", language="en")


def test_remove_recognizer_when_multiple_instances_exist():
    registry = RecognizerRegistry()

    spacy_english = SpacyRecognizer(supported_language="en")
    spacy_spanish = SpacyRecognizer(supported_language="es")
    registry.add_recognizer(spacy_english)
    registry.add_recognizer(spacy_spanish)

    registry.remove_recognizer("SpacyRecognizer", language="en")
    assert len(registry.recognizers) == 1

    assert registry.recognizers[0].supported_language == "es"
    assert len([rec for rec in registry.recognizers
                if rec.name == "SpacyRecognizer"]) == 1


# ---------------------------------------------------------------------------
# Country filter (load_predefined_recognizers(countries=...)) — fixes #1328
# ---------------------------------------------------------------------------


def _recognizer_class_names(registry):
    return {type(rec).__name__ for rec in registry.recognizers}


def test_load_predefined_recognizers_without_country_filter_loads_all():
    """Default behavior must be unchanged when `countries` is omitted."""
    baseline = RecognizerRegistry()
    baseline.load_predefined_recognizers()

    explicit_none = RecognizerRegistry()
    explicit_none.load_predefined_recognizers(countries=None)

    assert _recognizer_class_names(baseline) == _recognizer_class_names(explicit_none)


def test_load_predefined_recognizers_filters_to_requested_countries():
    """Only recognizers from the requested countries plus country-agnostic
    recognizers (generic, NER, NLP engine, third-party) should be loaded.
    """
    registry = RecognizerRegistry()
    registry.load_predefined_recognizers(countries=["us"])
    names = _recognizer_class_names(registry)

    # A US recognizer is present.
    assert "UsSsnRecognizer" in names
    # A non-US country recognizer is absent.
    assert "UkNinoRecognizer" not in names
    assert "NhsRecognizer" not in names
    # Country-agnostic recognizers are still present.
    assert "CreditCardRecognizer" in names
    assert "EmailRecognizer" in names


def test_load_predefined_recognizers_country_filter_is_case_insensitive():
    registry_lower = RecognizerRegistry()
    registry_lower.load_predefined_recognizers(countries=["us"])

    registry_upper = RecognizerRegistry()
    registry_upper.load_predefined_recognizers(countries=["US"])

    assert _recognizer_class_names(registry_lower) == _recognizer_class_names(
        registry_upper
    )


def test_load_predefined_recognizers_empty_countries_keeps_only_agnostic():
    """Passing an empty list drops every country-specific recognizer but keeps
    generic ones.
    """
    registry = RecognizerRegistry()
    registry.load_predefined_recognizers(countries=[])
    names = _recognizer_class_names(registry)

    assert "UsSsnRecognizer" not in names
    assert "UkNinoRecognizer" not in names
    assert "NhsRecognizer" not in names
    # Country-agnostic recognizers remain.
    assert "CreditCardRecognizer" in names
    assert "EmailRecognizer" in names


def test_load_predefined_recognizers_multiple_countries():
    registry = RecognizerRegistry()
    registry.load_predefined_recognizers(countries=["us", "uk"])
    names = _recognizer_class_names(registry)

    assert "UsSsnRecognizer" in names
    assert "NhsRecognizer" in names  # UK National Health Service
    # Germany should be excluded.
    assert not any(n.startswith("De") for n in names if n != "DateRecognizer")


# ---------------------------------------------------------------------------
# COUNTRY_CODE class attribute on EntityRecognizer + filter integration — #1328
# ---------------------------------------------------------------------------


def test_entity_recognizer_country_code_default_is_none():
    """A recognizer class with no ``COUNTRY_CODE`` declared is locale-agnostic
    via the inherited default on ``EntityRecognizer``.
    """
    rec = create_mock_pattern_recognizer("en", "FOO", "rec")
    assert rec.country_code() is None
    assert rec.is_country_specific() is False


def test_country_code_lowercases_class_attribute():
    """``country_code()`` normalizes the class-level ``COUNTRY_CODE`` to lowercase.

    The filter's case-insensitive contract is enforced at the source of
    truth, regardless of how the subclass spells its ``COUNTRY_CODE``.
    """

    class _UpperCased(PatternRecognizer):
        COUNTRY_CODE = "DE"

        def __init__(self):
            super().__init__(
                supported_entity="X",
                patterns=[Pattern("p", "REGEX", 1.0)],
            )

    rec = _UpperCased()
    assert rec.country_code() == "de"
    assert rec.is_country_specific() is True


def test_predefined_country_specific_recognizer_carries_class_country_code():
    """Predefined country recognizers expose their class-level ``COUNTRY_CODE``.

    The country tag is reconciled at construction time and surfaced via
    the instance's ``country_code()`` method; the ClassVar itself remains
    accessible for class-level introspection without instantiating.
    """
    # ClassVar accessible without instantiation (the no-instantiation
    # introspection path is via the attribute, not the method).
    assert UsSsnRecognizer.COUNTRY_CODE == "us"

    # Instance method returns the resolved tag.
    rec = UsSsnRecognizer()
    assert rec.country_code() == "us"
    assert rec.is_country_specific() is True


def test_country_code_class_attribute_is_authoritative_over_instance_attr():
    """Mutating ``rec.COUNTRY_CODE`` after construction does not change the tag.

    Country resolution happens once in ``__init__`` (via
    ``_resolve_country_code``) and the resolved value is cached as
    ``self._country_code``. Re-assigning the class attribute on an
    instance after the fact is intentionally a no-op for ``country_code()``
    so the country tag stays consistent for the lifetime of the recognizer.
    """
    rec = UsSsnRecognizer()
    rec.COUNTRY_CODE = "ca"  # noqa: B010 — exercising the contract
    assert rec.country_code() == "us"


def test_country_filter_keeps_untagged_custom_recognizer():
    """An untagged custom recognizer (no ``COUNTRY_CODE`` declared) is the
    "I haven't opted in" case and must always be kept regardless of the
    requested countries — this is what makes the migration backwards
    compatible.
    """
    custom = create_mock_pattern_recognizer("en", "MY_THING", "Custom")
    assert custom.country_code() is None

    registry = RecognizerRegistry()
    registry.load_predefined_recognizers(countries=["us"])
    registry.add_recognizer(custom)

    assert custom in registry.recognizers


def test_get_country_codes_returns_loaded_countries():
    """``RecognizerRegistry.get_country_codes()`` aggregates the
    class-level ``COUNTRY_CODE`` across all loaded recognizers.

    The default registry is English-only and many predefined country
    recognizers are either disabled by default or scoped to non-English
    languages, so we assert the subset that actually loads: US and UK
    recognizers are enabled-by-default and English-language.
    """
    registry = RecognizerRegistry()
    registry.load_predefined_recognizers()

    codes = registry.get_country_codes()
    assert isinstance(codes, list)
    assert codes == sorted(codes), "country codes should be returned sorted"
    assert "us" in codes
    assert "uk" in codes
    # Every code returned is non-empty and lowercased (the contract).
    assert all(isinstance(c, str) and c == c.lower() and c for c in codes)


def test_get_country_codes_after_country_filter():
    """``get_country_codes()`` reflects the country filter applied at load."""
    registry = RecognizerRegistry()
    registry.load_predefined_recognizers(countries=["us"])

    assert registry.get_country_codes() == ["us"]


def test_get_country_codes_excludes_locale_agnostic_recognizers():
    """Filter out locale-agnostic recognizers from the country code report.

    Recognizers without a ``COUNTRY_CODE`` are never reported by
    ``get_country_codes`` even though they are present in the registry.
    """
    agnostic = create_mock_pattern_recognizer("en", "FOO", "Agnostic")
    assert agnostic.country_code() is None

    registry = RecognizerRegistry()
    registry.add_recognizer(agnostic)

    assert registry.get_country_codes() == []


def test_to_dict_omits_country_code_when_unset():
    """``to_dict`` only emits ``country_code`` when the recognizer has a tag.

    Locale-agnostic recognizers (no class ``COUNTRY_CODE``, no constructor
    kwarg) keep ``country_code`` out of the serialized payload so the
    dict stays minimal and round-trips losslessly.
    """
    rec = create_mock_pattern_recognizer("en", "FOO", "rec")
    assert rec.country_code() is None
    assert "country_code" not in rec.to_dict()


def test_to_dict_emits_class_level_country_code():
    """``to_dict`` surfaces the resolved tag for a predefined country class.

    The serialized form includes ``country_code`` even though the tag
    came from the class-level ``COUNTRY_CODE`` ClassVar, so a generic
    consumer of the dict (e.g. logs, audit trails) doesn't need to know
    which path the tag came from.
    """
    rec = UsSsnRecognizer()
    assert rec.to_dict().get("country_code") == "us"


# ---------------------------------------------------------------------------
# Constructor ``country_code=`` kwarg — the path for custom recognizers
# without a subclass (Issue #2000 review). Reconciliation matrix:
#
#   ClassVar          | kwarg            | result
#   ------------------+------------------+-----------------------------
#   None              | None             | self._country_code = None
#   None              | "am"             | self._country_code = "am" (NEW)
#   "us"              | None             | self._country_code = "us"
#   "us"              | "us" (matches)   | self._country_code = "us"
#   "us"              | "uk" (conflict)  | ValueError
# ---------------------------------------------------------------------------


def test_constructor_country_code_tags_locale_agnostic_class():
    """``country_code=`` on a class without ``COUNTRY_CODE`` tags the instance.

    This is the new capability: a custom recognizer (no subclass with a
    ClassVar) can now declare a country at construction time, which means
    YAML ``type: custom`` entries with ``country_code:`` flow through
    ``from_dict`` and tag the resulting instance.
    """
    rec = PatternRecognizer(
        supported_entity="AM_ID",
        patterns=[Pattern("p", regex="REGEX", score=1.0)],
        country_code="am",
    )
    assert rec.country_code() == "am"
    assert rec.is_country_specific() is True


def test_constructor_country_code_normalizes_case_and_whitespace():
    """``country_code=" AM "`` is stored as ``"am"``."""
    rec = PatternRecognizer(
        supported_entity="AM_ID",
        patterns=[Pattern("p", regex="REGEX", score=1.0)],
        country_code="  AM  ",
    )
    assert rec.country_code() == "am"


def test_constructor_country_code_rejects_blank():
    """Blank / whitespace-only ``country_code`` raises ``ValueError``."""
    with pytest.raises(ValueError, match="non-empty"):
        PatternRecognizer(
            supported_entity="AM_ID",
            patterns=[Pattern("p", regex="REGEX", score=1.0)],
            country_code="   ",
        )


def test_constructor_country_code_rejects_non_string():
    """Non-string ``country_code`` raises ``TypeError``."""
    with pytest.raises(TypeError, match="must be a string"):
        PatternRecognizer(
            supported_entity="AM_ID",
            patterns=[Pattern("p", regex="REGEX", score=1.0)],
            country_code=42,
        )


def test_constructor_country_code_matches_class_level_is_fine():
    """Passing the same value as ``COUNTRY_CODE`` is redundant but harmless.

    Useful for callers that want to be explicit about the country at
    every layer (e.g. test helpers, generated code) without colliding
    with the class declaration.
    """
    rec = UsSsnRecognizer.__new__(UsSsnRecognizer)
    EntityRecognizer.__init__(
        rec,
        supported_entities=["US_SSN"],
        country_code="us",
    )
    assert rec.country_code() == "us"


def test_constructor_country_code_conflicts_with_class_level_raises():
    """Passing a value that disagrees with ``COUNTRY_CODE`` raises ``ValueError``.

    A predefined Polish-tax-ID recognizer can never be silently re-tagged
    as British via the constructor; the class-level declaration wins and
    misconfiguration fails loudly with both values in the message.
    """
    with pytest.raises(ValueError, match="conflicts with class-level"):
        rec = UsSsnRecognizer.__new__(UsSsnRecognizer)
        EntityRecognizer.__init__(
            rec,
            supported_entities=["US_SSN"],
            country_code="uk",
        )


def test_constructor_country_code_match_is_case_insensitive():
    """Match-check between kwarg and ``COUNTRY_CODE`` is case-insensitive."""
    rec = UsSsnRecognizer.__new__(UsSsnRecognizer)
    EntityRecognizer.__init__(
        rec,
        supported_entities=["US_SSN"],
        country_code="US",
    )
    assert rec.country_code() == "us"


def test_pattern_recognizer_from_dict_roundtrip_preserves_country_code():
    """``from_dict(to_dict(rec))`` round-trips a constructor-tagged recognizer.

    Round-tripping is what makes the YAML ``type: custom`` path useful:
    the loader serializes/reconstructs the dict at various points, and
    losing the tag mid-flight would silently drop custom recognizers
    from the country filter.
    """
    rec = PatternRecognizer(
        supported_entity="AM_ID",
        patterns=[Pattern("AM ID", regex=r"\b\d{10}\b", score=0.5)],
        country_code="am",
    )

    serialized = rec.to_dict()
    assert serialized["country_code"] == "am"

    restored = PatternRecognizer.from_dict(serialized)
    assert restored.country_code() == "am"
    assert restored.supported_entities == rec.supported_entities


# ---------------------------------------------------------------------------
# Input validation for ``countries=`` / ``supported_countries=``
# ---------------------------------------------------------------------------


def test_load_predefined_recognizers_validates_countries_input():
    """Validation is enforced end-to-end through the public entry point.

    ``RecognizerRegistry.load_predefined_recognizers(countries="us")``
    raises ``TypeError`` rather than silently loading nothing.
    """
    registry = RecognizerRegistry()
    with pytest.raises(TypeError, match="iterable of strings"):
        registry.load_predefined_recognizers(countries="us")


# ---------------------------------------------------------------------------
# YAML ``country_code`` cross-validation
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Newly registered pattern recognizers are enable-safe
# ---------------------------------------------------------------------------


def test_when_newly_registered_yaml_recognizers_enabled_then_they_load(tmp_path):
    """AbaRouting, FiPersonalIdentityCode and SgUen were exported in code but
    missing from ``default_recognizers.yaml``; their entries ship
    ``enabled: false``, so this flips them on and asserts they instantiate."""
    conf_path = (
        Path(__file__).parent.parent
        / "presidio_analyzer"
        / "conf"
        / "default_recognizers.yaml"
    )
    conf = yaml.safe_load(conf_path.read_text())
    targets = {
        "AbaRoutingRecognizer",
        "FiPersonalIdentityCodeRecognizer",
        "SgUenRecognizer",
    }
    conf["supported_languages"] = ["en", "fi"]
    for recognizer_conf in conf["recognizers"]:
        if recognizer_conf["name"] in targets:
            recognizer_conf["enabled"] = True
    enabled_conf = tmp_path / "enabled.yaml"
    enabled_conf.write_text(yaml.safe_dump(conf))

    registry = RecognizerRegistryProvider(
        conf_file=str(enabled_conf)
    ).create_recognizer_registry()

    assert targets <= _recognizer_class_names(registry)


# ---------------------------------------------------------------------------
# ``default_recognizers.yaml`` hygiene
# ---------------------------------------------------------------------------


def _default_recognizers_conf():
    conf_path = (
        Path(__file__).parent.parent
        / "presidio_analyzer"
        / "conf"
        / "default_recognizers.yaml"
    )
    return yaml.safe_load(conf_path.read_text())


def _entry_name(entry):
    """Return the instance name an entry declares.

    ``RecognizerListLoader.get_recognizer_name`` answers a different question:
    it resolves the *class* to instantiate and so prefers ``class_name``. That
    makes it the wrong key for the duplicate check below, where two entries may
    legitimately share a class as long as ``name`` tells the instances apart.
    It is still the right fallback for a bare-string entry such as
    ``- SpacyRecognizer`` and for a dict that names only a class, because there
    the class name is also the instance name.
    """
    if isinstance(entry, dict) and entry.get("name"):
        return entry["name"]
    return RecognizerListLoader.get_recognizer_name(entry)


def _declared_languages(entry):
    """Return every language code an entry declares, in all the loader's shapes.

    ``RecognizerListLoader._get_recognizer_languages`` reads
    ``supported_languages`` three ways: absent or ``None``, in which case one
    recognizer is built per registry language and the entry declares no code of
    its own; a list of plain codes; or a list of
    ``{"language": ..., "context": ...}`` mappings. A bare-string entry carries
    no configuration at all and falls into the first case. Only the second and
    third declare anything for this test to check.
    """
    if isinstance(entry, str):
        return []
    languages = entry.get("supported_languages")
    if not languages:
        return []
    return [
        language if isinstance(language, str) else language["language"]
        for language in languages
    ]


def test_default_recognizers_yaml_has_no_duplicate_entries():
    """A name listed twice is instantiated twice.

    ``UkPostcodeRecognizer`` was added by #1858 and again by #1857, which
    merged later, so the file carried two identical blocks and the registry
    built two identical recognizers. Results happen to dedupe downstream, so
    nothing looked wrong from the outside while the regexes ran twice.

    Worse, construction is per entry but removal is per class:
    ``RecognizerRegistryProvider.__remove_disabled_nlp_recognizers`` resolves
    the not-enabled entries to classes and drops every instance of those
    classes, so enabling one of a same-class pair and leaving the other
    disabled builds the recognizer and then silently removes it again.

    Keyed on the instance name rather than the class, deliberately: two entries
    of the same class are legitimate as long as ``class_name`` carries the class
    and ``name`` distinguishes the instances. What the shipped file must not
    carry is the same name twice.
    """
    names = [_entry_name(entry) for entry in _default_recognizers_conf()["recognizers"]]
    duplicates = sorted({name for name in names if names.count(name) > 1})

    assert duplicates == [], f"duplicate recognizer entries: {duplicates}"


def test_default_recognizers_yaml_declares_languages_not_countries():
    """``supported_languages`` holds language codes; ``country_code`` holds the country.

    The Korean entries listed ``kr`` — the ISO 3166-1 country code — next to
    ``ko``, the ISO 639-1 language code. The loader builds one recognizer per
    listed language, so on a registry that does not name ``kr`` every such
    instance is built and then dropped by
    ``RecognizerListLoader._is_language_supported_globally``, one warning
    apiece, on every registry build.

    ``ConfigurationValidator.validate_language_codes`` does not catch this:
    ``kr`` is a well-formed two-letter code, just not the right one.
    """
    # ISO 639-1 codes the shipped recognizers are written against. Adding one
    # here should be a deliberate decision, not a side effect of a new entry.
    known_languages = {"de", "en", "es", "fi", "fr", "it", "ko", "pl", "sv", "th", "tr"}

    # ``kr`` survives on these two entries as a backward-compatibility alias,
    # not as a language. Both classes defaulted to ``supported_language="kr"``
    # until it was moved to ``ko`` — #1742 (2025-10-08) for the RRN, #2170
    # (2026-08-05) for the passport — so a registry still configured with the
    # old code would go quiet if the alias were dropped now. The three sibling
    # ``Kr*`` recognizers never had a ``kr`` default and carry no such
    # allowance.
    #
    # Deprecated in favour of ``ko`` and scheduled for removal in
    # <release TBD>. Delete these two entries in the same change.
    deprecated_language_aliases = {
        "KrRrnRecognizer": {"kr"},
        "KrPassportRecognizer": {"kr"},
    }

    offenders = {}
    for entry in _default_recognizers_conf()["recognizers"]:
        name = _entry_name(entry)
        allowed = known_languages | deprecated_language_aliases.get(name, set())
        for code in _declared_languages(entry):
            if code not in allowed:
                offenders.setdefault(name, []).append(code)

    assert offenders == {}, f"non-language codes in supported_languages: {offenders}"


def test_deprecated_kr_alias_still_loads_its_recognizers():
    """The retained ``kr`` alias has to actually serve a registry that names it.

    This is the configuration the carve-out above exists for. With
    ``supported_languages: ["kr"]`` the loader builds one instance per declared
    language and ``_is_language_supported_globally`` then drops every instance
    whose language the registry does not list, so only the entries that still
    declare ``kr`` survive. Drop the alias and this registry loads nothing —
    which is the breakage the deprecation is being staged to avoid.
    """
    korean_entries = [
        entry
        for entry in _default_recognizers_conf()["recognizers"]
        if _entry_name(entry).startswith("Kr")
    ]
    assert {"KrRrnRecognizer", "KrPassportRecognizer"} <= {
        _entry_name(entry) for entry in korean_entries
    }, "the two alias entries are missing from the shipped file"

    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["kr"],
            "recognizers": [dict(entry, enabled=True) for entry in korean_entries],
        }
    ).create_recognizer_registry()

    assert _recognizer_class_names(registry) == {
        "KrRrnRecognizer",
        "KrPassportRecognizer",
    }
    # The three entries that only declare ``ko`` are built and then dropped,
    # so nothing survives under a language the registry never asked for.
    assert {rec.supported_language for rec in registry.recognizers} == {"kr"}
