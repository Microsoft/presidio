"""Tests for HuggingFaceNerRecognizer."""

import logging
from unittest.mock import MagicMock, patch

import pytest
from presidio_analyzer.predefined_recognizers import (
    HuggingFaceNerRecognizer,
)
from presidio_analyzer.recognizer_registry.recognizers_loader_utils import (
    RecognizerListLoader,
)

# Path to mock the HuggingFace pipeline import
HF_PIPELINE_PATH = (
    "presidio_analyzer.predefined_recognizers.ner."
    "huggingface_ner_recognizer.hf_pipeline"
)

TEST_MODEL_NAME = "dslim/bert-base-NER"


@pytest.fixture
def mock_torch_installed():
    """Fixture to mock torch as installed and configured."""
    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = True
    mock_torch.cuda.device_count.return_value = 1
    with patch(
        "presidio_analyzer.predefined_recognizers.ner.huggingface_ner_recognizer.torch",
        mock_torch,
    ):
        yield


@pytest.fixture
def mock_transformers_pipeline():
    """Fixture to mock HuggingFace transformers pipeline."""
    mock_pipeline_instance = MagicMock()

    with patch(HF_PIPELINE_PATH, return_value=mock_pipeline_instance):
        mock_pipeline_instance.tokenizer = MagicMock()
        yield mock_pipeline_instance


@pytest.fixture
def mock_recognizer(mock_torch_installed, mock_transformers_pipeline):
    """
    Create a HuggingFaceNerRecognizer with a mocked pipeline.

    Reduces boilerplate in test functions.
    """

    def _create(
        return_value=None, model_name=TEST_MODEL_NAME, supported_language="en", **kwargs
    ):
        if return_value is not None:
            # mock_transformers_pipeline is the pipeline mock.
            # Setting its return_value defines the result of calling it.
            mock_transformers_pipeline.return_value = return_value

        rec = HuggingFaceNerRecognizer(
            model_name=model_name, supported_language=supported_language, **kwargs
        )
        return rec

    return _create


def test_analyze_person_name(mock_recognizer):
    """Test detection of person name."""
    recognizer = mock_recognizer(
        return_value=[
            {"entity_group": "PER", "start": 11, "end": 23, "score": 0.95},
        ],
        model_name=TEST_MODEL_NAME,
        supported_language="en",
    )

    text = "My name is Taewoong Kim and my phone is 555-1234"
    entities = ["PERSON"]

    results = recognizer.analyze(text, entities)

    assert len(results) == 1
    assert results[0].entity_type == "PERSON"
    assert results[0].start == text.index("Taewoong Kim")
    assert results[0].end == text.index("Taewoong Kim") + len("Taewoong Kim")
    assert results[0].score == pytest.approx(0.95, rel=1e-2)


def test_analyze_korean_with_particles(mock_recognizer):
    """Test detection in Korean text with particles (agglutinative language)."""
    # Mock HuggingFace pipeline output - returns clean entity without particle
    recognizer = mock_recognizer(
        return_value=[{"entity_group": "PS", "start": 6, "end": 9, "score": 0.95}],
        model_name="test-sample-model",
        supported_language="ko",
    )

    # "김태웅이고" contains name + particle, but NER returns only "김태웅"
    text = "내 이름은 김태웅이고 전화번호는 010-1234-5678이야"
    entities = ["PERSON"]

    results = recognizer.analyze(text, entities)

    assert len(results) == 1
    assert results[0].entity_type == "PERSON"
    assert results[0].start == text.index("김태웅")
    assert results[0].end == text.index("김태웅") + len("김태웅")
    assert results[0].score == pytest.approx(0.95, rel=1e-2)


def test_analyze_multiple_entities(mock_recognizer):
    """Test detection of multiple entity types."""
    recognizer = mock_recognizer(
        return_value=[
            {"entity_group": "PER", "start": 0, "end": 12, "score": 0.92},
            {"entity_group": "LOC", "start": 22, "end": 30, "score": 0.88},
            {"entity_group": "ORG", "start": 44, "end": 53, "score": 0.85},
        ],
        model_name=TEST_MODEL_NAME,
        supported_language="en",
    )

    text = "Taewoong Kim lives in New York and works at Microsoft"
    entities = ["PERSON", "LOCATION", "ORGANIZATION"]

    results = recognizer.analyze(text, entities)

    assert len(results) == 3
    # Sort by start index to ensure test stability
    results.sort(key=lambda x: x.start)
    assert results[0].entity_type == "PERSON"
    assert results[1].entity_type == "LOCATION"
    assert results[2].entity_type == "ORGANIZATION"


def test_analyze_filters_low_confidence(mock_recognizer):
    """Test that low confidence predictions are filtered out."""
    recognizer = mock_recognizer(
        return_value=[
            {"entity_group": "PER", "start": 0, "end": 12, "score": 0.3},
            {"entity_group": "PER", "start": 17, "end": 25, "score": 0.9},
        ],
        model_name=TEST_MODEL_NAME,
        threshold=0.5,
    )

    text = "Taewoong Kim and Jane Doe"
    entities = ["PERSON"]

    results = recognizer.analyze(text, entities)

    # Only the high confidence result should be returned
    assert len(results) == 1
    assert results[0].score == pytest.approx(0.9, rel=1e-2)


def test_analyze_with_custom_label_mapping(mock_recognizer):
    """Test custom label mapping."""
    custom_mapping = {"CUSTOM_PERSON": "PERSON"}
    recognizer = mock_recognizer(
        return_value=[
            {"entity_group": "CUSTOM_PERSON", "start": 0, "end": 12, "score": 0.90},
        ],
        model_name="custom/model",
        label_mapping=custom_mapping,
    )

    text = "Taewoong Kim is here"
    entities = ["PERSON"]

    results = recognizer.analyze(text, entities)

    assert len(results) == 1
    assert results[0].entity_type == "PERSON"


def test_analyze_filters_unsupported_entities(mock_recognizer):
    """Test that unsupported entities are filtered out."""
    recognizer = mock_recognizer(
        return_value=[{"entity_group": "PER", "start": 0, "end": 12, "score": 0.95}],
        model_name=TEST_MODEL_NAME,
    )

    text = "Taewoong Kim is here"
    entities = ["LOCATION"]  # Only looking for LOCATION, not PERSON

    results = recognizer.analyze(text, entities)

    # Should filter out PERSON since we only requested LOCATION
    assert len(results) == 0


def test_analyze_empty_text(mock_recognizer):
    """Test handling of empty text."""
    recognizer = mock_recognizer(model_name=TEST_MODEL_NAME)

    results = recognizer.analyze("", ["PERSON"])
    assert len(results) == 0

    results = recognizer.analyze("   ", ["PERSON"])
    assert len(results) == 0


def test_analyze_no_entities_found(mock_recognizer):
    """Test when no entities are found."""
    # Since mock_recognizer uses return_value for pipeline, and pipeline(text)
    # returns list of entities. A simple empty list represents no detections.
    recognizer = mock_recognizer(return_value=[], model_name=TEST_MODEL_NAME)

    text = "No entities in this text"
    entities = ["PERSON", "LOCATION"]

    results = recognizer.analyze(text, entities)

    assert len(results) == 0


@patch(HF_PIPELINE_PATH, return_value=MagicMock())
@pytest.mark.usefixtures("mock_torch_installed")
def test_default_supported_language(_mock_pipeline):
    """Test that default supported language is English."""
    recognizer = HuggingFaceNerRecognizer(model_name=TEST_MODEL_NAME)
    assert recognizer.supported_language == "en"


@patch(HF_PIPELINE_PATH, return_value=MagicMock())
@pytest.mark.usefixtures("mock_torch_installed")
def test_custom_supported_language(_mock_pipeline):
    """Test setting custom supported language."""
    recognizer = HuggingFaceNerRecognizer(
        model_name="test-sample-model", supported_language="ko"
    )
    assert recognizer.supported_language == "ko"


@patch(HF_PIPELINE_PATH, return_value=MagicMock())
@pytest.mark.usefixtures("mock_torch_installed")
def test_supported_entities_from_label_mapping(_mock_pipeline):
    """Test that supported entities are derived from label mapping."""
    recognizer = HuggingFaceNerRecognizer(model_name=TEST_MODEL_NAME)
    # Should include standard Presidio entities from DEFAULT_LABEL_MAPPING
    assert "PERSON" in recognizer.supported_entities
    assert "LOCATION" in recognizer.supported_entities
    assert "ORGANIZATION" in recognizer.supported_entities


@pytest.mark.usefixtures("mock_torch_installed")
def test_hf_recognizer_load_errors():
    """Test error handling during model loading phase."""
    path = HF_PIPELINE_PATH
    # 1. Test ImportError when transformers is missing
    with patch(path, new=None):
        with pytest.raises(ImportError):
            HuggingFaceNerRecognizer(model_name="test")

    # 2. Test ValueError when model_name is missing
    with patch(path, new=MagicMock()):
        with pytest.raises(ValueError, match="model_name must be set"):
            HuggingFaceNerRecognizer(model_name=None)


@pytest.mark.usefixtures("mock_torch_installed")
def test_load_invokes_hf_pipeline_with_expected_args():
    """Test that load() calls hf_pipeline with correct arguments."""
    # Patch with MagicMock to ensure it acts as "installed"
    with patch(HF_PIPELINE_PATH, new=MagicMock()) as mock_hf_pipeline:
        HuggingFaceNerRecognizer(
            model_name="test-model", aggregation_strategy="simple", device=-1
        )

        mock_hf_pipeline.assert_called_once_with(
            "token-classification",
            model="test-model",
            tokenizer="test-model",
            aggregation_strategy="simple",
            device=-1,
        )


def test_analyze_long_text_chunking(mock_recognizer):
    """Test that long text is split into chunks and offsets are corrected."""
    # Use text with spaces for predictable boundaries
    # Text: "A A A A A A A A A A..." (Indices: 0, 2, 4, 6, 8...)
    text = ("A " * 20).strip()  # Length 39

    recognizer = mock_recognizer(
        model_name="test-sample-model", chunk_size=10, chunk_overlap=4
    )
    # The CharacterBasedTextChunker is initialized inside the recognizer
    # using these parameters.

    # Chunk 1: "A A A A A " (0-10). Extends to 11 (space at 11 is boundary).
    # Range 0-11.
    # Mock Entity: PER at 2-3 ("A"). Global 2-3.

    # Next start: 11 - 4 = 7.
    # Chunk 2 Start 7.
    # Text[7] is ' '. Text[8] is 'A'.
    # Mock Entity: LOC at 8-9 (Global).
    # Relative start for Global 8: 8 - 7 = 1.
    # Relative end for Global 9: 9 - 7 = 2.

    # Extended returns
    recognizer.ner_pipeline.side_effect = [
        [{"entity_group": "PER", "start": 2, "end": 3, "score": 0.9}],
        [{"entity_group": "LOC", "start": 1, "end": 2, "score": 0.9}],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
    ]

    results = recognizer.analyze(text, ["PERSON", "LOCATION"])
    results.sort(key=lambda x: x.start)

    assert len(results) == 2

    # First entity: PERSON at 2-3
    assert results[0].entity_type == "PERSON"
    assert results[0].start == 2
    assert results[0].end == 3

    # Second entity: LOCATION at 8-9
    assert results[1].entity_type == "LOCATION"
    assert results[1].start == 8
    assert results[1].end == 9


def test_analyze_deduplication_keeps_highest_score(mock_recognizer):
    """Test deduplication keeps highest score when same span detected twice."""
    text = ("A " * 20).strip()

    recognizer = mock_recognizer(
        model_name="test-sample-model",
        chunk_size=10,
        chunk_overlap=8,  # Start 11-8=3 to overlap Global 4-5
    )

    # Chunk 1: 0-11.
    #   Mock: PER at 4-5 (Global 4-5). Score 0.6.

    # Next start: 11 - 8 = 3.
    # Chunk 2 Start 3.
    #   Mock: PER at Global 4-5.
    #   Relative start: 4 - 3 = 1.
    #   Relative end: 5 - 3 = 2.

    recognizer.ner_pipeline.side_effect = [
        [{"entity_group": "PER", "start": 4, "end": 5, "score": 0.60}],
        [{"entity_group": "PER", "start": 1, "end": 2, "score": 0.95}],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
    ]

    results = recognizer.analyze(text, ["PERSON"])
    results.sort(key=lambda x: x.start)

    assert len(results) == 1
    assert results[0].score == pytest.approx(0.95, rel=1e-2)
    assert results[0].start == 4
    assert results[0].end == 5


@pytest.mark.usefixtures("mock_torch_installed")
def test_hf_recognizer_init_variations(caplog):
    """Test various initialization scenarios and warnings."""
    caplog.set_level(logging.WARNING)
    path = HF_PIPELINE_PATH
    with patch(path, new=MagicMock()):
        # Check warning for aggregation_strategy='none'
        HuggingFaceNerRecognizer(
            model_name="test-sample-model", aggregation_strategy="none"
        )
        assert (
            "aggregation_strategy='none' may result in fragmented entities"
            in caplog.text
        )

        # Verify supported_entities is correctly stored in the base class field
        rec2 = HuggingFaceNerRecognizer(
            model_name="test-sample-model", supported_entities=["TEST_ENTITY"]
        )
        assert "TEST_ENTITY" in rec2.supported_entities


@pytest.mark.usefixtures("mock_torch_installed")
def test_hf_recognizer_analyze_lazy_load(caplog):
    """Test automatic lazy loading in analyze()."""
    caplog.set_level(logging.WARNING)
    path = HF_PIPELINE_PATH
    with patch(path, new=MagicMock()):
        rec = HuggingFaceNerRecognizer(model_name="test-sample-model")

        # Stub predict_with_chunking
        rec.text_chunker = MagicMock()
        rec.text_chunker.predict_with_chunking.return_value = []

        rec.ner_pipeline = None

        with patch.object(rec, "load") as mock_load:
            rec.analyze("some text", entities=[])

            # Verify automatic load was triggered
            mock_load.assert_called_once()


@pytest.mark.usefixtures("mock_torch_installed")
@pytest.mark.parametrize(
    "device_input, expected_device",
    [
        ("cpu", -1),
        ("cuda", 0),
        ("cuda:1", 1),
        (0, 0),
    ],
)
def test_hf_recognizer_device_parsing(device_input, expected_device):
    """Test that various device strings/ints are correctly parsed for the pipeline."""
    path = HF_PIPELINE_PATH
    with patch(path, new=MagicMock()):
        # Mock torch in sys.modules to make the test independent of torch installation.
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.device_count.return_value = 2

        with patch.dict("sys.modules", {"torch": mock_torch}):
            rec = HuggingFaceNerRecognizer(
                model_name="test-sample-model", device=device_input
            )
            # Ensure the device was normalized in the constructor
            assert rec.device == expected_device


@pytest.mark.usefixtures("mock_torch_installed")
def test_hf_recognizer_device_fallback_and_validation():
    """Test device fallback to CPU and invalid device validation (fail-fast)."""
    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = True
    mock_torch.cuda.device_count.return_value = 1

    with patch.dict("sys.modules", {"torch": mock_torch}):
        with patch(HF_PIPELINE_PATH, new=MagicMock()) as mock_pipeline:
            # Request GPU 1 when only GPU 0 is available (should fallback to CPU -1)
            HuggingFaceNerRecognizer(model_name="test-sample-model", device=1)
            _, kwargs = mock_pipeline.call_args
            assert kwargs["device"] == -1

            # Request completely invalid string (should still fail-fast during parsing)
            mock_pipeline.reset_mock()
            with pytest.raises(ValueError, match="Invalid device specified"):
                HuggingFaceNerRecognizer(model_name="test-sample-model", device="tpu")

            # Ensure pipeline was NOT called (validation should happen before creation)
            mock_pipeline.assert_not_called()


@pytest.mark.usefixtures("mock_torch_installed")
@patch(HF_PIPELINE_PATH, new=MagicMock())
def test_hf_recognizer_init_logs_warning_for_extra_kwargs(caplog):
    """Test that valid but unsupported kwargs trigger a warning."""
    caplog.set_level(logging.WARNING, logger="presidio-analyzer")
    # Passed 'unsupported_arg' which is not in __init__
    HuggingFaceNerRecognizer(model_name="test-model", unsupported_arg="some_value")

    assert "Ignoring unsupported kwargs" in caplog.text


@pytest.mark.usefixtures("mock_torch_installed")
@patch(HF_PIPELINE_PATH, new=MagicMock())
def test_hf_recognizer_init_uses_provided_text_chunker():
    """Test that an external text_chunker can be injected."""
    mock_chunker = MagicMock()
    rec = HuggingFaceNerRecognizer(model_name="test-model", text_chunker=mock_chunker)
    assert rec.text_chunker is mock_chunker


@pytest.mark.usefixtures("mock_torch_installed")
def test_hf_recognizer_load_cuda_unavailable_fallback(caplog):
    """Test fallback to CPU if CUDA is requested but unavailable."""
    caplog.set_level(logging.WARNING)

    # Simulate CUDA not available
    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = False
    mock_torch.cuda.device_count.return_value = 0

    with patch(
        "presidio_analyzer.predefined_recognizers.ner.huggingface_ner_recognizer.torch",
        mock_torch,
    ):
        with patch(HF_PIPELINE_PATH) as mock_pipeline:
            # Request GPU (device=0)
            rec = HuggingFaceNerRecognizer(model_name="test", device=0)
            rec.load()

            # Should fallback to -1 (CPU)
            assert "CUDA is not available. Falling back to CPU." in caplog.text
            args, kwargs = mock_pipeline.call_args
            assert kwargs.get("device") == -1


def test_hf_recognizer_prediction_edge_cases(mock_recognizer, caplog):
    """Test edge cases in prediction logic (BILOU prefixes, filtering, etc)."""
    caplog.set_level(logging.WARNING)
    # create recognizer with mocked pipeline using fixture
    rec = mock_recognizer(model_name="test-sample-model")

    # Case 1: Model returns a label not in mapping (Discovery via Unmapped)
    rec.ner_pipeline.return_value = [
        {"entity": "UNKNOWN_ENT", "score": 0.9, "start": 0, "end": 4}
    ]
    res1 = rec.analyze("test", entities=["UNKNOWN_ENT"])
    assert len(res1) == 1
    assert res1[0].entity_type == "UNKNOWN_ENT"

    # Case 2: Label in mapping but user did not ask for it (Filtering)
    rec.ner_pipeline.return_value = [
        {"entity": "B-PER", "score": 0.9, "start": 0, "end": 4}
    ]
    res2 = rec.analyze("test", entities=["LOCATION"])
    assert len(res2) == 0

    # Case 3: Label prefix stripping logic (BILOU)
    rec.ner_pipeline.return_value = [
        {"entity": "B-PER", "score": 0.9, "start": 0, "end": 4},
        {"entity": "I-PER", "score": 0.9, "start": 5, "end": 9},
    ]
    res3 = rec.analyze("test", entities=["PERSON"])
    assert len(res3) == 2
    assert res3[0].entity_type == "PERSON"
    assert res3[1].entity_type == "PERSON"

    # Case 4: Overwriting label prefixes (Custom Prefix)
    rec.label_prefixes = ["Tag:"]
    rec.ner_pipeline.return_value = [
        {"entity": "Tag:PER", "score": 0.9, "start": 0, "end": 4},
        {"entity": "B-PER", "score": 0.9, "start": 5, "end": 9},
    ]
    res4 = rec.analyze("test", entities=["PERSON"])
    assert len(res4) == 2
    assert res4[0].entity_type == "PERSON"  # Stripped correctly
    assert res4[1].entity_type == "B-PER"  # NOT stripped (standard prefix ignored)

    # Case 5: Inference engine throws an exception
    rec.ner_pipeline.side_effect = Exception("Pipeline failure")
    assert rec.analyze("test", entities=["PERSON"]) == []
    assert "NER prediction failed" in caplog.text


def test_hf_recognizer_analyze_handles_malformed_pipeline_output(
    mock_recognizer, caplog
):
    """Test that the recognizer handles malformed pipeline outputs gracefully."""
    caplog.set_level(logging.WARNING)
    rec = mock_recognizer(model_name="test-model")

    # 1. Pipeline returns non-list
    caplog.clear()
    rec.ner_pipeline.return_value = {"not": "a list"}
    assert rec.analyze("test", entities=["PERSON"]) == []
    assert "Unexpected pipeline output type" in caplog.text

    # 2. Pipeline returns list with non-dict items
    caplog.clear()
    rec.ner_pipeline.return_value = ["not a dict"]
    assert rec.analyze("test", entities=["PERSON"]) == []
    assert "Unexpected prediction item type" in caplog.text

    # 3. Prediction missing label
    caplog.clear()
    rec.ner_pipeline.return_value = [{"score": 0.9, "start": 0, "end": 4}]
    assert rec.analyze("test", entities=["PERSON"]) == []

    # 4. Prediction with non-numeric score
    caplog.clear()
    rec.ner_pipeline.return_value = [
        {"entity": "PER", "score": "bad", "start": 0, "end": 4}
    ]
    assert rec.analyze("test", entities=["PERSON"]) == []
    assert "Failed to convert score to float" in caplog.text

    # 5. Prediction missing start/end
    caplog.clear()
    rec.ner_pipeline.return_value = [{"entity": "PER", "score": 0.9}]
    assert rec.analyze("test", entities=["PERSON"]) == []


def test_hf_recognizer_loader_supported_entities_filtering():
    """Verify if supported_entities survives the RecognizerListLoader logic."""
    rec_conf = {
        "name": "HuggingFaceNerRecognizer",
        "model_name": "test-model",
        "supported_entities": ["STAY_PERSISTENT"],
    }
    lang_conf = {"supported_language": "en"}

    # HuggingFaceNerRecognizer accepts **kwargs, so the loader will not strip
    # extra fields (like supported_entities) during kwargs preparation.
    # Whether the recognizer uses them is handled by the recognizer implementation.
    kwargs = RecognizerListLoader._prepare_recognizer_kwargs(
        rec_conf, lang_conf, HuggingFaceNerRecognizer
    )

    # If the test fails here, it means the loader logic incorrectly filtered it out.
    assert "supported_entities" in kwargs, (
        "supported_entities was filtered out by loader!"
    )
    assert kwargs["supported_entities"] == ["STAY_PERSISTENT"]


@patch(HF_PIPELINE_PATH, return_value=MagicMock())
@pytest.mark.usefixtures("mock_torch_installed")
def test_hf_recognizer_default_chunker(_mock_pipeline):
    """Test that HuggingFaceNerRecognizer uses CharacterBasedTextChunker by default."""
    from presidio_analyzer.chunkers import CharacterBasedTextChunker

    rec = HuggingFaceNerRecognizer(model_name="test-model")
    assert isinstance(rec.text_chunker, CharacterBasedTextChunker)
    assert rec.text_chunker.chunk_size == 400
    assert rec.text_chunker.chunk_overlap == 40


@patch(HF_PIPELINE_PATH, return_value=MagicMock())
@pytest.mark.usefixtures("mock_torch_installed")
def test_hf_recognizer_custom_chunk_size(_mock_pipeline):
    """Test that chunk_size and chunk_overlap params are forwarded."""
    from presidio_analyzer.chunkers import CharacterBasedTextChunker

    rec = HuggingFaceNerRecognizer(
        model_name="test-model", chunk_size=600, chunk_overlap=80
    )
    assert isinstance(rec.text_chunker, CharacterBasedTextChunker)
    assert rec.text_chunker.chunk_size == 600
    assert rec.text_chunker.chunk_overlap == 80


@patch(HF_PIPELINE_PATH, return_value=MagicMock())
@pytest.mark.usefixtures("mock_torch_installed")
def test_hf_recognizer_text_chunker_dict_config_via_loader(_mock_pipeline):
    """Test that text_chunker dict is converted to chunker by the registry loader."""
    from presidio_analyzer.chunkers import CharacterBasedTextChunker
    from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

    provider = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "global_regex_flags": 26,
            "recognizers": [
                {
                    "name": "HF NER",
                    "type": "predefined",
                    "class_name": "HuggingFaceNerRecognizer",
                    "model_name": "test-model",
                    "supported_languages": ["en"],
                    "supported_entities": ["PERSON"],
                    "device": "cpu",
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
    hf_recs = [
        r for r in registry.recognizers if isinstance(r, HuggingFaceNerRecognizer)
    ]
    assert len(hf_recs) == 1
    assert isinstance(hf_recs[0].text_chunker, CharacterBasedTextChunker)
    assert hf_recs[0].text_chunker.chunk_size == 300
    assert hf_recs[0].text_chunker.chunk_overlap == 40


@patch(HF_PIPELINE_PATH, return_value=MagicMock())
@pytest.mark.usefixtures("mock_torch_installed")
def test_hf_recognizer_text_chunker_object(_mock_pipeline):
    """Test that text_chunker accepts a BaseTextChunker instance directly."""
    from presidio_analyzer.chunkers import CharacterBasedTextChunker

    custom_chunker = CharacterBasedTextChunker(chunk_size=500, chunk_overlap=100)
    rec = HuggingFaceNerRecognizer(model_name="test-model", text_chunker=custom_chunker)
    assert rec.text_chunker is custom_chunker


@patch(HF_PIPELINE_PATH, return_value=MagicMock())
@pytest.mark.usefixtures("mock_torch_installed")
def test_hf_recognizer_resolves_deferred_tokenizer_chunker(mock_pipeline):
    """A deferred TokenizerBasedTextChunker is resolved during load()."""
    from presidio_analyzer.chunkers import TokenizerBasedTextChunker

    # The pipeline exposes a fast tokenizer that the chunker should adopt.
    mock_tokenizer = MagicMock()
    mock_tokenizer.is_fast = True
    mock_pipeline.return_value.tokenizer = mock_tokenizer

    chunker = TokenizerBasedTextChunker(max_tokens=128, overlap_tokens=16)
    assert chunker.is_deferred

    # __init__ triggers load() (via EntityRecognizer), which resolves the chunker.
    rec = HuggingFaceNerRecognizer(model_name="test-model", text_chunker=chunker)

    assert rec.text_chunker is chunker
    assert not chunker.is_deferred
    assert chunker.tokenizer is mock_tokenizer
    assert chunker.max_tokens == 128
    assert chunker.overlap_tokens == 16
