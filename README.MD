# Presidio - Data Protection and De-identification SDK
## :mega: Presidio has moved to a new home! [Read more here](docs/project_transition.md) :mega:
**Context aware, pluggable and customizable PII de-identification service for text and images.**

---

[![Build Status](https://github.com/data-privacy-stack/presidio/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/data-privacy-stack/presidio/actions/workflows/ci.yml)
[![MIT license](https://img.shields.io/badge/license-MIT-brightgreen.svg)](http://opensource.org/licenses/MIT)
![Release](https://img.shields.io/github/release/data-privacy-stack/presidio.svg)
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/6076/badge)](https://www.bestpractices.dev/projects/6076)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/presidio-analyzer.svg)](https://pypi.python.org/pypi/presidio-analyzer/)
[![Discord](https://img.shields.io/badge/Discord-Join%20the%20community-5865F2?logo=discord&logoColor=white)](https://discord.gg/MewtBGFquB)

| Component | Downloads | Coverage |
|-----------|-----------|----------|
| Presidio Analyzer | [![Pypi Downloads](https://img.shields.io/pypi/dm/presidio-analyzer.svg)](https://pypi.python.org/pypi/presidio-analyzer/) | [![Coverage](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/data-privacy-stack/presidio/coverage-data-presidio-analyzer/endpoint.json)](https://github.com/data-privacy-stack/presidio/tree/coverage-data-presidio-analyzer) |
| Presidio Anonymizer | [![Pypi Downloads](https://img.shields.io/pypi/dm/presidio-anonymizer.svg)](https://pypi.python.org/pypi/presidio-anonymizer/) | [![Coverage](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/data-privacy-stack/presidio/coverage-data-presidio-anonymizer/endpoint.json)](https://github.com/data-privacy-stack/presidio/tree/coverage-data-presidio-anonymizer) |
| Presidio Image-Redactor | [![Pypi Downloads](https://img.shields.io/pypi/dm/presidio-image-redactor.svg)](https://pypi.python.org/pypi/presidio-image-redactor/) | [![Coverage](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/data-privacy-stack/presidio/coverage-data-presidio-image-redactor/endpoint.json)](https://github.com/data-privacy-stack/presidio/tree/coverage-data-presidio-image-redactor) |
| Presidio Structured | [![Pypi Downloads](https://img.shields.io/pypi/dm/presidio-structured.svg)](https://pypi.python.org/pypi/presidio-structured/) | [![Coverage](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/data-privacy-stack/presidio/coverage-data-presidio-structured/endpoint.json)](https://github.com/data-privacy-stack/presidio/tree/coverage-data-presidio-structured) |
## What is Presidio

Presidio _(Origin from Latin praesidium ‘protection, garrison’)_ helps to ensure sensitive data is properly managed and governed. It provides fast **_identification_** and **_anonymization_** modules for private entities in text such as credit card numbers, names, locations, social security numbers, bitcoin wallets, US phone numbers, financial data and more.

![Presidio demo gif](docs/assets/changing_text.gif)

---

### :blue_book: [Full documentation](https://data-privacy-stack.github.io/presidio)

### :mega: [Project transition update](docs/project_transition.md)

### :question: [Frequently Asked Questions](docs/faq.md)

### :thought_balloon: [Demo](https://huggingface.co/spaces/presidio/presidio_demo)

### :flight_departure: [Examples](https://data-privacy-stack.github.io/presidio/samples/)

---


### Goals

- Allow organizations to preserve privacy in a simpler way by democratizing de-identification technologies and introducing transparency in decisions.
- Embrace extensibility and customizability to a specific business need.
- Facilitate both fully automated and semi-automated PII de-identification flows on multiple platforms.

### Main features

1. **Predefined** or **custom PII recognizers** leveraging _Named Entity Recognition_, _regular expressions_, _rule based logic_ and _checksum_ with relevant context in multiple languages.
2. Options for connecting to external PII detection models.
3. Multiple usage options, **from Python or PySpark workloads through Docker to Kubernetes**.
4. **Customizability** in PII identification and de-identification.
5. Module for **redacting PII text in images** (standard image types and DICOM medical images).

:warning: Presidio can help identify sensitive/PII data in un/structured text. However, because it is using automated detection mechanisms, there is no guarantee that Presidio will find all sensitive information. Consequently, additional systems and protections should be employed.

## Installing Presidio

1. [Using pip](https://data-privacy-stack.github.io/presidio/installation/#using-pip)
2. [Using Docker](https://data-privacy-stack.github.io/presidio/installation/#using-docker)
3. [From source](https://data-privacy-stack.github.io/presidio/installation/#install-from-source)
4. [Migrating from V1 to V2](./docs/presidio_V2.md)

## Running Presidio

1. [Getting started](https://data-privacy-stack.github.io/presidio/getting_started)
2. [Setting up a development environment](https://data-privacy-stack.github.io/presidio/development)
3. [PII de-identification in text](https://data-privacy-stack.github.io/presidio/text_anonymization)
4. [PII de-identification in images](https://data-privacy-stack.github.io/presidio/image-redactor)
5. [Usage samples and example deployments](https://data-privacy-stack.github.io/presidio/samples)

---

## Support

- Before you submit an issue, please go over the [documentation](https://data-privacy-stack.github.io/presidio/).
- For general discussions, please use the [GitHub repo's discussion board](https://github.com/data-privacy-stack/presidio/discussions).
- If you have a usage question, found a bug or have a suggestion for improvement, please file a [GitHub issue](https://github.com/data-privacy-stack/presidio/issues).
- For other matters, please email [presidio@dataprivacystack.org](mailto:presidio@dataprivacystack.org).

## Contributing

For details on contributing to this repository, see the [contributing guide](CONTRIBUTING.md).

This project has adopted the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).

## Contributors

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->
<!-- ALL-CONTRIBUTORS-LIST:END -->
<a href="https://github.com/data-privacy-stack/presidio/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=data-privacy-stack/presidio" />
</a>
