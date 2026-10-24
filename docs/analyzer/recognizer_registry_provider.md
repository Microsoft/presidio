# Customizing recognizer registry from file
To load recognizers from file, use `RecognizerRegistryProvider` to instantiate the recognizer registry and then pass it through to the analyzer engine:

```python
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

recognizer_registry_conf_file = "./analyzer/recognizers-config.yml"

provider = RecognizerRegistryProvider(
                conf_file=recognizer_registry_conf_file
            )
registry = provider.create_recognizer_registry()
analyzer = AnalyzerEngine(registry=registry)

results = analyzer.analyze(text="My name is Morris", language="en")
print(results)
```

## Configuration file structure

```yaml
global_regex_flags: 26

supported_languages: 
  - en

recognizers: 
...
```

The configuration file consists of two parts:

  - `global_regex_flags`: regex flags to be used in regex matching (see [regex flags](https://docs.python.org/3/library/re.html#flags)).
  - `supported_languages`: A list of supported languages that the registry will support.
  - `recognizers`: a list of recognizers to be loaded by the recognizer registry. This list consists of two different types of recognizers: 
    - Predefined: A set of already defined recognizer classes in presidio. This includes all recognizers defined in the codebase (along with user defined recognizers) that inherit from EntityRecognizer.
    - Custom: custom created pattern recognizers that are created based on the fields provided in the configuration file.

!!! note "Note"

    supported_languages must be identical to the same field in analyzer_engine

## Recognizer list

The recognizer list comprises of both the predefined and custom recognizers, for example: 

```yaml
...
  - name: CreditCardRecognizer
    supported_languages:
    - language: en
      context: [credit, card, visa, mastercard, cc, amex, discover, jcb, diners, maestro, instapayment]
    - language: es
      context: [tarjeta, credito, visa, mastercard, cc, amex, discover, jcb, diners, maestro, instapayment]
    - language: it
    - language: pl
    type: predefined
    score_thresholds:
      default: 0.4
      CREDIT_CARD: 0.7

  - name: UsBankRecognizer
    supported_languages: 
    - en
    type: predefined

  - name: MedicalLicenseRecognizer
    type: predefined

  - name: ExampleCustomRecognizer
    patterns:
    - name: "zip code (weak)"
      regex: "(\\b\\d{5}(?:\\-\\d{4})?\\b)"
      score: 0.01
    supported_languages:
    - language: en
      context: [zip, code]
    - language: es
      context: [código, postal]
    supported_entity: "ZIP"
    type: custom
    enabled: true

  - name: "TitlesRecognizer"
    supported_language: "en"
    supported_entity: "TITLE"
    deny_list: [Mr., Mrs., Ms., Miss, Dr., Prof.]
    deny_list_score: 1

  - name: "HuggingFace NER"
    type: "predefined"
    class_name: "HuggingFaceNerRecognizer"
    model_name: "dslim/bert-base-NER"
    supported_languages:
      - en
    supported_entities: ["PERSON", "LOCATION", "ORGANIZATION"]
    aggregation_strategy: "simple"
    device: "cpu"
```

### The recognizer parameters

  - `supported_languages`: A list of supported languages that the analyzer will support. In case this field is missing, a recognizer will be created for each supported language provided to the `AnalyzerEngine`. 
  In addition to the language code, this field also contains a list of context words, which increases confidence in the detection in case it is found in the surroundings of a detected entity (as seen in the credit card example above).
  - `type`: this could be either predefined or custom. As this is optional, if not stated otherwise, the default type is custom.
  - `name`: Different per the type of the recognizer. For predefined recognizers, this is the class name as defined in presidio, while for custom recognizers, it will be set as the name of the recognizer.
  - `patterns`: a list of objects of type `Pattern` that contains a name, score and regex that define matching patterns.
  - `enabled`: enables or disables the recognizer.
  - `supported_entity`: the detected entity associated by the recognizer.
  - `deny_list`: A list of words to detect, in case the recognizer uses a predefined list of words.
  - `deny_list_score`: confidence score for a term identified using a deny-list. If omitted, defaults to `1.0` (previously this silently defaulted to `0.0` when loaded through `RecognizerRegistryProvider`, which caused deny-list matches to be filtered out by any positive `score_threshold`).
  - `score_thresholds`: optional score thresholds for this recognizer. Use `default` as the recognizer-wide threshold and entity names for overrides. Note that supplying `analyzer_engine.analyze(score_threshold=...)` bypasses recognizer-level thresholds for that request. The precedence is: Presidio Analyzer analyzer.analyze(score_threshold=...) > an entity specific threshold > a recognizer default threshold (`default`) > the Presidio Analyzer `default_score_threshold`.
  - `text_chunker`: configures how long texts are split for NER recognizers (`GLiNERRecognizer`, `HuggingFaceNerRecognizer`). Accepts a dict with `chunker_type` and params. Available types: `character` (default) and `tokenizer` (uses the model's tokenizer for accurate token-based splitting). Example:

    ```yaml
    - name: GLiNERRecognizer
      type: predefined
      model_name: urchade/gliner_multi_pii-v1
      text_chunker:
        chunker_type: tokenizer
        # max_tokens omitted: auto-derived from the model's tokenizer and
        # reduced to reserve room for special tokens ([CLS]/[SEP]). Set it
        # explicitly only if you account for those special tokens yourself.
        overlap_tokens: 32
    ```

!!! tip "Configuration Tip: Agglutinative languages (e.g., Korean)"

    If spaCy-based NER produces noisy or redundant results, you can disable `SpacyRecognizer` and use `HuggingFaceNerRecognizer` as an alternative. Note that `HuggingFaceNerRecognizer` bypasses the spaCy tokenizer alignment mechanism.



    ```yaml
    - name: "SpacyRecognizer"
      type: "predefined"
      class_name: "SpacyRecognizer"
      supported_languages: ["ko"]
      enabled: false
    ```

## Using a custom registry file with the Presidio Analyzer server

The Presidio Analyzer server (the `presidio-analyzer` Docker image) selects
its recognizer registry through the `RECOGNIZER_REGISTRY_CONF_FILE`
environment variable. It defaults to the bundled
`presidio_analyzer/conf/default_recognizers.yaml`; point it at your own YAML
file (mounted into the container) to load a modified registry without
rebuilding the image. The server reads `ANALYZER_CONF_FILE` and
`NLP_CONF_FILE` the same way.

!!! note "Note"

    `supported_languages` in the registry file must match the same field in
    the analyzer configuration file.

### Example: enabling a pattern-based country recognizer for `en`

Some predefined recognizers are only registered for their native language.
`ItFiscalCodeRecognizer`, for example, is registered with
`supported_languages: [it]` in `default_recognizers.yaml`, so the default
image — which loads the `en` NLP model and `supported_languages: [en]` —
cannot detect Italian fiscal codes. Because the recognizer is pattern-based,
it does not depend on the Italian NLP model and can be enabled for `en` by
overriding the registry file:

1. Copy the default registry file and change the recognizer's
`supported_languages` (leave `country_code` unchanged — it must match the
class declaration and is only the country tag, not a language):

    ```yaml
    - name: ItFiscalCodeRecognizer
      supported_languages:
      - en
      type: predefined
      country_code: it
    ```

2. Run the analyzer with the file mounted and the environment variable set:

    ```bash
    docker run --rm -p 3000:3000 \
      -v $(pwd)/my_recognizers.yaml:/app/my_recognizers.yaml \
      -e RECOGNIZER_REGISTRY_CONF_FILE=/app/my_recognizers.yaml \
      ghcr.io/data-privacy-stack/presidio-analyzer:<version>
    ```

Requests with `entities: ["IT_FISCAL_CODE"]` are now served for
`language: en`.

To restrict or extend which country-specific recognizers are loaded in
general, see [Filtering recognizers by country](filtering_by_country.md).
