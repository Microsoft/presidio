"""LangExtract helper utilities."""

import logging
from typing import Dict, List, Optional

from presidio_analyzer import AnalysisExplanation, RecognizerResult

logger = logging.getLogger("presidio-analyzer")

try:
    import langextract as lx
    import langextract.factory as lx_factory

    # Make sure builtin providers are pre-loaded to work around a bug in LangExtract
    # that fails to load them automatically if the provider name is specified for a
    # built-in provider rather than inferred from the model_id.
    lx.providers.load_builtins_once()
    lx.providers.load_plugins_once()
except ImportError:
    lx = None
    lx_factory = None

__all__ = [
    "lx",
    "lx_factory",
    "check_langextract_available",
    "extract_lm_config",
    "get_supported_entities",
    "create_reverse_entity_mapping",
    "calculate_extraction_confidence",
    "convert_langextract_to_presidio_results",
]


def check_langextract_available():
    """Check if langextract is available and raise error if not."""
    if not lx:
        raise ImportError(
            "LangExtract is not installed. "
            "Install it with: poetry install --extras langextract"
        )


# Default alignment score mappings for LangExtract extractions
DEFAULT_ALIGNMENT_SCORES = {
    "MATCH_EXACT": 0.95,
    "MATCH_FUZZY": 0.80,
    "MATCH_LESSER": 0.70,
    "NOT_ALIGNED": 0.60,
}


def extract_lm_config(config: Dict) -> Dict:
    """Extract LM recognizer configuration section with default values.

    :param config: Full configuration dictionary.
    :return: LM recognizer config with keys: supported_entities, min_score,
             labels_to_ignore, enable_generic_consolidation.
    """
    lm_config_section = config.get("lm_recognizer", {})

    return {
        "supported_entities": lm_config_section.get("supported_entities"),
        "min_score": lm_config_section.get("min_score", 0.5),
        "labels_to_ignore": lm_config_section.get("labels_to_ignore", []),
        "enable_generic_consolidation": lm_config_section.get(
            "enable_generic_consolidation", True
        ),
    }


def get_supported_entities(
    lm_config: Dict, langextract_config: Dict
) -> Optional[List[str]]:
    """Get supported entities list, checking LM config first then LangExtract config.

    :param lm_config: LM recognizer configuration dictionary.
    :param langextract_config: LangExtract configuration dictionary.
    :return: List of supported entity types, or None if not specified.
    """
    return lm_config.get("supported_entities") or langextract_config.get(
        "supported_entities"
    )


def create_reverse_entity_mapping(entity_mappings: Dict) -> Dict:
    """Create reverse mapping from values to keys.

    :param entity_mappings: Original entity mapping dictionary.
    :return: Reversed dictionary mapping values to keys.
    """
    return {v: k for k, v in entity_mappings.items()}


def calculate_extraction_confidence(
    extraction, alignment_scores: Optional[Dict[str, float]] = None
) -> float:
    """Calculate confidence score based on extraction alignment status.

    :param extraction: LangExtract extraction object with optional alignment_status.
    :param alignment_scores: Custom score mapping for alignment statuses (optional).
    :return: Confidence score between 0.0 and 1.0.
    """
    default_score = 0.85

    if alignment_scores is None:
        alignment_scores = DEFAULT_ALIGNMENT_SCORES

    if not hasattr(extraction, "alignment_status") or not (extraction.alignment_status):
        return default_score

    status = str(extraction.alignment_status).upper()
    for status_key, score in alignment_scores.items():
        if status_key in status:
            return score

    return default_score


def convert_langextract_to_presidio_results(
    langextract_result,
    entity_mappings: Dict,
    supported_entities: List[str],
    enable_generic_consolidation: bool,
    recognizer_name: str,
    alignment_scores: Optional[Dict[str, float]] = None,
) -> List[RecognizerResult]:
    """Convert LangExtract extraction results to Presidio RecognizerResult objects.

    :param langextract_result: LangExtract result object with extractions.
    :param entity_mappings: Mapping of extraction classes to Presidio entity types.
    :param supported_entities: List of supported Presidio entity types.
    :param enable_generic_consolidation: Whether to consolidate unknown entities.
    :param recognizer_name: Name of recognizer for result metadata.
    :param alignment_scores: Custom alignment score mappings (optional).
    :return: List of Presidio RecognizerResult objects.
    """
    results = []
    if not langextract_result or not langextract_result.extractions:
        return results

    supported_entities_set = set(supported_entities)

    for extraction in langextract_result.extractions:
        extraction_class = extraction.extraction_class

        if extraction_class in supported_entities_set:
            entity_type = extraction_class
        else:
            extraction_class_lower = extraction_class.lower()
            entity_type = entity_mappings.get(extraction_class_lower)

        if not entity_type:
            if enable_generic_consolidation:
                entity_type = extraction_class.upper()
                logger.debug(
                    "Unknown extraction class '%s' will be consolidated to "
                    "GENERIC_PII_ENTITY",
                    extraction_class,
                )
            else:
                logger.warning(
                    "Unknown extraction class '%s' not found in entity "
                    "mappings, skipping",
                    extraction_class,
                )
                continue

        if not extraction.char_interval:
            logger.warning("Extraction missing char_interval, skipping")
            continue

        confidence = calculate_extraction_confidence(extraction, alignment_scores)

        metadata = {}
        if hasattr(extraction, "attributes") and extraction.attributes:
            metadata["attributes"] = extraction.attributes
        if hasattr(extraction, "alignment_status") and extraction.alignment_status:
            metadata["alignment"] = str(extraction.alignment_status)

        explanation = AnalysisExplanation(
            recognizer=recognizer_name,
            original_score=confidence,
            textual_explanation=(
                f"LangExtract extraction with {extraction.alignment_status} alignment"
                if hasattr(extraction, "alignment_status")
                and extraction.alignment_status
                else "LangExtract extraction"
            ),
        )

        result = RecognizerResult(
            entity_type=entity_type,
            start=extraction.char_interval.start_pos,
            end=extraction.char_interval.end_pos,
            score=confidence,
            analysis_explanation=explanation,
            recognition_metadata=metadata if metadata else None,
        )

        results.append(result)

    return results
