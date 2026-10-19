# Presidio structured

## Description

The Presidio structured package is a flexible and customizable framework designed to identify and protect structured sensitive data.

This tool extends the capabilities of Presidio, focusing on structured data formats such as tabular formats and semi-structured formats (JSON).
It leverages the detection capabilities of Presidio-Analyzer to identify columns or keys containing personally identifiable information (PII), and establishes a mapping between these column/keys names and the detected PII entities.

Following the detection, Presidio-Anonymizer is used to apply de-identification techniques
to each value in columns identified as containing PII, ensuring the sensitive data is appropriately protected.

Note that sensitive data might not be automatically detected in some cases. Consequently, additional systems and protections should be employed.

## Installation

### As a python package

To install the `presidio-structured` package, run the following command:

```sh
pip install presidio-structured
```

#### Getting started

##### Example 1: Anonymizing DataFrames

```python
import pandas as pd
from presidio_structured import StructuredEngine, PandasAnalysisBuilder
from presidio_anonymizer.entities import OperatorConfig
from faker import Faker # optionally using faker as an example

# Initialize the engine with a Pandas data processor (default)
pandas_engine = StructuredEngine()

# Create a sample DataFrame
sample_df = pd.DataFrame({'name': ['John Doe', 'Jane Smith'], 'email': ['john.doe@example.com', 'jane.smith@example.com']})

# Generate a tabular analysis which describes PII entities in the DataFrame.
tabular_analysis = PandasAnalysisBuilder().generate_analysis(sample_df)

# Define anonymization operators
fake = Faker()
operators = {
    "PERSON": OperatorConfig("replace", {"new_value": "REDACTED"}),
    "EMAIL_ADDRESS": OperatorConfig("custom", {"lambda": lambda x: fake.safe_email()})
}

# Anonymize DataFrame
anonymized_df = pandas_engine.anonymize(sample_df, tabular_analysis, operators=operators)
print(anonymized_df)
```

##### Example 2: Anonymizing JSON Data

```python
from presidio_structured import StructuredEngine, JsonAnalysisBuilder, StructuredAnalysis, JsonDataProcessor
from presidio_anonymizer.entities import OperatorConfig
from faker import Faker # optionally using faker as an example

# Initialize the engine with a JSON data processor
json_engine = StructuredEngine(data_processor=JsonDataProcessor())


# Sample JSON data
sample_json = {
    "user": {
        "name": "John Doe",
        "email": "john.doe@example.com"
    }
}

# Generate analysis for simple JSON data
json_analysis = JsonAnalysisBuilder().generate_analysis(sample_json)

# Define anonymization operators
fake = Faker() # using faker for email generation.
operators = {
    "PERSON": OperatorConfig("replace", {"new_value": "REDACTED"}),
    "EMAIL_ADDRESS": OperatorConfig("custom", {"lambda": lambda x: fake.safe_email()})
}

# Anonymize JSON data
anonymized_json = json_engine.anonymize(sample_json, json_analysis, operators=operators)
print(anonymized_json)

# Handling Json Data with nested objects in lists
sample_complex_json = {
    "users": [
        {"name": "John Doe", "email": "john.doe@example.com"},
        {"name": "Jane Smith", "email": "jane.smith@example.com"}
    ]
}

# Nesting objects in lists is not supported in JsonAnalysisBuilder for now,
# Manually defining the analysis for complex JSON data
json_complex_analysis = StructuredAnalysis(entity_mapping={
    "users.name": "PERSON",
    "users.email": "EMAIL_ADDRESS"
})

# Anonymize complex JSON data
anonymized_complex_json = json_engine.anonymize(sample_complex_json, json_complex_analysis, operators=operators)
print(anonymized_complex_json)
```

A more detailed sample can be found here:

- <https://github.com/data-privacy-stack/presidio/blob/main/docs/samples/python/example_structured.ipynb>

#### Selection Strategy for Entity Detection in Tabular Data

- **Most Common:**  Identifies the most frequently occurring PII entity in a data column or field.
- **Highest Confidence:**  Selects PII entities based on the highest confidence scores, irrespective of their occurrence frequency.
- **Mixed (default):**  Combines the strengths of both the above strategies. It selects the entity with the highest confidence score if that score exceeds a specified threshold (controlled by `mixed_strategy_threshold`); otherwise, it defaults to the most common entity. This keeps a confident detection (e.g. an email address recognized at 1.0) from losing to noisier, more frequent detections (e.g. URL fragments of the same emails recognized at 0.5).

##### Usage

Specify the `selection_strategy` and optionally the `mixed_strategy_threshold` in the `generate_analysis()` method:

```python
# Generate a tabular analysis using the default (mixed) strategy
tabular_analysis = PandasAnalysisBuilder().generate_analysis(sample_df)

# Generate a tabular analysis using the most common strategy
tabular_analysis = PandasAnalysisBuilder().generate_analysis(sample_df, selection_strategy="most_common")

# Generate a tabular analysis using the highest confidence strategy
tabular_analysis = PandasAnalysisBuilder().generate_analysis(sample_df, selection_strategy="highest_confidence")

# Generate a tabular analysis using the mixed strategy
tabular_analysis = PandasAnalysisBuilder().generate_analysis(sample_df, selection_strategy="mixed", mixed_strategy_threshold=0.75)
```

#### Future work

- Improve support for datasets with mixed free-text and structure data (e.g. some columns contain free text)
- Add support for the detection of sensitive column names
- PySpark implementation
- Integration of additional anonymization techniques such as K-Anonymity and Differential Privacy.

Contributions are welcome! Please refer to the [Contributing Guide](https://github.com/data-privacy-stack/presidio/blob/main/CONTRIBUTING.md).

#### More information

- [API documentation](../api/structured_python.md)
- [Sample code](../samples/python/example_structured.ipynb)
- [Join the discussion](https://github.com/data-privacy-stack/presidio/discussions?discussions_q=structured)
- [Relevant issues on GitHub](https://github.com/data-privacy-stack/presidio/issues?q=is%3Aissue+label%3Astructured-data)
