# Presidio CLI

[![PyPI license](https://img.shields.io/pypi/l/presidio-cli.svg)](https://pypi.python.org/pypi/presidio-cli/)
[![PyPI version](https://badge.fury.io/py/presidio-cli.svg)](https://badge.fury.io/py/presidio-cli)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://GitHub.com/Naereen/StrapDown.js/graphs/commit-activity)
[![PyPI download month](https://img.shields.io/pypi/dm/presidio-cli.svg)](https://pypi.python.org/pypi/presidio-cli/)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/presidio-cli.svg)](https://pypi.python.org/pypi/presidio-cli/)

CLI tool that analyzes text for PII Entities using Presidio Analyzer.

## Prerequisites

`Python` version: 3.10, 3.11, 3.12, 3.13

`poetry` tool installed:

```shell
# check if app is installed
poetry --version

# install, if not available
pip install poetry
```

## Install `presidio-cli` in a virtual env

### Install from Python Package Index

install in current python env

```shell
python -m pip install presidio-cli
```

install required apps and presidio-cli in virtual environment

```shell
poetry add presidio-cli
```

### Install from source

```shell
# clone from git
git clone https://github.com/data-privacy-stack/presidio
cd presidio/presidio-cli
# install required apps and presidio-cli
poetry install
```

## Install language models for `spaCy`

Load models for the English (en) language using the command presented below. For further information please visit section [models](https://spacy.io/models/en).

```shell
python -m spacy download en_core_web_lg
```

## Configuration file syntax

The default configuration is taken from the `.presidiocli` file in a current directory.

Configuration file supports the following parameters in a yaml file:

- language - the expected language for PII detection. Default is `en`. For supporting additional languages, see [this documentation](https://presidio.dataprivacystack.org/analyzer/languages/)

- entities - list of entities to recognize. Maps to the `entities` field in presidio-analyzer. If empty, returns all [supported entities](https://presidio.dataprivacystack.org/supported_entities/) for this input language.

- ignore - list of ignored files/folders/directories based on pattern. It is recommended to ignore `Version Control` files, for example `.git`

- allow - list of tokens that should not be marked as PII.

- threshold - only show problems/findings whose scores are at or above this threshold. Must be a number between 0 and 1.

Note: a file requires at least one parameter to be set.

An example of yaml configuration file content:

```yaml
---
language: en
ignore: |
  .git
  *.cfg
entities:
  - PERSON
  - CREDIT_CARD
  - EMAIL_ADDRESS
allow:
  - "allowed token 1"
  - "allowed token 2"
threshold: 0.8

```

## Run the Presidio CLI

Run the Presidio CLI to execute [Presidio Analyzer](https://presidio.dataprivacystack.org/analyzer/)
with specified configuration: language, threshold, entities and ignore pre-configured files/paths.

### Configuration from a file

An example of running script with configuration from a file.

There are two example `.yaml` configuration files in the [`conf`](presidio_cli/conf) directory:

- [default.yaml](presidio_cli/conf/default.yaml) - ignore the `.git` directory
- [limited.yaml](presidio_cli/conf/limited.yaml) - limit list of entities used to only 3 of them, ignore `.git` directory and `.cfg` files.

```shell
# run with default configuration (file `.presidiocli`) in the current directory
presidio .

# run with configuration limited.yaml in the "tests" directory
presidio -c presidio_cli/conf/limited.yaml tests/

# run with configuration limited.yaml in single file only tests/test_analyzer.py
presidio -c presidio_cli/conf/limited.yaml tests/test_analyzer.py
```

### Threshold override

Use `--threshold` to override the loaded config for a single run:

```shell
presidio --threshold 0.7 tests/
```

The CLI keeps the existing selection order: `--config-data`, `--config-file`, `.presidiocli`, then the default config. The command-line flag only changes the in-memory threshold after that config is loaded.

### Configuration as a parameter

An example of using configuration as data in parameter:

```shell
# ignore paths .git and *.cfg
presidio -d "ignore: |
  .git
  *.cfg" tests/

# limit list of entities to CREDIT_CARD
presidio -d "entities:
  - CREDIT_CARD" tests/

# equivalent to use -c parameter
presidio -d "$(cat presidio_cli/conf/limited.yaml)" tests/
```

### Formatting output

Output can be formatted using `-f` or `--format` parameter. The default format is `auto`.

Available formats:

- standard - standard output format

```shell
presidio -d "entities:
  - PERSON" -f standard tests/conftest.py
# result
tests/conftest.py
  34:58     0.85     PERSON
  37:33     0.85     PERSON
```

- github - [GitHub Actions workflow commands](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands) that create a `warning` or `error` annotation for each finding

```shell
presidio -d "entities:
  - PERSON" -f github tests/conftest.py
# result
::group::tests/conftest.py
::warning file=tests/conftest.py,line=34,col=58::34:58 [PERSON] score=0.85
::warning file=tests/conftest.py,line=37,col=33::37:33 [PERSON] score=0.85
::endgroup::
```

- colored - standard output format but with colors: error scores are red, warning scores are yellow

- parsable - easy to parse automaticaly

```shell
presidio -d "entities:
  - PERSON" -f parsable tests/conftest.py
# result
{"entity_type": "PERSON", "start": 57, "end": 62, "score": 0.85, "analysis_explanation": null}
{"entity_type": "PERSON", "start": 32, "end": 37, "score": 0.85, "analysis_explanation": null}
```

- auto - default format, switches automatically between those 2 modes:
  - github, if run on github - environment variables `GITHUB_ACTIONS` and `GITHUB_WORKFLOW` are set
  - colored, otherwise

### Warnings and errors

Each finding has a level based on its score:

- error - the score is 1.0
- warning - the score is below 1.0

Use `--no-warnings` to output only error-level findings:

```shell
presidio --no-warnings tests/
```

### Exit codes

- `0` - no findings were output
- `1` - at least one finding was output, or the configuration is invalid
- `2` - invalid command-line arguments

Findings filtered out by `threshold` or `--no-warnings` do not affect the exit code. To report findings without failing a CI step, ignore the exit code:

```shell
presidio . || true
```

### List of all parameters

Simply run the following to get a list of all available options for the CLI:

```shell
presidio --help
```
