"""Install the default NLP models defined in the provided yaml file."""

import argparse
import logging
from typing import Dict, Optional, Union

import yaml
from spacy.cli import download as spacy_download

try:
    import stanza
except ImportError:
    # stanza should be installed manually
    stanza = None

try:
    import transformers
    from huggingface_hub import snapshot_download
    from transformers import AutoModelForTokenClassification, AutoTokenizer
except ImportError:
    # transformers should be installed manually
    transformers = None

logger = logging.getLogger()
logger.setLevel("INFO")
logger.addHandler(logging.StreamHandler())


def install_models(
    nlp_conf_file: Optional[str] = None, analyzer_conf_file: Optional[str] = None
) -> None:
    """
    Install NLP models based on configuration files.

    :param nlp_conf_file: Path to NLP configuration YAML file.
    :param analyzer_conf_file: Optional analyzer configuration file
        which may include NLP configuration.
    """
    # Prefer nlp_configuration embedded inside a unified ANALYZER_CONF_FILE.
    if analyzer_conf_file:
        try:
            with open(analyzer_conf_file) as fh:
                analyzer_config = yaml.safe_load(fh)
        except OSError as e:
            raise OSError(
                f"Could not read analyzer conf file '{analyzer_conf_file}'"
            ) from e
        if analyzer_config and "nlp_configuration" in analyzer_config:
            logger.info(
                "Using nlp_configuration from analyzer conf file: %s",
                analyzer_conf_file,
            )
            _install_models_from_nlp_config(analyzer_config["nlp_configuration"])
            return

    # Fall back to the plain NLP conf file (backward-compatible path).
    try:
        with open(nlp_conf_file) as fh:
            nlp_configuration = yaml.safe_load(fh)
    except OSError as e:
        raise OSError(f"Could not read NLP conf file '{nlp_conf_file}'") from e
    _install_models_from_nlp_config(nlp_configuration)


def _install_models_from_nlp_config(nlp_configuration: dict) -> None:
    """Download all models described in an nlp_configuration dict.

    :param nlp_configuration: Dict with at least ``nlp_engine_name`` and
        ``models`` keys (i.e. the content of a plain NLP conf file, or the
        value of the ``nlp_configuration`` key in a unified analyzer conf).
    """
    logger.info(f"Installing models from configuration: {nlp_configuration}")

    if "nlp_engine_name" not in nlp_configuration:
        raise ValueError("NLP config file should contain an nlp_engine_name field")

    if "models" not in nlp_configuration:
        raise ValueError("NLP config file should contain a list of models")

    for model in nlp_configuration["models"]:
        engine_name = nlp_configuration["nlp_engine_name"]
        model_name = model["model_name"]
        _download_model(engine_name, model_name)

    logger.info("finished installing models")


def _download_model(engine_name: str, model_name: Union[str, Dict[str, str]]) -> None:
    if engine_name == "spacy" or engine_name == "slim":
        spacy_download(model_name)
    elif engine_name == "stanza":
        if stanza:
            stanza.download(model_name)
        else:
            raise ImportError("stanza is not installed")
    elif engine_name == "transformers":
        if transformers:
            _install_transformers_spacy_models(model_name)
        else:
            raise ImportError("transformers is not installed")
    elif engine_name == "no_op":
        logger.info("No NLP model installation required for no_op engine")
    else:
        raise ValueError(f"Unsupported nlp engine: {engine_name}")


def _install_transformers_spacy_models(model_name: Dict[str, str]) -> None:
    if "spacy" not in model_name:
        raise ValueError(
            "transformers config should contain "
            "a spacy model/pipeline such as en_core_web_sm"
        )
    if "transformers" not in model_name:
        raise ValueError(
            "transformers config should contain a path to a transformers model"
        )

    spacy_model = model_name["spacy"]
    transformers_model = model_name["transformers"]

    # download spacy model/pipeline
    logger.info(f"Installing spaCy model: {spacy_model}")
    spacy_download(spacy_model)

    # download transformers model
    logger.info(f"Installing transformers model: {transformers_model}")
    snapshot_download(repo_id=transformers_model)

    # Instantiate to make sure it's downloaded during installation and not runtime
    AutoTokenizer.from_pretrained(transformers_model)
    AutoModelForTokenClassification.from_pretrained(transformers_model)


if __name__ == "__main__":
    import warnings

    parser = argparse.ArgumentParser(
        description="Install NLP models into the presidio-analyzer Docker container"
    )
    parser.add_argument(
        "--conf_file",
        required=False,
        default=None,
        help="Deprecated. Use --nlp_conf_file instead.",
    )
    parser.add_argument(
        "--nlp_conf_file",
        required=False,
        default=None,
        help="Location of nlp configuration yaml file. Default: conf/default.yaml",
    )
    parser.add_argument(
        "--analyzer_conf_file",
        required=False,
        default=None,
        help=(
            "Optional path to an analyzer conf file which may include "
            "NLP configuration. When provided, --nlp_conf_file is ignored."
        ),
    )
    args = parser.parse_args()

    if args.conf_file and args.nlp_conf_file:
        parser.error(
            "--conf_file and --nlp_conf_file cannot be used together. "
            "Use --nlp_conf_file only."
        )

    if args.conf_file:
        warnings.warn(
            "--conf_file is deprecated and will be removed in a future version. "
            "Use --nlp_conf_file instead.",
            DeprecationWarning,
            stacklevel=1,
        )
        args.nlp_conf_file = args.conf_file

    install_models(
        nlp_conf_file=args.nlp_conf_file or "presidio_analyzer/conf/default.yaml",
        analyzer_conf_file=args.analyzer_conf_file,
    )
