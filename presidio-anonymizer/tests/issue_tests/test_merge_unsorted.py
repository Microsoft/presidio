import pytest
from presidio_anonymizer import AnonymizerEngine
from presidio_analyzer import RecognizerResult


def test_merge_entities_when_unsorted():
    """
    Test that entities are correctly merged even when the input list
    is not sorted by start position.
    This reproduces the bug from Issue #1090 and #1573.
    """
    engine = AnonymizerEngine()
    
    # The original text
    text = "My name is Dave Jones"
    
    # Create unsorted results: "Jones" (start=16) comes before "Dave" (start=11)
    # Text: "My name is Dave Jones"
    #                     ^^^^ (start=11, end=15)
    #                           ^^^^^ (start=16, end=21)
    unsorted_results = [
        RecognizerResult(entity_type="PERSON", start=16, end=21, score=0.85),  # "Jones"
        RecognizerResult(entity_type="PERSON", start=11, end=15, score=0.85),  # "Dave"
    ]
    
    # Call the internal merge method with both text and analyzer_results
    merged = engine._merge_entities_with_spaces_between(
        text=text, 
        analyzer_results=unsorted_results
    )
    
    # Should merge into ONE entity covering "Dave Jones"
    assert len(merged) == 1, f"Expected 1 merged entity, got {len(merged)}"
    assert merged[0].entity_type == "PERSON"
    assert merged[0].start == 11, f"Expected start=11, got {merged[0].start}"
    assert merged[0].end == 21, f"Expected end=21, got {merged[0].end}"
