# No code configuration

No-code configuration can be helpful in three scenarios:

1. There's an existing set of regular expressions / deny-lists that should be leveraged within Presidio.
2. As a simple way to configure which recognizers to enable and disable, and how to configure the NLP engine.
3. For team members interested in changing the configuration without writing code.

In this example, we'll show how to create a no-code configuration in Presidio.
We start by creating YAML configuration files that are based on the default ones.
The default configuration files for Presidio can be found here:

- [Analyzer configuration](https://github.com/data-privacy-stack/presidio/blob/main/presidio-analyzer/presidio_analyzer/conf/default_analyzer.yaml)
- [Recognizer registry configuration](https://github.com/data-privacy-stack/presidio/blob/main/presidio-analyzer/presidio_analyzer/conf/default_recognizers.yaml)
- [NLP engine configuration](https://github.com/data-privacy-stack/presidio/blob/main/presidio-analyzer/presidio_analyzer/conf/default.yaml)

Alternatively, one can create one configuration file for all three components.
In this example, we'll tweak the configuration to reduce the number of predefined recognizers to only a few, and add a new custom one. We'll also adjust the context words to support the detection of a different language (Spanish).

```python
import yaml
import json
import tempfile
from pprint import pprint
from presidio_analyzer import AnalyzerEngineProvider
```

In this example we're going to create the yaml as a string for illustration purposes, but the more common scenario is to create these YAML files and load them into the `PresidioAnalyzerProvider`.

## Defining the configuration in YAML format

### General Analyzer parameters

([default file](https://github.com/data-privacy-stack/presidio/blob/main/presidio-analyzer/presidio_analyzer/conf/default_analyzer.yaml))

```python
analyzer_config_yaml = """
supported_languages: 
  - en
  - es
default_score_threshold: 0.4
"""
```

### Recognizer Registry parameters

([default file](https://github.com/data-privacy-stack/presidio/blob/main/presidio-analyzer/presidio_analyzer/conf/default_recognizers.yaml))

```python

recognizer_registry_config_yaml = """
recognizer_registry:
  supported_languages: 
  - en
  - es
  global_regex_flags: 26

  recognizers:
  - name: CreditCardRecognizer
    supported_languages:
    - language: en
      context: [credit, card, visa, mastercard, cc, amex, discover, jcb, diners, maestro, instapayment]
    - language: es
      context: [tarjeta, credito, visa, mastercard, cc, amex, discover, jcb, diners, maestro, instapayment]
    type: predefined
    score_thresholds:
      default: 0.4
      CREDIT_CARD: 0.7
    
  - name: DateRecognizer
    supported_languages:
    - language: en
      context: [date, time, birthday, birthdate, dob]
    - language: es
      context: [fecha, tiempo, hora, nacimiento, dob]
    type: predefined

  - name: EmailRecognizer
    supported_languages:
    - language: en
      context: [email, mail, address]
    - language: es
      context: [correo, electrónico, email]
    type: predefined
    
  - name: PhoneRecognizer
    type: predefined
    supported_languages:
    - language: en
      context: [phone, number, telephone, fax]
    - language: es
      context: [teléfono, número, fax]
    
  - name: "Titles recognizer (en)"
    supported_language: "en"
    supported_entity: "TITLE"
    deny_list:
      - Mr.
      - Mrs.
      - Ms.
      - Miss
      - Dr.
      - Prof.
      - Doctor
      - Professor
  - name: "Titles recognizer (es)"
    supported_language: "es"
    supported_entity: "TITLE"
    deny_list:
      - Sr.
      - Señor
      - Sra.
      - Señora
      - Srta.
      - Señorita
      - Dr.
      - Doctor
      - Doctora
      - Prof.
      - Profesor
      - Profesora
"""
```

Each recognizer can set a `default` threshold and entity-specific overrides in `score_thresholds`. Supplying `analyze(score_threshold=...)` bypasses recognizer-level thresholds for that request. When omitted, precedence is an entity override, the recognizer default, then the analyzer's `default_score_threshold`.

### NLP Engine parameters

([default file](https://github.com/data-privacy-stack/presidio/blob/main/presidio-analyzer/presidio_analyzer/conf/default.yaml))

```python
nlp_engine_yaml = """
nlp_configuration:
    nlp_engine_name: transformers
    models:
      -
        lang_code: en
        model_name:
          spacy: en_core_web_sm
          transformers: StanfordAIMI/stanford-deidentifier-base
      -
        lang_code: es
        model_name:
          spacy: es_core_news_sm
          transformers: MMG/xlm-roberta-large-ner-spanish  
    ner_model_configuration:
      labels_to_ignore:
      - O
      aggregation_strategy: first # "simple", "first", "average", "max"
      stride: 16
      alignment_mode: expand # "strict", "contract", "expand"
      model_to_presidio_entity_mapping:
        PER: PERSON
        PERSON: PERSON
        LOC: LOCATION
        LOCATION: LOCATION
        GPE: LOCATION
        ORG: ORGANIZATION
        ORGANIZATION: ORGANIZATION
        NORP: NRP
        AGE: AGE
        ID: ID
        EMAIL: EMAIL
        PATIENT: PERSON
        STAFF: PERSON
        HOSP: ORGANIZATION
        PATORG: ORGANIZATION
        DATE: DATE_TIME
        TIME: DATE_TIME
        PHONE: PHONE_NUMBER
        HCW: PERSON
        HOSPITAL: LOCATION
        FACILITY: LOCATION
        VENDOR: ORGANIZATION
        MISC: ID
    
      low_confidence_score_multiplier: 0.4
      low_score_entity_names:
      - ID
"""
```

## Creating the analyzer engine and running it

### Create a unified YAML file and save it as a temp file

```python
full_config = f"{analyzer_config_yaml}\n{recognizer_registry_config_yaml}\n{nlp_engine_yaml}"

with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.yaml') as temp_file:
    # Write the YAML string to the temp file
    temp_file.write(full_config)
    temp_file_path = temp_file.name


```

### Pass the YAML file to `AnalyzerEngineProvider` to create an `AnalyzerEngine` instance

```python
analyzer_engine = AnalyzerEngineProvider(analyzer_engine_conf_file=temp_file_path).create_engine()

```

### Print the loaded configuration for both languages

```python
for lang in ("en", "es"):
    pprint(f"Supported entities for {lang}:")
    print("\n")
    pprint(analyzer_engine.get_supported_entities(lang), compact=True)
    
    print(f"\nLoaded recognizers for {lang}:")
    pprint([rec.name for rec in analyzer_engine.registry.get_recognizers(lang, all_fields=True)], compact=True)
    print("\n")
   
print(f"\nLoaded NER models:")
pprint(analyzer_engine.nlp_engine.models)
```

## Run two requests, one in English and one in Spanish

```python
es_text = "Hola, me llamo David Johnson y soy originalmente de Liverpool. Mi número de tarjeta de crédito es 4095260993934932"
analyzer_engine.analyze(es_text, language="es")
```

```python
en_text = "Hi, my name is David Johnson and I'm originally from Liverpool. My credit card number is 4095260993934932"
analyzer_engine.analyze(en_text, language="en")
```
