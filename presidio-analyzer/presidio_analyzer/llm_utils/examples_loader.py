"""Examples loading utilities for LLM recognizers."""

import logging
from typing import Dict, List

from .config_loader import load_yaml_file, resolve_config_path, validate_config_fields
from .langextract_helper import check_langextract_available, lx

logger = logging.getLogger("presidio-analyzer")

__all__ = [
    "load_yaml_examples",
    "convert_to_langextract_format",
]


def load_yaml_examples(examples_file: str, conf_subdir: str = "conf") -> List[Dict]:
    """Load and validate examples from YAML configuration file.

    :param examples_file: Path to YAML file with examples (repo-root-relative).
    :param conf_subdir: Configuration subdirectory (deprecated, kept for compatibility).
    :return: List of example dictionaries.
    :raises ValueError: If 'examples' field is missing.
    """
    filepath = resolve_config_path(examples_file)
    data = load_yaml_file(filepath)
    validate_config_fields(data, ["examples"], "Examples file")
    return data["examples"]


def convert_to_langextract_format(examples_data: List[Dict]) -> List:
    """Convert example dictionaries to LangExtract Example objects.

    :param examples_data: List of example dictionaries with text and extractions.
    :return: List of LangExtract Example objects.
    :raises ImportError: If langextract is not installed.
    """
    check_langextract_available()

    langextract_examples = []
    for example in examples_data:
        extractions = [
            lx.data.Extraction(
                extraction_class=ext["extraction_class"],
                extraction_text=ext["extraction_text"],
                attributes=ext.get("attributes", {}),
            )
            for ext in example.get("extractions", [])
        ]

        langextract_examples.append(
            lx.data.ExampleData(text=example["text"], extractions=extractions)
        )

    return langextract_examples
