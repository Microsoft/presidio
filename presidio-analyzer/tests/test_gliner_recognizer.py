import sys

import pytest
from unittest.mock import MagicMock, patch

from presidio_analyzer.predefined_recognizers import GLiNERRecognizer
from presidio_analyzer.chunkers import CharacterBasedTextChunker


@pytest.fixture
def mock_gliner():
    """
    Fixture to mock GLiNER class and its methods.
    """

    pytest.importorskip("gliner", reason="GLiNER package is not installed")

    # Mock the GLiNER class and its methods
    mock_gliner_instance = MagicMock()
    mock_gliner_instance.to.return_value = mock_gliner_instance
    # Mock the from_pretrained method to return the mock instance
    with patch("gliner.GLiNER.from_pretrained", return_value=mock_gliner_instance):
        yield mock_gliner_instance


def test_analyze_passed_entities_are_subset_of_entity_mapping(
    mock_gliner
):

    if sys.version_info < (3, 10):
        pytest.skip("gliner requires Python >= 3.10")

    # Mock GLiNER predict_entities
    mock_gliner.predict_entities.return_value = [
        {"label": "person", "start": 11, "end": 19, "score": 0.95},
        {"label": "location", "start": 33, "end": 41, "score": 0.85},
        {"label": "org", "start": 313, "end": 411, "score": 0.85},
    ]

    entity_mapping = {
        "person": "PERSON",
        "organization": "ORG",
        "location": "LOC",
    }

    gliner_recognizer = GLiNERRecognizer(
        entity_mapping=entity_mapping,
    )

    gliner_recognizer.gliner = mock_gliner
    text = "My name is John Doe from Seattle."
    entities = ["PERSON", "LOC"]

    results = gliner_recognizer.analyze(text, entities)

    # Check the number of results
    assert len(results) == 2

    # Check the first result
    assert results[0].entity_type == "PERSON"
    assert results[0].start == 11
    assert results[0].end == 19
    assert results[0].score == pytest.approx(0.95, rel=1e-2)

    # Check the second result
    assert results[1].entity_type == "LOC"
    assert results[1].start == 33
    assert results[1].end == 41
    assert results[1].score == pytest.approx(0.85, rel=1e-2)


def test_analyze_with_unsupported_entity(mock_gliner):


    if sys.version_info < (3, 10):
        pytest.skip("gliner requires Python >= 3.10")


    # Mock GLiNER predict_entities
    mock_gliner.gliner.predict_entities.return_value = [
        {"label": "BIRD", "start": 0, "end": 5, "score": 0.75},
    ]

    text = "Unknown entity."
    entities = ["PERSON", "LOC"]

    gliner_recognizer = GLiNERRecognizer(
        supported_entities=entities,
    )

    gliner_recognizer.gliner = mock_gliner

    results = gliner_recognizer.analyze(text, entities)

    # Should filter out unsupported entities
    assert len(results) == 0


def test_analyze_with_entity_mapping(mock_gliner):
    # Mock GLiNER predict_entities
    mock_gliner.predict_entities.return_value = [
        {"label": "organization", "start": 10, "end": 20, "score": 0.90},
    ]

    text = "Works at Microsoft."
    entity_mapping = {"organization": "ORG"}

    gliner_recognizer = GLiNERRecognizer(
        entity_mapping=entity_mapping,
    )

    gliner_recognizer.gliner = mock_gliner

    results = gliner_recognizer.analyze(text, ["ORG"])

    # Check mapping from 'organization' to 'ORG'
    assert len(results) == 1
    assert results[0].entity_type == "ORG"
    assert results[0].start == 10
    assert results[0].end == 20
    assert results[0].score == pytest.approx(0.90, rel=1e-2)


def test_analyze_with_no_entities(mock_gliner):
    # Mock GLiNER predict_entities
    mock_gliner.predict_entities.return_value = []

    text = "No entities here."
    entities = []


    gliner_recognizer = GLiNERRecognizer(
        supported_entities=["ORG", "LOC", "PER"],
    )

    results = gliner_recognizer.analyze(text, entities)

    # Should return no results
    assert len(results) == 0


def test_gliner_handles_long_text_with_chunking(mock_gliner):
    """Test that GLiNER chunks long text and adjusts entity offsets correctly."""
    if sys.version_info < (3, 10):
        pytest.skip("gliner requires Python >= 3.10")

    text = "John Smith lives here. " + ("x " * 120) + "Jane Doe works there."

    # Mock returns entities with positions relative to each chunk
    def mock_predict_entities(text, labels, flat_ner, threshold, multi_label):
        entities = []
        if "John Smith" in text:
            start = text.find("John Smith")
            entities.append({"label": "person", "start": start, "end": start + 10, "score": 0.95})
        if "Jane Doe" in text:
            start = text.find("Jane Doe")
            entities.append({"label": "person", "start": start, "end": start + 8, "score": 0.93})
        return entities

    mock_gliner.predict_entities.side_effect = mock_predict_entities

    gliner_recognizer = GLiNERRecognizer(
        entity_mapping={"person": "PERSON"},
        text_chunker=CharacterBasedTextChunker(chunk_size=250, chunk_overlap=50),
    )
    gliner_recognizer.gliner = mock_gliner

    results = gliner_recognizer.analyze(text, ["PERSON"])

    # Verify chunking occurred (predict_entities called multiple times)
    assert mock_gliner.predict_entities.call_count == 2, f"Expected 2 chunks, got {mock_gliner.predict_entities.call_count}"
    
    # Verify exactly 2 entities were detected
    assert len(results) == 2, f"Expected 2 entities, found {len(results)}"
    
    # Verify both entities have correct offsets in original text
    assert text[results[0].start:results[0].end] == "John Smith"
    assert results[0].entity_type == "PERSON"
    assert results[0].score == 0.95
    
    assert text[results[1].start:results[1].end] == "Jane Doe"
    assert results[1].entity_type == "PERSON"
    assert results[1].score == 0.93


def test_gliner_detects_entity_split_across_chunk_boundary(mock_gliner):
    """Test that overlap catches entities split at chunk boundaries."""
    if sys.version_info < (3, 10):
        pytest.skip("gliner requires Python >= 3.10")

    # Entity "Amanda Williams" will be split: "Amanda" at end of chunk 1, "Williams" at start of chunk 2
    # With 50-char overlap, both parts should be in the overlapping region
    text = ("x " * 100) + "Amanda Williams" + (" x" * 100)

    def mock_predict_entities(text, labels, flat_ner, threshold, multi_label):
        entities = []
        if "Amanda Williams" in text:
            start = text.find("Amanda Williams")
            entities.append({"label": "person", "start": start, "end": start + 15, "score": 0.92})
        return entities

    mock_gliner.predict_entities.side_effect = mock_predict_entities

    gliner_recognizer = GLiNERRecognizer(
        entity_mapping={"person": "PERSON"},
        text_chunker=CharacterBasedTextChunker(chunk_size=250, chunk_overlap=50),
    )
    gliner_recognizer.gliner = mock_gliner

    results = gliner_recognizer.analyze(text, ["PERSON"])

    # Verify entity at boundary was detected
    assert len(results) == 1, f"Expected 1 entity, found {len(results)}"
    assert text[results[0].start:results[0].end] == "Amanda Williams"
    assert results[0].entity_type == "PERSON"


def test_gliner_deduplicates_entities_in_overlap_region(mock_gliner):
    """Test that duplicate entities from overlapping chunks are removed."""
    if sys.version_info < (3, 10):
        pytest.skip("gliner requires Python >= 3.10")

    # Create text where entity appears in overlap region of both chunks
    text = ("x " * 95) + "Dr. Smith" + (" x" * 100)

    call_count = 0
    def mock_predict_entities(text, labels, flat_ner, threshold, multi_label):
        nonlocal call_count
        call_count += 1
        entities = []
        if "Dr. Smith" in text:
            start = text.find("Dr. Smith")
            # Return slightly different scores to test that highest is kept
            score = 0.95 if call_count == 1 else 0.90
            entities.append({"label": "person", "start": start, "end": start + 9, "score": score})
        return entities

    mock_gliner.predict_entities.side_effect = mock_predict_entities

    gliner_recognizer = GLiNERRecognizer(
        entity_mapping={"person": "PERSON"},
        text_chunker=CharacterBasedTextChunker(chunk_size=250, chunk_overlap=50),
    )
    gliner_recognizer.gliner = mock_gliner

    results = gliner_recognizer.analyze(text, ["PERSON"])

    # Verify: Called multiple times due to overlap
    assert mock_gliner.predict_entities.call_count >= 2, "Should process multiple chunks"
    
    # Verify: Only 1 result after deduplication (not 2)
    assert len(results) == 1, f"Expected 1 deduplicated entity, found {len(results)}"
    
    # Verify: Kept the one with highest score (0.95 from first chunk)
    assert results[0].score == 0.95
    assert text[results[0].start:results[0].end] == "Dr. Smith"


GLINER_MOCK_PATH = (
    "presidio_analyzer.predefined_recognizers.ner.gliner_recognizer.GLiNER"
)


@pytest.mark.parametrize(
    "load_onnx_model,onnx_model_file,expected_onnx_model,expected_file",
    [
        (True, "model.onnx", True, "model.onnx"),
        (False, "model.onnx", False, "model.onnx"),
        (True, "custom_model.onnx", True, "custom_model.onnx"),
        (False, "custom_model.onnx", False, "custom_model.onnx"),
    ],
)
def test_when_onnx_parameters_then_passes_to_from_pretrained(
    load_onnx_model, onnx_model_file, expected_onnx_model, expected_file
):
    """Test that ONNX parameters are passed to GLiNER.from_pretrained."""
    if sys.version_info < (3, 10):
        pytest.skip("gliner requires Python >= 3.10")

    pytest.importorskip("gliner", reason="GLiNER package is not installed")

    with patch(GLINER_MOCK_PATH) as mock_gliner_class:
        mock_gliner_instance = MagicMock()
        mock_gliner_class.from_pretrained.return_value = mock_gliner_instance

        recognizer = GLiNERRecognizer(
            supported_entities=["PERSON"],
            load_onnx_model=load_onnx_model,
            onnx_model_file=onnx_model_file,
        )
        recognizer.load()

        # Verify from_pretrained was called with expected parameters
        assert mock_gliner_class.from_pretrained.called
        call_kwargs = mock_gliner_class.from_pretrained.call_args[1]
        assert call_kwargs["load_onnx_model"] is expected_onnx_model
        assert call_kwargs["onnx_model_file"] == expected_file


def test_when_model_kwargs_then_passes_to_from_pretrained():
    """Test that additional model kwargs are passed to GLiNER.from_pretrained."""
    if sys.version_info < (3, 10):
        pytest.skip("gliner requires Python >= 3.10")

    pytest.importorskip("gliner", reason="GLiNER package is not installed")

    with patch(GLINER_MOCK_PATH) as mock_gliner_class:
        mock_gliner_instance = MagicMock()
        mock_gliner_class.from_pretrained.return_value = mock_gliner_instance

        # Pass additional kwargs that might be supported by GLiNER in the future
        recognizer = GLiNERRecognizer(
            supported_entities=["PERSON"],
            custom_param1="value1",
            custom_param2=42,
        )
        recognizer.load()

        # Verify from_pretrained was called with the custom parameters
        assert mock_gliner_class.from_pretrained.called
        call_kwargs = mock_gliner_class.from_pretrained.call_args[1]
        assert call_kwargs["custom_param1"] == "value1"
        assert call_kwargs["custom_param2"] == 42


def test_gliner_default_chunker():
    """Test that GLiNER uses CharacterBasedTextChunker by default."""
    if sys.version_info < (3, 10):
        pytest.skip("gliner requires Python >= 3.10")
    pytest.importorskip("gliner", reason="GLiNER package is not installed")

    recognizer = GLiNERRecognizer(supported_entities=["PERSON"])
    assert isinstance(recognizer.text_chunker, CharacterBasedTextChunker)
    assert recognizer.text_chunker.chunk_size == 250
    assert recognizer.text_chunker.chunk_overlap == 50


def test_gliner_custom_chunk_size():
    """Test that chunk_size and chunk_overlap params are forwarded."""
    if sys.version_info < (3, 10):
        pytest.skip("gliner requires Python >= 3.10")
    pytest.importorskip("gliner", reason="GLiNER package is not installed")

    recognizer = GLiNERRecognizer(
        supported_entities=["PERSON"], chunk_size=400, chunk_overlap=60
    )
    assert isinstance(recognizer.text_chunker, CharacterBasedTextChunker)
    assert recognizer.text_chunker.chunk_size == 400
    assert recognizer.text_chunker.chunk_overlap == 60


def test_gliner_text_chunker_dict_config_via_loader():
    """Test that text_chunker dict is converted to chunker by the registry loader."""
    if sys.version_info < (3, 10):
        pytest.skip("gliner requires Python >= 3.10")
    pytest.importorskip("gliner", reason="GLiNER package is not installed")
    from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

    provider = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "global_regex_flags": 26,
            "recognizers": [
                {
                    "name": "GLiNERRecognizer",
                    "type": "predefined",
                    "supported_entities": ["PERSON"],
                    "supported_languages": ["en"],
                    "text_chunker": {
                        "chunker_type": "character",
                        "chunk_size": 300,
                        "chunk_overlap": 40,
                    },
                }
            ],
        }
    )
    registry = provider.create_recognizer_registry()
    gliner_recs = [
        r for r in registry.recognizers if isinstance(r, GLiNERRecognizer)
    ]
    assert len(gliner_recs) == 1
    assert isinstance(gliner_recs[0].text_chunker, CharacterBasedTextChunker)
    assert gliner_recs[0].text_chunker.chunk_size == 300
    assert gliner_recs[0].text_chunker.chunk_overlap == 40


def test_gliner_text_chunker_object():
    """Test that text_chunker accepts a BaseTextChunker instance directly."""
    if sys.version_info < (3, 10):
        pytest.skip("gliner requires Python >= 3.10")
    pytest.importorskip("gliner", reason="GLiNER package is not installed")

    custom_chunker = CharacterBasedTextChunker(chunk_size=500, chunk_overlap=100)
    recognizer = GLiNERRecognizer(
        supported_entities=["PERSON"], text_chunker=custom_chunker
    )
    assert recognizer.text_chunker is custom_chunker


def test_gliner_resolves_deferred_tokenizer_chunker():
    """A deferred TokenizerBasedTextChunker is resolved during load()."""
    if sys.version_info < (3, 10):
        pytest.skip("gliner requires Python >= 3.10")
    pytest.importorskip("gliner", reason="GLiNER package is not installed")

    from presidio_analyzer.chunkers import TokenizerBasedTextChunker

    with patch(GLINER_MOCK_PATH) as mock_gliner_class:
        mock_gliner_instance = MagicMock()
        mock_gliner_class.from_pretrained.return_value = mock_gliner_instance

        # The GLiNER model exposes its own fast tokenizer.
        mock_tokenizer = MagicMock()
        mock_tokenizer.is_fast = True
        mock_gliner_instance.data_processor.transformer_tokenizer = mock_tokenizer

        chunker = TokenizerBasedTextChunker(max_tokens=128, overlap_tokens=16)
        assert chunker.is_deferred

        recognizer = GLiNERRecognizer(
            supported_entities=["PERSON"], text_chunker=chunker
        )
        recognizer.load()

        assert recognizer.text_chunker is chunker
        assert not chunker.is_deferred
        assert chunker.tokenizer is mock_tokenizer
        assert chunker.max_tokens == 128
        assert chunker.overlap_tokens == 16
