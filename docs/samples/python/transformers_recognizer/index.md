# Add a Transformers model based EntityRecognizer

!!! note "Note"

    This example demonstrates how to create a **Presidio Recognizer**.
    To integrate a transformers model as a **Presidio NLP Engine**, see [this documentation](../../../analyzer/nlp_engines/transformers.md).

    We allow these two options, as a user might want to have multiple NER models running in parallel. In this case, one can create multiple `EntityRecognizer` instances, each serving a different model. If you only plan to use one NER model, consider creating a [`TransformersNlpEngine`](../../../analyzer/nlp_engines/transformers.md) instead of the [`TransformersRecognizer`](https://github.com/data-privacy-stack/presidio/blob/main/docs/samples/python/transformers_recognizer/transformer_recognizer.py) described in this document.

When initializing the `TransformersRecognizer`, choose from the following options:

1. A string referencing an uploaded model to HuggingFace. See the different available options for models [here](https://huggingface.co/models?pipeline_tag=token-classification&sort=downloads).

2. Initialize your own `TokenClassificationPipeline` instance using your custom transformers model and use it for inference.

3. Provide the path to your own local custom trained model.

!!! note "Note"
    For each combination of model & dataset, it is recommended to create a configuration object which includes setting necessary parameters for getting the correct results. Please reference this [configuration.py](https://github.com/data-privacy-stack/presidio/blob/main/docs/samples/python/transformers_recognizer/configuration.py) file for examples.

## Example Code

This example code uses a `TransformersRecognizer` for NER, and removes the default `SpacyRecognizer`.
In order to be able to use spaCy features such as lemmas, we introduce the small (and faster) `en_core_web_sm` model.

[link to full TransformersRecognizer code](https://github.com/data-privacy-stack/presidio/blob/main/docs/samples/python/transformers_recognizer/transformer_recognizer.py)

```python
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider
import spacy

model_path = "obi/deid_roberta_i2b2"
supported_entities = BERT_DEID_CONFIGURATION.get(
    "PRESIDIO_SUPPORTED_ENTITIES")
transformers_recognizer = TransformersRecognizer(model_path=model_path,
                                                 supported_entities=supported_entities)

# This would download a large (~500Mb) model on the first run
transformers_recognizer.load_transformer(**BERT_DEID_CONFIGURATION)

# Add transformers model to the registry
registry = RecognizerRegistry()
registry.add_recognizer(transformers_recognizer)
registry.remove_recognizer("SpacyRecognizer")

# Use small spacy model, for faster inference.
if not spacy.util.is_package("en_core_web_sm"):
    spacy.cli.download("en_core_web_sm")

nlp_configuration = {
    "nlp_engine_name": "spacy",
    "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
}

nlp_engine = NlpEngineProvider(nlp_configuration=nlp_configuration).create_engine()

analyzer = AnalyzerEngine(registry=registry, nlp_engine=nlp_engine)

sample = "My name is John and I live in NY"
results = analyzer.analyze(sample, language="en",
                           return_decision_process=True,
                           )
print("Found the following entities:")
for result in results:
    print(result, '----', sample[result.start:result.end])
```
