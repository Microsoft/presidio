# Samples

| Topic       |     Data Type     |Resource                                  | Sample                                                                                                                                          |
| :---------- |:--------------------------------------| :---------------------------------| :---------------------------------------------------------------------------------------------------------------------------------------------- |
| Usage | Text      | Python Notebook                        | [Presidio Basic Usage Notebook](python/presidio_notebook.ipynb)  |
| Usage | Text       | Python Notebook                       | [Customizing Presidio Analyzer](python/customizing_presidio_analyzer.ipynb) |
| Usage | Text       | Python Notebook                       | [Configuring The NLP engine](python/ner_model_configuration.ipynb) |
| Usage | Semi-structured       | Python Notebook            | [Analyzing structured / semi-structured data in batch](python/batch_processing.ipynb)|
| Usage | Text       | Python Notebook                       | [Encrypting and Decrypting identified entities](python/encrypt_decrypt.ipynb)|
| Usage | Text       | Python Notebook                       | [Getting the identified entity value using a custom Operator](python/getting_entity_values.ipynb)|
| Usage | text       | Python Notebook                       | [Anonymizing known values](python/Anonymizing%20known%20values.ipynb)
| Usage | Images       | Python Notebook                     | [Redacting Text PII from DICOM images](python/example_dicom_image_redactor.ipynb)
| Usage | Images        | Python Notebook                    | [Using an allow list with image redaction](python/image_redaction_allow_list_approach.ipynb)
| Usage | PDF   | Python Notebook                            | [Annotating PII in a PDF](python/example_pdf_annotation.ipynb)
| Usage | Images     | Python Notebook                       | [Plot custom bounding boxes](python/plot_custom_bboxes.ipynb)
| Usage | Text     | Python Notebook                         | [Integrating with external services](python/integrating_with_external_services.ipynb) |
| Usage | Text       | Python file                           | [Remote Recognizer](python/example_remote_recognizer.py) |
| Usage | Structured     | Python Notebook                   | [Presidio Structured Basic Usage Notebook](python/example_structured.ipynb) |
| Usage | Text      | Python file                            | [Azure AI Language as a Remote Recognizer](python/text_analytics/index.md)  |
| Usage | Text      | Python file                            | [Azure Health Data Services de-identification Service as a Remote Recognizer](python/ahds/index.md)  |
| Usage | Text      | Python file                            | [AHDS Surrogate Example](python/ahds/example_ahds_surrogate.py)  |
| Usage | Text      | Python file                            | [Language Model-based PII/PHI Detection using LangExtract](python/langextract/index.md)  |
| Usage | CSV       | Python file                            | [Analyze and Anonymize CSV file](https://github.com/data-privacy-stack/presidio/blob/main/docs/samples/python/process_csv_file.py) |
| Usage | Text      | Python                                 | [Using Flair as an external PII model](https://github.com/data-privacy-stack/presidio/blob/main/docs/samples/python/flair_recognizer.py)|
| Usage | Text      | Python file                            | [Using Span Marker as an external PII model](https://github.com/data-privacy-stack/presidio/blob/main/docs/samples/python/span_marker_recognizer.py)|
| Usage | Text      | Python file                            | [Using Transformers as an external PII model](python/transformers_recognizer/index.md)|
| Usage | Text      | Python file                            | [Pseudonymization (replace PII values using mappings)](python/pseudonymization.ipynb)|
| Usage | Text      | Python file                            | [Passing a lambda as a Presidio anonymizer using Faker](python/example_custom_lambda_anonymizer.py)|
| Usage | Text      | Python file                            | [Synthetic data generation with OpenAI](python/synth_data_with_openai.ipynb)|
| Usage | Text      | Python file                            | [Keeping some entities from being anonymized](python/keep_entities.ipynb)|
| Usage | Text     | LiteLLM Proxy                           | [PII Masking LLM calls across Anthropic/Gemini/Bedrock/Azure, etc.](docker/litellm.md)|
| Usage | Text     | AISIX AI Gateway                        | [Protect LLM requests with Presidio and AISIX AI Gateway](docker/aisix.md)|
| Usage | Text     | Python Notebook                         | [YAML based no-code configuration](python/no_code_config.ipynb) |
| Usage | Text     | Python file                             | [Using GLiNER within Presidio](python/gliner.md) |
| Usage      | | REST API (postman)                          | [Presidio as a REST endpoint](docker/index.md)|
| Deployment | | App Service                                 | [Presidio with App Service](deployments/app-service/index.md)|
| Deployment | | Kubernetes                                  | [Presidio with Kubernetes](deployments/k8s/index.md)|
| Deployment | | Spark/Azure Databricks                      | [Presidio with Spark](deployments/spark/index.md)|
| Deployment | | OpenTelemetry/Grafana                       | [Redacting Telemetry with Presidio](deployments/redacting-telemetry/index.md)|
| Deployment | | Data Protection toolkit for OpenAI          | [Data Protection toolkit for OpenAI](deployments/openai-anonymaztion-and-deanonymaztion-best-practices/index.md)|
| Deployment | | Spark with Microsoft Fabric                 | [Presidio with Fabric](fabric/index.md)|
| Deployment | | Azure Data Factory with App Service         | [ETL for small dataset](deployments/data-factory/presidio-data-factory.md#option-1-presidio-as-an-http-rest-endpoint) |
| Deployment | | Azure Data Factory with Databricks          | [ETL for large datasets](deployments/data-factory/presidio-data-factory.md#option-2-presidio-on-azure-databricks) |
| ADF Pipeline | | Azure Data Factory                        | [Add Presidio as an HTTP service to your Azure Data Factory](deployments/data-factory/presidio-data-factory-template-gallery-http.md) |
| ADF Pipeline | | Azure Data Factory                        | [Add Presidio on Databricks to your Azure Data Factory](deployments/data-factory/presidio-data-factory-template-gallery-databricks.md) |
| Demo |  | Streamlit app                                    | [Create a simple demo app using Streamlit](python/streamlit/index.md)
