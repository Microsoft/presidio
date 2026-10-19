# Example 7: Tracing the decision process

Presidio-analyzer's decision process exposes information on why a specific PII was detected. Such information could contain:

- Which recognizer detected the entity
- Which regex pattern was used
- Interpretability mechanisms in ML models
- Which context words improved the score
- Confidence scores before and after each step
- The text each entity was identified from (`identified_text`)
And more.

For more information, refer to the [decision process documentation](https://data-privacy-stack.github.io/presidio/analyzer/decision_process/).

Let's use the decision process output to understand how the zip code value was detected:

<!--pytest-codeblocks:cont-->
```python
from presidio_analyzer import AnalyzerEngine
import pprint

analyzer = AnalyzerEngine()

results = analyzer.analyze(
    text="My zip code is 90210", language="en", return_decision_process=True
)

decision_process = results[0].analysis_explanation

pp = pprint.PrettyPrinter()
print("Decision process output:\n")
pp.pprint(decision_process.__dict__)
```

When developing new recognizers, one can add information to this explanation and extend it with additional findings.
