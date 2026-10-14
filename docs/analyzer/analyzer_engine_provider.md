# Configuring the Analyzer Engine from file

Presidio uses `AnalyzerEngineProvider` to load `AnalyzerEngine` configuration from file. 
Configuration can be loaded in three different ways:

## Using a single file

Create an `AnalyzerEngineProvider` using a single configuration file and set its path to `analyzer_engine_conf_file`, then create `AnalyzerEngine` based on it:

```python
from presidio_analyzer import AnalyzerEngine, AnalyzerEngineProvider

analyzer_conf_file = "./analyzer/analyzer-config-all.yml"

provider = AnalyzerEngineProvider(
    analyzer_engine_conf_file=analyzer_conf_file
    )
analyzer = provider.create_engine()

results = analyzer.analyze(text="My name is Morris", language="en")
print(results)
```

An example configuration file:

```yaml
supported_languages: 
- en
default_score_threshold: 0

nlp_configuration:
  nlp_engine_name: spacy
  models:
  -
    lang_code: en
    model_name: en_core_web_lg
  -
    lang_code: es
    model_name: es_core_news_md
  ner_model_configuration:
    model_to_presidio_entity_mapping:
      PER: PERSON
      PERSON: PERSON
      LOC: LOCATION
      LOCATION: LOCATION
      GPE: LOCATION
      ORG: ORGANIZATION
      DATE: DATE_TIME
      TIME: DATE_TIME
      NORP: NRP

    low_confidence_score_multiplier: 0.4
    low_score_entity_names:
    - ORGANIZATION
    - ORG
    default_score: 0.85

recognizer_registry:
  global_regex_flags: 26
  recognizers: 
  - name: CreditCardRecognizer
    supported_languages: 
      - en
    supported_entity: IT_FISCAL_CODE
    type: predefined
    score_thresholds:
      default: 0.4
      CREDIT_CARD: 0.7

  - name: ItFiscalCodeRecognizer
    type: predefined
```

The configuration file contains the following parameters:

- `supported_languages`: A list of supported languages that the analyzer will support.
- `default_score_threshold`: A score that determines the minimal threshold for detection.
- `nlp_configuration`: Configuration given to the NLP engine which will detect the PIIs and extract features for the downstream logic.
- `recognizer_registry`: All the recognizers that will be used by the analyzer. Each recognizer entry can define `score_thresholds`, using `default` as its fallback and entity names for overrides.

!!! note "Defining confidence thresholds"
    Presidio supports multiple types of score thresholds: default ones (for the analyzer and each recognizer), per-request thresholds, and per-entity thresholds. Supplying `analyzer.analyze(score_threshold=...)` bypasses recognizer-level thresholds for that request and applies the supplied threshold to every result. The order of importance is: `analyzer.analyze(score_threshold=...)` > an entity specific threshold > a recognizer default threshold (`default`) > the Presidio Analyzer `default_score_threshold`.

!!! note "Note"

    `supported_languages` must be identical to the same field in recognizer_registry

## Using multiple files

Create an `AnalyzerEngineProvider` using three different configuration files for each of the following components:

  - Analyzer
  - NLP Engine
  - Recognizer Registry

!!! note "Note"

    Each of these parameters is optional and in case it's not set, the default configuration will be used. 


```python
from presidio_analyzer import AnalyzerEngine, AnalyzerEngineProvider

analyzer_conf_file = "./analyzer/analyzer-config.yml"
nlp_engine_conf_file = "./analyzer/nlp-config.yml"
recognizer_registry_conf_file = "./analyzer/recognizers-config.yml"

provider = AnalyzerEngineProvider(
    analyzer_engine_conf_file=analyzer_conf_file,
    nlp_engine_conf_file=nlp_engine_conf_file,
    recognizer_registry_conf_file=recognizer_registry_conf_file,
    )
analyzer = provider.create_engine()

results = analyzer.analyze(text="My name is Morris", language="en")
print(results)
```

The structure of the configuration files is as follows:

- Analyzer engine configuration file:

    ```yaml
    supported_languages: 
    - en
    default_score_threshold: 0
    ```

- NLP engine configuration file structure is examined thoroughly in the [Customizing the NLP model](customizing_nlp_models.md) section.

- Recognizer registry configuration file structure is examined thoroughly in the [Customizing recognizer registry from file](recognizer_registry_provider.md) section.

## Using the default configuration

Create an `AnalyzerEngineProvider` without any parameters. This will load the default configuration:

```python
from presidio_analyzer import AnalyzerEngine, AnalyzerEngineProvider

provider = AnalyzerEngineProvider().create_engine()

results = provider.analyze(text="My name is Morris", language="en")
print(results)
```

The default configuration of `AnalyzerEngine` is defined in the following files: 

  -  [Analyzer Engine](https://github.com/data-privacy-stack/presidio/blob/main/presidio-analyzer/presidio_analyzer/conf/default_analyzer.yaml)
  -  [NLP Engine](https://github.com/data-privacy-stack/presidio/blob/main/presidio-analyzer/presidio_analyzer/conf/default.yaml)
  -  [Recognizer Registry](https://github.com/data-privacy-stack/presidio/blob/main/presidio-analyzer/presidio_analyzer/conf/default_recognizers.yaml)

## Enabling and disabling recognizers
In general, recognizers that are not added to the configuration would not be created, with one exception.

### Enabling/Disabling the NLP recognizer
One exception to this is the recognizer which extracts the `NlpEngine` entities (e.g. `SpacyRecognizer` when the `NlpEngine` is `SpacyNlpEngine`; `TransformersRecognizer` when the engine is `TransformersNlpEngine` and `StanzaRecognizer` when the engine is `StanzaNlpEngine`). 

Recognizers (including the NLP recognizer) could be disabled by defining `enabled=false` in the YAML configuration. For example:
```yaml
recognizer_registry:
  global_regex_flags: 26
  recognizers:
    - name: SpacyRecognizer
      type: predefined
      enabled: false
    - name: CreditCardRecognizer
      type: predefined
      enabled: true

supported_languages:
  - en
default_score_threshold: 0.7

nlp_configuration:
  nlp_engine_name: spacy
  models:
    -
      lang_code: en
      model_name: en_core_web_lg
```

In this example, the `SpacyRecognizer` is disabled, and the `CreditCardRecognizer` is enabled, resulting in only the `CREDIT_CARD` PII entity to be returned if detected.

### Adding context words in YAML recognizers

Recognizers defined in YAML can also include a `context` field.  
When used with `AnalyzerEngine` and a context enhancer, these words boost the score if they appear near the detected entity.

Example:

```yaml
recognizers:
  - name: "Date of Birth Recognizer"
    supported_entity: "DATE_TIME"
    supported_language: "en"
    patterns:
      - name: "DOB without slashes"
        regex: "((19|20)\\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\\d|3[01]))"
        score: 0.8
    context:
      - DOB
```
```python
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_analyzer.context_aware_enhancers.lemma_context_aware_enhancer import LemmaContextAwareEnhancer

# Save the DOB recognizer YAML to disk
dob_yaml = """
recognizers:
  - name: "Date of Birth Recognizer"
    supported_entity: "DATE_TIME"
    supported_language: "en"
    patterns:
      - name: "DOB without slashes"
        regex: "((19|20)\\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\\d|3[01]))"
        score: 0.8
    context:
      - DOB
"""
with open("dob_recognizer.yml", "w") as f:
    f.write(dob_yaml)

# Configure NLP engine
configuration = {
    "nlp_engine_name": "spacy",
    "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
}
provider = NlpEngineProvider(nlp_configuration=configuration)
nlp_engine = provider.create_engine()

# Load recognizer from YAML
registry = RecognizerRegistry()
registry.add_recognizers_from_yaml("dob_recognizer.yml")

# Analyzer with custom registry
analyzer = AnalyzerEngine(
    registry=registry,
    nlp_engine=nlp_engine,
    supported_languages=["en"]
)

text = "DOB: 19571012"

# Run base analysis
results = analyzer.analyze(text=text, language="en")
print("Base results:", results)

# Apply context enhancer
enhancer = LemmaContextAwareEnhancer()
nlp_artifacts = analyzer.nlp_engine.process_text(text, language="en")

boosted = enhancer.enhance_using_context(
    text=text,
    raw_results=results,
    nlp_artifacts=nlp_artifacts,
    recognizers=registry.recognizers,
    context=["DOB"]
)
print("Boosted results:", boosted)
```
