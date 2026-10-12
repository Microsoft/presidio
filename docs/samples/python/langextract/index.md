# Language Model-based PII/PHI Detection (Experimental Feature)

## Introduction

Presidio supports language model-based PII/PHI detection for flexible entity recognition using language models (LLMs, SLMs, etc.). This approach enables detection of both:
- **PII (Personally Identifiable Information)**: Names, emails, phone numbers, SSN, credit cards, etc.
- **PHI (Protected Health Information)**: Medical records, health identifiers, etc.

(The default approach uses [LangExtract](https://github.com/google/langextract) under the hood to integrate with language model providers.)

## Entity Detection Capabilities

Unlike pattern-based recognizers, language model-based detection is flexible and depends on:

- The language model being used
- The prompt description provided
- The few-shot examples configured

The default configuration includes examples for common PII/PHI entities such as PERSON, EMAIL_ADDRESS, PHONE_NUMBER, US_SSN, CREDIT_CARD, MEDICAL_LICENSE, and more. 
**You can customize the prompts and examples to detect any entity types relevant to your use case**.

For the default entity mappings and examples, see the [default configuration](https://github.com/data-privacy-stack/presidio/blob/main/presidio-analyzer/presidio_analyzer/conf/langextract_config_ollama.yaml).

## Supported Language Model Providers

Presidio supports the following language model providers through LangExtract:

1. **Azure OpenAI** - Cloud-based Azure OpenAI Service (GPT-4o, GPT-4, GPT-3.5-turbo, etc.)
2. **Ollama** - Local language model deployment (open-source models like Gemma, Llama, etc.)

## Choosing Between Azure OpenAI and Ollama

| Feature | Azure OpenAI | Ollama |
|---------|--------------|--------|
| **Deployment** | Cloud (Azure) | Local (on-premises) |
| **Cost** | Pay-per-use (tokens) | Free (hardware required) |
| **Models** | GPT-4o, GPT-4, GPT-3.5-turbo | Open-source (Gemma, Llama, etc.) |
| **Privacy** | Microsoft Azure compliance | Complete data control |
| **Setup** | Azure Portal + API key/Managed Identity | Docker/local installation |
| **Authentication** | API Key or Managed Identity (RBAC) | None (local) |
| **Best For** | Production, enterprise compliance | Development, on-premises requirements |

**Recommendations**:

- **Use Azure OpenAI** for production workloads requiring enterprise security, compliance (HIPAA, SOC 2, etc.), and managed infrastructure
- **Use Ollama** for local development, testing, or when data must stay on-premises

## Language Model-based Recognizer Implementation

Presidio provides a hierarchy of recognizers for language model-based PII/PHI detection:

- **`LMRecognizer`**: Abstract base class for all language model recognizers (LLMs, SLMs, etc.)
- **`LangExtractRecognizer`**: Abstract base class for LangExtract library integration (model-agnostic)
- **`AzureOpenAILangExtractRecognizer`**: Concrete implementation for Azure OpenAI Service
  - [Implementation](https://github.com/data-privacy-stack/presidio/blob/main/presidio-analyzer/presidio_analyzer/predefined_recognizers/third_party/azure_openai_langextract_recognizer.py)
- **`BasicLangExtractRecognizer`**: Concrete implementation where ModelConfig is configured from YAML (supporting Ollama, OpenAI, Gemini, and other providers)
  - [Implementation](https://github.com/data-privacy-stack/presidio/blob/main/presidio-analyzer/presidio_analyzer/predefined_recognizers/third_party/basic_langextract_recognizer.py)

---

## Using Azure OpenAI (Cloud Models)

Azure OpenAI provides cloud-based access to OpenAI models (GPT-4o, GPT-4, GPT-3.5-turbo) with enterprise security and compliance features.

### Prerequisites

1. **Install Presidio with LangExtract support**:
   ```sh
   pip install "presidio-analyzer[langextract]"
   ```

2. **Set up Ollama**

You have two options to set up Ollama:

  **Option 1: Docker Compose** (recommended for CPU)
  
  This option requires Docker to be installed on your system.
  
  **Where to run:** From the root presidio directory (where `docker-compose.yml` is located)
  
  ```bash
  docker compose up -d ollama
  docker exec presidio-ollama-1 ollama pull qwen2.5:1.5b
  docker exec presidio-ollama-1 ollama list
  ```
  
  **Platform differences:**
  - **Linux/Mac**: Commands above work as-is
  - **Windows**: Use PowerShell or CMD, commands are the same
  
  If you don't have Docker installed:
  - Linux: Follow [Docker installation guide](https://docs.docker.com/engine/install/)
  - Mac: Install [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/)
  - Windows: Install [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)

  **Option 2: Native installation** (recommended for GPU acceleration)
  
  Follow the [official LangExtract Ollama guide](https://github.com/google/langextract?tab=readme-ov-file#using-local-llms-with-ollama).
  
  After installation, pull and run the model:
  ```bash
  ollama pull qwen2.5:1.5b
  ollama run qwen2.5:1.5b
  ```

  > This option provides better performance with GPU acceleration (e.g., on Mac with Metal Performance Shaders or systems with NVIDIA GPUs).
  > The model must be pulled and run before using the recognizer. The default model is `qwen2.5:1.5b`.

3. **Configuration** (optional): Create your own `ollama_config.yaml` or use the [default configuration](https://github.com/data-privacy-stack/presidio/blob/main//presidio-analyzer/presidio_analyzer/conf/langextract_config_ollama.yaml)

### Usage

**Option 1: Enable in configuration file**

Enable the recognizer in [`default_recognizers.yaml`](https://github.com/data-privacy-stack/presidio/blob/main/presidio-analyzer/presidio_analyzer/conf/default_recognizers.yaml):
```yaml
- name: BasicLangExtractRecognizer
  enabled: true  # Change from false to true
```

Then load the analyzer using this modified configuration file:

```python
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

# Point to your modified default_recognizers.yaml with Ollama enabled
provider = RecognizerRegistryProvider(
    conf_file="/path/to/your/modified/default_recognizers.yaml"
)
registry = provider.create_recognizer_registry()

# Create analyzer with the registry that includes Ollama recognizer
analyzer = AnalyzerEngine(registry=registry, supported_languages=["en"])

# Analyze text - Ollama recognizer will participate in detection
results = analyzer.analyze(text="My email is john.doe@example.com", language="en")
```

**Option 2: Add programmatically**

```python
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.predefined_recognizers.third_party.basic_langextract_recognizer import BasicLangExtractRecognizer

analyzer = AnalyzerEngine()
analyzer.registry.add_recognizer(BasicLangExtractRecognizer())

results = analyzer.analyze(text="My email is john.doe@example.com", language="en")
```

!!! note "Note"
    The recognizer is disabled by default in `default_recognizers.yaml` to avoid requiring Ollama for basic Presidio usage. Enable it when you have Ollama set up and running.

### Custom Configuration

To use a custom configuration file:

```python
analyzer.registry.add_recognizer(
    BasicLangExtractRecognizer(config_path="/path/to/custom_config.yaml")
)
```

### Configuration Options

The `langextract_config_ollama.yaml` file supports the following options:

- **`model_id`**: The model to use.
- **`provider.name`**: The model provider (eg, ollama, openai)
- **`provider.kwargs`**: kwargs to pass to the model provider (eg, `model_url` for Ollama, `base_url` for OpenAI)
- **`provider.extract_params`**: Extraction parameters (eg, `use_schema_constraints`, `fence_output`, `temperature`)
- **`provider.language_model_params`**: Parameters for the model itself (eg, `timeout`, `num_ctx`)
- **`supported_entities`**: PII/PHI entity types to detect
- **`entity_mappings`**: Map LangExtract entity classes to Presidio entity names
- **`min_score`**: Minimum confidence score (default: `0.5`)

See the [configuration file](https://github.com/data-privacy-stack/presidio/blob/main/presidio-analyzer/presidio_analyzer/conf/ollama_config.yaml) for all options.

## Troubleshooting

**ConnectionError: "Ollama server not reachable"**
- Ensure Ollama is running: `docker ps` or check `http://localhost:11434`
- Verify the `model_url` in your configuration matches your Ollama server address

**RuntimeError: "Model 'qwen2.5:1.5b' not found"**
- Pull the model: `docker exec -it presidio-ollama-1 ollama pull qwen2.5:1.5b`
- Or for manual setup: `ollama pull qwen2.5:1.5b`
- Verify the model name matches the `model_id` in your configuration

---

## Using Azure OpenAI (Cloud Models)

Azure OpenAI provides cloud-based access to OpenAI models (GPT-4o, GPT-4, GPT-3.5-turbo) with enterprise security and compliance features.

### Prerequisites

1. **Install Presidio with LangExtract support**:
   ```sh
   pip install "presidio-analyzer[langextract]"
   ```
   
   This installs `langextract` with OpenAI support, including the OpenAI Python SDK and Azure Identity libraries.

2. **Azure Subscription**: Create one at [azure.microsoft.com](https://azure.microsoft.com)

3. **Azure OpenAI Resource**:
   - Create an Azure OpenAI resource in [Azure Portal](https://portal.azure.com)
   - Request access if needed (some regions require approval)
   - Deploy a model and note the **deployment name** you choose (e.g., "gpt-4", "my-gpt-deployment")

4. **Optional: Download config file** (only if customizing entities/prompts):

   ```sh
   # On macOS/Linux/PowerShell:
   wget https://raw.githubusercontent.com/data-privacy-stack/presidio/main/presidio-analyzer/presidio_analyzer/conf/langextract_config_azureopenai.yaml
   
   # Or download manually from:
   # https://github.com/data-privacy-stack/presidio/blob/main/presidio-analyzer/presidio_analyzer/conf/langextract_config_azureopenai.yaml
   ```

### Authentication Options

Azure OpenAI supports multiple authentication methods with flexible configuration:

#### Option 1: Direct Parameters (Recommended for Most Users)

Simplest approach - pass credentials and deployment name as parameters:

```python
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.predefined_recognizers import AzureOpenAILangExtractRecognizer

# Initialize with deployment name and credentials
azure_openai = AzureOpenAILangExtractRecognizer(
    model_id="gpt-4",  # Your Azure deployment name
    azure_endpoint="https://your-resource.openai.azure.com/",
    api_key="your-api-key-here",
    api_version="2024-02-15-preview"  # Optional
)

analyzer = AnalyzerEngine()
analyzer.registry.add_recognizer(azure_openai)

results = analyzer.analyze(
    text="My email is john.doe@example.com and my phone is 555-123-4567",
    language="en"
)
```

#### Option 2: Environment Variables

Use environment variables for credentials:

```python
import os
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.predefined_recognizers import AzureOpenAILangExtractRecognizer

# Set environment variables
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://your-resource.openai.azure.com/"
os.environ["AZURE_OPENAI_API_KEY"] = "your-api-key-here"

# Initialize with just deployment name
azure_openai = AzureOpenAILangExtractRecognizer(
    model_id="gpt-4"  # Your Azure deployment name
)

analyzer = AnalyzerEngine()
analyzer.registry.add_recognizer(azure_openai)

results = analyzer.analyze(
    text="My email is john.doe@example.com and my phone is 555-123-4567",
    language="en"
)
```

#### Option 3: Managed Identity (Production)

**More secure** - No API keys in code, uses Azure RBAC:

```python
import os
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.predefined_recognizers import AzureOpenAILangExtractRecognizer

# Set endpoint (no API key = uses managed identity)
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://your-resource.openai.azure.com/"

# Initialize without API key (uses managed identity)
azure_openai = AzureOpenAILangExtractRecognizer(
    model_id="gpt-4"  # Your Azure deployment name
)

analyzer = AnalyzerEngine()
analyzer.registry.add_recognizer(azure_openai)

results = analyzer.analyze(
    text="Patient John Smith has SSN 123-45-6789",
    language="en"
)
```

**Managed Identity Authentication Flow** (Production):

When `api_key` is not provided, the provider automatically uses `ChainedTokenCredential` which tries credentials in order:

1. **EnvironmentCredential** - Service principal from environment variables
2. **WorkloadIdentityCredential** - Azure Kubernetes Service workload identity
3. **ManagedIdentityCredential** - Azure VM/App Service managed identity

For local development, set `ENV=development` to use `DefaultAzureCredential` instead:

```python
import os
os.environ["ENV"] = "development"
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://your-resource.openai.azure.com/"
# AZURE_OPENAI_API_KEY not set - uses DefaultAzureCredential in development mode
# (includes Azure CLI, VS Code, etc.)

azure_openai = AzureOpenAILangExtractRecognizer()
```

**Setup Managed Identity**:

1. Enable managed identity on your Azure resource (VM, App Service, Container Instance, etc.)
2. Grant the managed identity **"Cognitive Services OpenAI User"** role on your Azure OpenAI resource
3. No API keys needed - authentication is automatic

See [Azure Managed Identity documentation](https://learn.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/overview) for details.

### Configuration File (Optional)

The configuration file is **optional** for basic usage. You only need it to customize:

- Supported entity types
- Entity mappings (LangExtract → Presidio)
- Prompts and examples
- Detection parameters

For basic usage, just pass `model_id` as a parameter (see examples above).

**When you need a custom config:**

1. **Download** the default config:

   ```sh
   wget https://raw.githubusercontent.com/data-privacy-stack/presidio/main/presidio-analyzer/presidio_analyzer/conf/langextract_config_azureopenai.yaml
   ```

2. **Customize** entities, prompts, or other settings in the file

3. **Use** the customized config:

   ```python
   recognizer = AzureOpenAILangExtractRecognizer(
       model_id="gpt-4",  # Can override config's model_id
       config_path="./custom_config.yaml",
       azure_endpoint="...",
       api_key="..."
   )
   ```

**Configuration Reference**:

The config file contains two main sections:

**`lm_recognizer` section** (LLM recognizer settings):

- `supported_entities`: List of PII/PHI entity types to detect
- `labels_to_ignore`: Entity labels to skip during processing
- `enable_generic_consolidation`: Whether to consolidate unknown entities to GENERIC_PII_ENTITY
- `min_score`: Minimum confidence score threshold (0.0-1.0)

**`langextract` section** (LangExtract-specific settings):

- `model.model_id`: Azure OpenAI deployment name (e.g., "gpt-4o", "gpt-4", "gpt-35-turbo")
- `model.temperature`: Model temperature for generation (null = use model default)
- `prompt_file`: Path to custom prompt template file
- `examples_file`: Path to few-shot examples file
- `entity_mappings`: Map LangExtract entity classes to Presidio entity names

See the [full config file](https://github.com/data-privacy-stack/presidio/blob/main/presidio-analyzer/presidio_analyzer/conf/langextract_config_azureopenai.yaml) for details.

---

## Using Ollama (Local Models)
