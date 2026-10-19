# Example 5: Supporting new models and languages

Two main parts in Presidio handle the text, and should be adapted if a new language is required:

1. The `NlpEngine` containing the NLP model which performs tokenization, lemmatization, Named Entity Recognition (if supported), and other NLP tasks.
2. The different PII recognizers (`EntityRecognizer` objects) should be adapted or created.

## Adapting the NLP engine

As its internal NLP engine, Presidio supports both spaCy and Stanza. Make sure you download the required models from spacy/stanza prior to using them. More details [here](https://data-privacy-stack.github.io/presidio/analyzer/languages/#configuring-the-nlp-engine). For example, to download the Spanish medium spaCy model: `python -m spacy download es_core_news_md`

In this example we will configure Presidio to use spaCy as its underlying NLP framework, with NLP models in English and Spanish:

<!--pytest-codeblocks:cont-->
```python
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider

# import spacy
# spacy.cli.download("es_core_news_md")

# Create configuration containing engine name and models
configuration = {
    "nlp_engine_name": "spacy",
    "models": [
        {"lang_code": "es", "model_name": "es_core_news_md"},
        {"lang_code": "en", "model_name": "en_core_web_lg"},
    ],
}

# Create NLP engine based on configuration
provider = NlpEngineProvider(nlp_configuration=configuration)
nlp_engine_with_spanish = provider.create_engine()

# Pass the created NLP engine and supported_languages to the AnalyzerEngine
analyzer = AnalyzerEngine(
    nlp_engine=nlp_engine_with_spanish, supported_languages=["en", "es"]
)

# Analyze in different languages
results_spanish = analyzer.analyze(text="Mi nombre es Morris", language="es")
print("Results from Spanish request:")
print(results_spanish)

results_english = analyzer.analyze(text="My name is Morris", language="en")
print("Results from English request:")
print(results_english)
```

[See this documentation](https://data-privacy-stack.github.io/presidio/analyzer/languages/) for more details on setting up additional NLP models and languages.

## Using external models/frameworks

Some languages are not supported by spaCy/Stanza/huggingface, or have very limited support in those. In this case, other frameworks could be leveraged. (see [example 4](04_external_services.md) for more information).

Since Presidio requires a spaCy model to be passed, we propose to use a simple spaCy pipeline such as `en_core_web_sm` as the NLP engine's model, and a recognizer calling an external framework/service as the Named Entity Recognition (NER) model.
