# Presidio anonymizer

## Description

The Presidio anonymizer is a Python based module for anonymizing detected PII text
entities with desired values.

![Anonymizer Design](../docs/assets/anonymizer-design.png)

### Deploy Presidio anonymizer to Azure

Use the following button to deploy presidio anonymizer to your Azure subscription.
 
[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Fmicrosoft%2Fpresidio%2Fmain%2Fpresidio-anonymizer%2Fdeploytoazure.json)


The Presidio-Anonymizer package contains both Anonymizers and Deanonymizers.
- *Anonymizers* are used to replace a PII entity text with some other value.
- *Deanonymizers* are used to revert the anonymization operation. 
  For example, to decrypt an encrypted text.

### Anonymizer

Presidio anonymizer comes by default with the following anonymizers:

-   **Replace**: Replaces the PII with desired value.
    -   Parameters: `new_value` - replaces existing text with the given value.
        If `new_value` is not supplied or empty, default behavior will be: <entity_type>
        e.g: <PHONE_NUMBER>

-   **Redact**: Removes the PII completely from text.
    -   Parameters: None
-   **Hash**: Hashes the PII using either sha256 or sha512. 
    -   Parameters:
        - `hash_type`: Sets the type of hashing. 
          Can be either `sha256` or `sha512` (`md5` is deprecated as of version 2.2.358).
          The default hash type is `sha256`.
-   **Mask**: Replaces the PII with a sequence of a given character.
    -   Parameters:

        -   `chars_to_mask`: The amount of characters out of the PII that should be
            replaced.
        -   `masking_char`: The character to be replaced with.
        -   `from_end`: Whether to mask the PII from it's end.
    
-   **Encrypt**: Encrypt the PII entity text and replace the original with the encrypted string. 
-   **Custom**: Replace the PII with the result of the function executed on the PII string.
    - Parameters: `lambda`: Lambda function to execute on the PII string.
    The lambda return type must be a string.
-   **AHDS Surrogate**: Use Azure Health Data Services de-identification service surrogation to generate realistic, medically-appropriate surrogates for detected PHI entities. This operator maintains data utility by preserving data relationships and format.
    - Parameters:
        - `endpoint`: AHDS endpoint (optional, can use AHDS_ENDPOINT env var)
        - `entities`: List of entities detected by analyzer  
        - `input_locale`: Input locale (default: "en-US")
        - `surrogate_locale`: Surrogate locale (default: "en-US")
    - Requires: `pip install presidio-anonymizer[ahds]`
    - Usage: `OperatorConfig("surrogate", {...})`


The **Anonymizer** default setting is to use the Advanced Encryption Standard (AES) as the encryption algorithm, also known as Rijndael. 
   
-  Parameters:
    - `key`: A cryptographic key used for the encryption. 
      The length of the key needs to be of 128, 192 or 256 bits, in a string format.
    - `deterministic`: Optional boolean, `false` by default. When `true`, the same
      text always encrypts to the same value, which keeps references across a dataset
      intact. It reveals which entities share a value and how often each value occurs,
      so turn it on only where referential integrity is an actual requirement.

Note: If the default anonymizer is not provided, 
the default anonymizer is "replace" for all entities. 
The replacing value will be the entity type e.g.: <PHONE_NUMBER>

#### Handling overlaps between entities

As the input text could potentially have overlapping PII entities, there are different
anonymization scenarios:

-   **No overlap (single PII)**: When there is no overlap in spans of entities, 
    Presidio Anonymizer uses a given or default anonymization operator to anonymize 
    and replace the PII text entity.
-   **Full overlap of PII entity spans**: When entities have overlapping substrings,  
    the PII with the higher score will be taken. 
    Between PIIs with identical scores, the selection is arbitrary.
-   **One PII is contained in another**: Presidio Anonymizer will use the PII with the larger text even if it's score is lower.
-   **Partial intersection**: Presidio Anonymizer will anonymize each individually and will return a concatenation of the anonymized text. 
    For example: 
    For the text
    ```
    I'm George Washington Square Park.
    ``` 
    Assuming one entity is `George Washington` and the other is `Washington State Park` 
    and assuming the default anonymizer, the result would be 
    ```
    I'm <PERSON><LOCATION>.
    ```

Additional examples for overlapping PII scenarios:

Text:
```
My name is Inigo Montoya. You Killed my Father. Prepare to die. BTW my number is:
03-232323.
```

-   No overlaps: Assuming only `Inigo` is recognized as NAME:
    ```
    My name is <NAME> Montoya. You Killed my Father. Prepare to die. BTW my number is:
    03-232323.
    ```
-   Full overlap: Assuming the number is recognized as PHONE_NUMBER with score of 0.7 and as SSN
    with score of 0.6, the higher score would count:
    ```
    My name is Inigo Montoya. You Killed my Father. Prepare to die. BTW my number is: <
    PHONE_NUMBER>.
    ```
-   One PII is contained is another: Assuming Inigo is recognized as FIRST_NAME and Inigo Montoya
    was recognized as NAME, the larger one will be used:
    ```
    My name is <NAME>. You Killed my Father. Prepare to die. BTW my number is: 03-232323.
    ```
-   Partial intersection: Assuming the number 03-2323 is recognized as a PHONE_NUMBER but 232323
    is recognized as SSN:
    ```
    My name is Inigo Montoya. You Killed my Father. Prepare to die. BTW my number is: <
    PHONE_NUMBER><SSN>.
    ```

### Deanonymizer

Presidio deanonymizer currently contains one operator:

-   **Decrypt**: Replace the encrypted text with decrypted text. 
    Uses Advanced Encryption Standard (AES) as the encryption algorithm, also known as Rijndael. 
    -  Parameters:
        -   `key` - a cryptographic key used for the encryption. 
            The length of the key needs to be of 128, 192 or 256 bits, in a string format.

Please notice: you can use "DEFAULT" as an operator key to define an operator over all entities.

## Installation

### As a python package:

To install Presidio Anonymizer, run the following, preferably in a virtual environment:

```sh
pip install presidio-anonymizer
```

#### Getting started

```python
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import RecognizerResult, OperatorConfig

# Initialize the engine with logger.
engine = AnonymizerEngine()

# Invoke the anonymize function with the text, 
# analyzer results (potentially coming from presidio-analyzer) and
# Operators to get the anonymization output:
result = engine.anonymize(
    text="My name is Bond, James Bond",
    analyzer_results=[
        RecognizerResult(entity_type="PERSON", start=11, end=15, score=0.8),
        RecognizerResult(entity_type="PERSON", start=17, end=27, score=0.8),
    ],
    operators={"PERSON": OperatorConfig("replace", {"new_value": "BIP"})},
)

print(result)
```
This example take the output of the AnonymizerEngine with encrypted PII entities, 
and decrypt it back to the original text:
```python
from presidio_anonymizer import DeanonymizeEngine
from presidio_anonymizer.entities import OperatorResult, OperatorConfig

# Initialize the engine with logger.
engine = DeanonymizeEngine()

# Invoke the deanonymize function with the text, anonymizer results and
# Operators to define the deanonymization type.
result = engine.deanonymize(
    text="My name is S184CMt9Drj7QaKQ21JTrpYzghnboTF9pn/neN8JME0=",
    entities=[
        OperatorResult(start=11, end=55, entity_type="PERSON"),
    ],
    operators={"DEFAULT": OperatorConfig("decrypt", {"key": "WmZq4t7w!z%C&F)J"})},
)

print(result)

```

Batch deanonymization works the same way for lists and nested dictionaries:
```python
from presidio_anonymizer import BatchDeanonymizeEngine
from presidio_anonymizer.entities import OperatorConfig, OperatorResult

engine = BatchDeanonymizeEngine()

results = engine.deanonymize_list(
    texts=[
        "My name is S184CMt9Drj7QaKQ21JTrpYzghnboTF9pn/neN8JME0=",
        "My name is S184CMt9Drj7QaKQ21JTrpYzghnboTF9pn/neN8JME0=",
    ],
    entities_list=[
        [OperatorResult(start=11, end=55, entity_type="PERSON")],
        [OperatorResult(start=11, end=55, entity_type="PERSON")],
    ],
    operators={"DEFAULT": OperatorConfig("decrypt", {"key": "WmZq4t7w!z%C&F)J"})},
)

print(results)
```

### As docker service:

In folder presidio/presidio-anonymizer run:

```
docker-compose up -d
```

### HTTP API

Follow the [API Spec](https://presidio.dataprivacystack.org/api-docs/api-docs.html#tag/Anonymizer) for the
Anonymizer REST API reference details
