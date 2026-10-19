# Example 6: Leveraging context words

Presidio has an internal mechanism for leveraging context words. This mechanism would increase the detection confidence of a PII entity in case a specific word appears before or after it.

Furthermore, it is possible to create your own context enhancer, if you require a different logic for identifying context terms. The default context-aware enhancer in Presidio is the `LemmaContextAwareEnhancer` which compares each recognizer's context terms with the lemma of each token in the sentence.

In this example we would first implement a zip code recognizer without context, and then add context to see how the confidence changes. Zip regex patterns (essentially 5 digits) are very weak, so we would want the initial confidence to be low, and increased with the existence of context words.

## Example: Adding context words support to recognizers

First, let's create a simple `US_ZIP_CODE` recognizer:

<!--pytest-codeblocks:cont-->
```python
from presidio_analyzer import (
    Pattern,
    PatternRecognizer,
    RecognizerRegistry,
    AnalyzerEngine,
)

# Define the regex pattern
regex = r"(\b\d{5}(?:\-\d{4})?\b)"  # very weak regex pattern
zipcode_pattern = Pattern(name="zip code (weak)", regex=regex, score=0.01)

# Define the recognizer with the defined pattern
zipcode_recognizer = PatternRecognizer(
    supported_entity="US_ZIP_CODE", patterns=[zipcode_pattern]
)

registry = RecognizerRegistry()
registry.add_recognizer(zipcode_recognizer)
analyzer = AnalyzerEngine(registry=registry)

# Test
results = analyzer.analyze(text="My zip code is 90210", language="en")

print(f"Result:\n {results}")
```

So this is working, but would catch any 5 digit string. This is why we set the score to 0.01. Let's use context words to increase score:

<!--pytest-codeblocks:cont-->
```python
from presidio_analyzer import PatternRecognizer

# Define the recognizer with the defined pattern and context words
zipcode_recognizer_w_context = PatternRecognizer(
    supported_entity="US_ZIP_CODE",
    patterns=[zipcode_pattern],
    context=["zip", "zipcode"],
)
```

When creating an ```AnalyzerEngine``` we can provide our own context enhancement logic by passing it to ```context_aware_enhancer``` parameter.
```AnalyzerEngine``` will create ```LemmaContextAwareEnhancer``` by default if not passed, which will enhance score of each matched result if its recognizer holds context words and the lemma of those words are found in the surroundings of the matched entity.

Creating the `AnalyzerEngine` and adding the new recognizer:

<!--pytest-codeblocks:cont-->
```python
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry

registry = RecognizerRegistry()
registry.add_recognizer(zipcode_recognizer_w_context)
analyzer = AnalyzerEngine(registry=registry)

# Test
results = analyzer.analyze(text="My zip code is 90210", language="en")
print("Result:")
print(results)
```

The confidence score is now 0.4, instead of 0.01, since the ```LemmaContextAwareEnhancer``` default context similarity factor is 0.35 and default minimum score with context similarity is 0.4. We can change that by passing other values to the ```context_similarity_factor``` and ```min_score_with_context_similarity``` parameters of the ```LemmaContextAwareEnhancer``` object. For example:

<!--pytest-codeblocks:cont-->
```python
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.context_aware_enhancers import LemmaContextAwareEnhancer

context_aware_enhancer = LemmaContextAwareEnhancer(
    context_similarity_factor=0.45, min_score_with_context_similarity=0.4
)

registry = RecognizerRegistry()
registry.add_recognizer(zipcode_recognizer_w_context)
analyzer = AnalyzerEngine(
    registry=registry, context_aware_enhancer=context_aware_enhancer
)

# Test
results = analyzer.analyze(text="My zip code is 90210", language="en")
print("Result:")
print(results)
```

The confidence score is now 0.46 because it got enhanced from 0.01 with 0.45 and is more than the minimum of 0.4.

Some lemmatizers split words into morphemes. For example, the Korean spaCy models can lemmatize `연락처가` as `연+락처+가` (the split depends on the surrounding text), so the context word `연락처` is not found. For such languages, pass their ISO 639-1 codes in `token_text_languages` to compare context words with the token text instead of the lemma:

```python
from presidio_analyzer.context_aware_enhancers import LemmaContextAwareEnhancer

context_aware_enhancer = LemmaContextAwareEnhancer(token_text_languages=["ko"])
```

In addition to surrounding words, additional context words could be passed on the request level.
This is useful when there is context coming from metadata such as column names or a specific user input.
In the following example, notice how the "zip" context word doesn't appear in the text but still enhances the confidence score from 0.01 to 0.4:

<!--pytest-codeblocks:cont-->
```python
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry, PatternRecognizer

# Define the recognizer with the defined pattern and context words
zipcode_recognizer = PatternRecognizer(
    supported_entity="US_ZIP_CODE",
    patterns=[zipcode_pattern],
    context=["zip", "zipcode"],
)
registry = RecognizerRegistry()
registry.add_recognizer(zipcode_recognizer)
analyzer = AnalyzerEngine(registry=registry)

# Test with an example record having a column name which could be injected as context
record = {"column_name": "zip", "text": "My code is 90210"}

result = analyzer.analyze(
    text=record["text"], language="en", context=[record["column_name"]]
)

print("Result:")
print(result)
```
