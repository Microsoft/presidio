# Presidio analyzer

## Description

The Presidio analyzer is a Python based service for detecting PII entities in text.

During analysis, it runs a set of different _PII Recognizers_,
each one in charge of detecting one or more PII entities using different mechanisms.

Presidio analyzer comes with a set of predefined recognizers,
but can easily be extended with other types of custom recognizers.
Predefined and custom recognizers leverage regex,
Named Entity Recognition and other types of logic to detect PII in unstructured text.

### Language Model-based PII/PHI Detection

Presidio analyzer supports language model-based PII/PHI detection (LLMs, SLMs) for flexible entity recognition. The current implementation uses [LangExtract](https://github.com/google/langextract) with support for multiple providers:

- **Ollama** - Local model deployment for privacy-sensitive environments
- **Azure OpenAI** - Cloud-based deployment with enterprise features

```bash
pip install "presidio-analyzer[langextract]"
```

#### Quick Usage

**Ollama** (local models):

```python
from presidio_analyzer.predefined_recognizers import BasicLangExtractRecognizer
recognizer = BasicLangExtractRecognizer()  # Uses default config
```

**Azure OpenAI** (cloud models):

```python
from presidio_analyzer.predefined_recognizers import AzureOpenAILangExtractRecognizer

# Simple usage - pass everything as parameters
recognizer = AzureOpenAILangExtractRecognizer(
    model_id="gpt-4",  # Your Azure deployment name
    azure_endpoint="https://your-resource.openai.azure.com/",
    api_key="your-api-key"
)

# Or use environment variables (AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY):
recognizer = AzureOpenAILangExtractRecognizer(
    model_id="gpt-4"  # Your Azure deployment name
)

# Advanced: Customize entities/prompts with config file
recognizer = AzureOpenAILangExtractRecognizer(
    model_id="gpt-4",
    config_path="./custom_config.yaml",  # Optional: for custom entities/prompts
    azure_endpoint="https://your-resource.openai.azure.com/",
    api_key="your-api-key"
)
```

**Note:** LangExtract recognizers do not validate connectivity during initialization. Connection errors or missing models will be reported when `analyze()` is first called.

See the [Language Model-based PII/PHI Detection guide](https://presidio.dataprivacystack.org/samples/python/langextract/) for complete setup and usage instructions.

## Deploy Presidio analyzer to Azure

Use the following button to deploy presidio analyzer to your Azure subscription.

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Fmicrosoft%2Fpresidio%2Fmain%2Fpresidio-analyzer%2Fdeploytoazure.json)

## Simple usage example

```python
from presidio_analyzer import AnalyzerEngine

# Set up the engine, loads the NLP module (spaCy model by default) and other PII recognizers
analyzer = AnalyzerEngine()

# Call analyzer to get results
results = analyzer.analyze(text="My phone number is 212-555-5555",
                           entities=["PHONE_NUMBER"],
                           language='en')
print(results)

```

## GPU Acceleration

For GPU acceleration, install the appropriate dependencies for your hardware:

- **Linux with NVIDIA GPU**: cupy-cuda12x (or the version matching your CUDA installation)
- **macOS with Apple Silicon**: MPS (Metal Performance Shaders) is currently not supported. The analyzer will use CPU for PyTorch operations.

## Documentation

Additional documentation on installation, usage and extending the Analyzer can be found under the [Analyzer](https://presidio.dataprivacystack.org/analyzer/) section of [Presidio Documentation](https://presidio.dataprivacystack.org)
