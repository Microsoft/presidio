# PII detection in different languages

Presidio supports PII detection in multiple languages.
In its default configuration, it contains recognizers and models for English.

To extend Presidio to detect PII in an additional language, these modules require modification:

1. The `NlpEngine` containing the NLP model which performs tokenization,
lemmatization, Named Entity Recognition (if supported), and other NLP tasks.
2. PII recognizers (different `EntityRecognizer` objects) should be adapted or created.

!!! note "Note"
    While different detection mechanisms such as regular expressions are language agnostic, the context words used to increase the PII detection confidence aren't. Consider updating the list of context words for each recognizer to leverage context words in additional languages.

## Table of contents

- [Configuring the NLP Engine](#configuring-the-nlp-engine)
- [Set up language specific recognizers](#set-up-language-specific-recognizers)
- [Automatically install NLP models into the Docker container](#automatically-install-nlp-models-into-the-docker-container)

### Configuring the NLP Engine

Presidio's NLP engine can be adapted to support multiple languages and frameworks (such as *spaCy, Stanza* and *transformers*).
Configuring the NLP engine for a new language or NLP framework is done by downloading or using a model trained on a different language, and providing a configuration.
See the [NLP model customization documentation](customizing_nlp_models.md) for details on how to configure models for new languages.


### Set up language specific recognizers

Recognizers are language dependent either by their logic or by the context words used while scanning the surrounding of a detected entity.
As these context words are used to increase score, they should be in the expected input language.

Consider updating the context words of existing recognizers or add new recognizers to support new languages.
Each recognizer can support one language. For example:

```python
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.predefined_recognizers import EmailRecognizer
from presidio_analyzer.nlp_engine import NlpEngineProvider

LANGUAGES_CONFIG_FILE = "./docs/analyzer/languages-config.yml"

# Create NLP engine based on configuration file
provider = NlpEngineProvider(conf_file=LANGUAGES_CONFIG_FILE)
nlp_engine_with_spanish = provider.create_engine()

# Setting up an English Email recognizer:
email_recognizer_en = EmailRecognizer(supported_language="en", context=["email", "mail"])

# Setting up a Spanish Email recognizer
email_recognizer_es = EmailRecognizer(supported_language="es", context=["correo", "electrónico"])

registry = RecognizerRegistry()

# Add recognizers to registry
registry.add_recognizer(email_recognizer_en)
registry.add_recognizer(email_recognizer_es)

# Set up analyzer with our updated recognizer registry
analyzer = AnalyzerEngine(
    registry=registry,
    supported_languages=["en","es"],
    nlp_engine=nlp_engine_with_spanish)

analyzer.analyze(text="My name is David", language="en")
```
Link to LANGUAGES_CONFIG_FILE=[languages-config.yml](https://github.com/data-privacy-stack/presidio/blob/main/docs/analyzer/languages-config.yml)

### Automatically install NLP models into the Docker container

When packaging the code into a Docker container, NLP models are automatically installed.
To define which models should be installed,
update the [conf/default.yaml](https://github.com/data-privacy-stack/presidio/blob/main/presidio-analyzer/presidio_analyzer/conf/default.yaml) file. This file is read during
the `docker build` phase and the models defined in it are installed automatically.

For `transformers` based models, the configuration [can be found here](https://github.com/data-privacy-stack/presidio/blob/main/presidio-analyzer/presidio_analyzer/conf/transformers.yaml). 
A docker file supporting transformers models [can be found here](https://github.com/data-privacy-stack/presidio/blob/main/presidio-analyzer/Dockerfile.transformers).
