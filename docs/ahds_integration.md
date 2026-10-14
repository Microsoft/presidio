# Azure Health Data Services De-identification Service Integration

Presidio supports integration with Azure Health Data Services (AHDS) de-identification service for both entity recognition and anonymization with realistic surrogate generation.

## Resources

- [Azure Health Data Services Documentation](https://learn.microsoft.com/azure/healthcare-apis/deidentification/)
- [Azure Health Deidentification Python SDK](https://pypi.org/project/azure-health-deidentification/)

## Overview

The AHDS de-identification service integration provides two main capabilities:

1. **AHDS Recognizer** (in presidio-analyzer): Detects PHI entities using the Azure Health Data Services de-identification service
2. **AHDS Surrogate Operator** (in presidio-anonymizer): Replaces PHI entities with realistic surrogates using the de-identification service

## Benefits of Surrogation

- **Maintains Data Utility**: Preserves structure and format for downstream analytics
- **Realistic Healthcare Context**: Generates medically plausible names, dates, and identifiers
- **Consistent Cross-References**: Same entity gets same surrogate throughout document
- **Format Preservation**: Maintains original formatting and linguistic patterns

## Installation

### For AHDS Recognizer
```bash
pip install "presidio-analyzer[ahds]"
```

### For AHDS Surrogate Operator
```bash
pip install "presidio-anonymizer[ahds]"
```

## Prerequisites

- [Azure Health Data Services de-identification service endpoint](https://learn.microsoft.com/azure/healthcare-apis/deidentification/quickstart)
- [Azure role-based access control configured](https://learn.microsoft.com/azure/healthcare-apis/deidentification/manage-access-rbac)
- Environment variables:
  - `AHDS_ENDPOINT`: Your AHDS de-identification service endpoint

## Complete Workflow Example

```python
import os
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

# Set your AHDS endpoint
os.environ["AHDS_ENDPOINT"] = "https://your-ahds-endpoint.api.eus001.deid.azure.com"

# Initialize engines
analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()

# Medical text with PHI
text = "Patient John Doe was seen by Dr. Smith on 2024-01-15 for diabetes treatment."

# Step 1: Detect entities using AHDS recognizer
analyzer_results = analyzer.analyze(
    text=text,
    entities=["PATIENT", "DOCTOR", "DATE"],
    language="en"
)

# Step 2: Anonymize using AHDS surrogate generation
result = anonymizer.anonymize(
    text=text,
    analyzer_results=analyzer_results,
    operators={
        "DEFAULT": OperatorConfig("surrogate", {
            "entities": analyzer_results,
            "input_locale": "en-US",
            "surrogate_locale": "en-US"
        })
    },
)

print(f"Original: {text}")
print(f"Anonymized: {result.text}")
# Output: "Patient Michael Johnson was seen by Dr. Brown on 1987-06-23 for diabetes treatment."
```

**Note:** This example uses the Azure Health Data Services de-identification service surrogation, which provides superior data utility by generating realistic, medically-appropriate surrogates while maintaining document structure and relationships.

## Configuration Options

### AHDS Surrogate Operator Parameters

- `endpoint`: AHDS de-identification service endpoint (optional, uses `AHDS_ENDPOINT` env var)
- `entities`: List of entities detected by analyzer
- `input_locale`: Input locale (default: "en-US")
- `surrogate_locale`: Surrogate locale (default: "en-US")

## Authentication

The AHDS de-identification service integration uses Azure authentication with a secure-by-default approach:

### Production Mode (Default)

By default, the integration uses a restricted credential chain that only includes:

1. **EnvironmentCredential**: Service Principal via environment variables
2. **WorkloadIdentityCredential**: Workload Identity (Kubernetes)
3. **ManagedIdentityCredential**: Managed Identity (Azure services)

This credential chain is more secure as it excludes interactive browser logins and developer credentials, making it suitable for production deployments.

### Development Mode

For local development, you can enable `DefaultAzureCredential` by setting the environment variable:

```bash
export ENV=development
```

In development mode, the integration uses `DefaultAzureCredential`, which supports additional authentication methods:

1. Environment variables (Service Principal)
2. Workload Identity
3. Managed Identity
4. Azure CLI (`az login`)
5. Azure PowerShell
6. Visual Studio/VS Code credentials
7. Interactive browser login

### Local Development Setup

For local development with Azure CLI authentication:

```bash
# Set development mode
export ENV=development

# Login with Azure CLI
az login

# Set your AHDS endpoint
export AHDS_ENDPOINT="https://your-ahds-endpoint.api.eus001.deid.azure.com"

# Now you can run Presidio with AHDS integration
python your_script.py
```

### Production Deployment Recommendations

For production deployments, we recommend:

1. **Do not set ENV=development** (use default production mode)
2. **Use Managed Identity** when running on Azure services (AKS, App Service, Functions, etc.)
3. **Use Workload Identity** for Kubernetes deployments
4. **Use Service Principal** with environment variables for other scenarios:
   ```bash
   export AZURE_CLIENT_ID="<client-id>"
   export AZURE_CLIENT_SECRET="<client-secret>"
   export AZURE_TENANT_ID="<tenant-id>"
   ```

### Environment Variables Summary

- `AHDS_ENDPOINT`: Your AHDS de-identification service endpoint (required)
- `ENV`: Set to `development` for local dev, omit for production (optional, default: production mode)

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError**: Install the AHDS optional dependencies
   ```bash
   pip install "presidio-analyzer[ahds]" "presidio-anonymizer[ahds]"
   ```

2. **Authentication errors**: Ensure Azure credentials are properly configured
   ```bash
   az login  # For local development
   ```

3. **Endpoint not found**: Verify the `AHDS_ENDPOINT` environment variable is set correctly

### Testing without AHDS

The AHDS operators gracefully handle missing dependencies and will be skipped if not available. Tests will be automatically skipped if the `AHDS_ENDPOINT` environment variable is not set.

## See Also

- [Presidio Analyzer](../analyzer/index.md)
- [Presidio Anonymizer](../anonymizer/index.md)
- [Azure Health Data Services de-identification service documentation](https://learn.microsoft.com/azure/healthcare-apis/deidentification/)
