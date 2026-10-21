"""Tests for batch inference support across recognizers and engine."""

import sys
from unittest.mock import MagicMock, patch

import pytest
from presidio_analyzer import (
    BatchAnalyzerEngine,
    RecognizerResult,
)
from presidio_analyzer.chunkers import BaseTextChunker
from presidio_analyzer.chunkers.base_chunker import TextChunk

# ---------------------------------------------------------------------------
# 7a. EntityRecognizer.batch_analyze — default implementation
# ---------------------------------------------------------------------------


def test_entity_recognizer_batch_analyze_default(analyzer_engine_simple):
    """Default batch_analyze delegates to analyze() per text."""
    # Get an actual recognizer from the registry
    recognizers = analyzer_engine_simple.registry.get_recognizers(
        language="en", all_fields=True
    )
    rec = recognizers[0]  # e.g. CreditCardRecognizer or PhoneRecognizer

    texts = ["Call me at 2352351232", "No entities here"]
    entities = rec.get_supported_entities()
    artifacts = [
        analyzer_engine_simple.nlp_engine.process_text(t, "en") for t in texts
    ]

    # Compare batch_analyze to individual analyze
    batch_results = rec.batch_analyze(texts, entities, artifacts)
    individual_results = [
        rec.analyze(t, entities, a) for t, a in zip(texts, artifacts)
    ]

    assert len(batch_results) == len(individual_results)
    for batch_res, ind_res in zip(batch_results, individual_results):
        assert len(batch_res) == len(ind_res)
        for b, i in zip(batch_res, ind_res):
            assert b.entity_type == i.entity_type
            assert b.start == i.start
            assert b.end == i.end
            assert b.score == i.score


def test_entity_recognizer_batch_analyze_empty():
    """batch_analyze with empty input returns empty list."""
    from presidio_analyzer.predefined_recognizers import CreditCardRecognizer

    rec = CreditCardRecognizer()
    assert rec.batch_analyze([], [], []) == []


def test_entity_recognizer_batch_analyze_length_mismatch_raises():
    """batch_analyze raises ValueError when texts/artifacts lengths differ."""
    from presidio_analyzer.predefined_recognizers import CreditCardRecognizer

    rec = CreditCardRecognizer()
    with pytest.raises(ValueError, match="Length mismatch"):
        rec.batch_analyze(["a", "b"], [], [None])  # 2 texts, 1 artifact


# ---------------------------------------------------------------------------
# 7b. BaseTextChunker.predict_batch_with_chunking
# ---------------------------------------------------------------------------


class _SimpleChunker(BaseTextChunker):
    """Chunker that splits texts into fixed-size chunks for testing."""

    def __init__(self, max_len=20, overlap=5):
        self.max_len = max_len
        self.overlap = overlap

    def chunk(self, text):
        if len(text) <= self.max_len:
            return [TextChunk(text=text, start=0, end=len(text))]
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + self.max_len, len(text))
            chunks.append(TextChunk(text=text[start:end], start=start, end=end))
            if end >= len(text):
                break
            start = end - self.overlap
        return chunks


def test_predict_batch_no_chunking_needed():
    """Single-chunk texts go to predict_batch_func in one length-sorted call."""
    chunker = _SimpleChunker(max_len=100)
    texts = ["Hello world", "Foo bar"]

    call_log = []

    def mock_predict_batch(chunk_texts):
        call_log.append(chunk_texts)
        results = []
        for ct in chunk_texts:
            if ct == "Hello world":
                results.append([RecognizerResult("PERSON", 0, 5, 0.9)])
            elif ct == "Foo bar":
                results.append([RecognizerResult("LOCATION", 0, 3, 0.8)])
            else:
                results.append([])
        return results

    results = chunker.predict_batch_with_chunking(texts, mock_predict_batch)

    assert len(call_log) == 1
    assert call_log[0] == sorted(texts, key=len)
    assert len(results) == 2
    assert len(results[0]) == 1
    assert results[0][0].entity_type == "PERSON"
    assert len(results[1]) == 1
    assert results[1][0].entity_type == "LOCATION"


def test_predict_batch_results_restored_to_original_order():
    """Results from length-sorted prediction map back to original text order."""
    chunker = _SimpleChunker(max_len=100)
    # Deliberately NOT in length order
    texts = ["the longest text of them all", "mid text", "tiny"]

    def mock_predict_batch(chunk_texts):
        # Sorting contract: called shortest-first
        assert chunk_texts == sorted(chunk_texts, key=len)
        # One entity per chunk, spanning the whole chunk text
        return [
            [RecognizerResult("ENT", 0, len(ct), 0.9)] for ct in chunk_texts
        ]

    results = chunker.predict_batch_with_chunking(texts, mock_predict_batch)

    assert len(results) == 3
    # Each result's span length must match its own text, not another's
    for text, text_results in zip(texts, results):
        assert len(text_results) == 1
        assert text_results[0].end == len(text)


def test_predict_batch_with_chunking_needed():
    """Texts that need chunking: all chunks batched together, offsets adjusted."""
    chunker = _SimpleChunker(max_len=10, overlap=0)
    # "abcdefghijklmnop" (16 chars) -> 2 chunks: [0:10], [10:16]
    texts = ["abcdefghijklmnop"]

    call_log = []

    def mock_predict_batch(chunk_texts):
        call_log.append(chunk_texts)
        results = []
        for ct in chunk_texts:
            if ct == "abcdefghij":
                results.append([RecognizerResult("PER", 2, 5, 0.9)])
            elif ct == "klmnop":
                results.append([RecognizerResult("LOC", 1, 4, 0.8)])
            else:
                results.append([])
        return results

    results = chunker.predict_batch_with_chunking(texts, mock_predict_batch)

    assert len(call_log) == 1
    assert len(results) == 1
    # First entity: offset 2 in chunk starting at 0 -> global 2
    # Second entity: offset 1 in chunk starting at 10 -> global 11
    entities = sorted(results[0], key=lambda r: r.start)
    assert entities[0].start == 2
    assert entities[0].end == 5
    assert entities[1].start == 11
    assert entities[1].end == 14


def test_predict_batch_mixed_short_and_long():
    """Mix of short texts (single chunk) and long texts (multiple chunks)."""
    chunker = _SimpleChunker(max_len=10, overlap=0)
    texts = ["short", "abcdefghijklmnop"]

    def mock_predict_batch(chunk_texts):
        results = []
        for ct in chunk_texts:
            if ct == "short":
                results.append([RecognizerResult("PER", 0, 5, 0.9)])
            elif ct == "abcdefghij":
                results.append([RecognizerResult("ORG", 0, 3, 0.8)])
            elif ct == "klmnop":
                results.append([])
            else:
                results.append([])
        return results

    results = chunker.predict_batch_with_chunking(texts, mock_predict_batch)

    assert len(results) == 2
    assert len(results[0]) == 1
    assert results[0][0].entity_type == "PER"
    assert len(results[1]) == 1
    assert results[1][0].entity_type == "ORG"
    assert results[1][0].start == 0


def test_predict_batch_empty_input():
    """Empty input returns empty list."""
    chunker = _SimpleChunker()
    results = chunker.predict_batch_with_chunking([], lambda x: [])
    assert results == []


def test_predict_batch_func_returns_wrong_length_raises():
    """predict_batch_with_chunking raises on mismatched result list length."""
    chunker = _SimpleChunker(max_len=100)

    def bad_predict(chunk_texts):
        return [[]]  # too few results

    with pytest.raises(ValueError, match="must return one result list"):
        chunker.predict_batch_with_chunking(["a", "b"], bad_predict)


def test_predict_batch_deduplication_on_overlapping_chunks():
    """Overlapping chunks should trigger deduplication."""
    chunker = _SimpleChunker(max_len=10, overlap=5)
    # "abcdefghijklmno" (15 chars)
    # Chunks: [0:10], [5:15]
    texts = ["abcdefghijklmno"]

    def mock_predict_batch(chunk_texts):
        results = []
        for ct in chunk_texts:
            if ct.startswith("abcde"):
                # Entity at position 6-8 in chunk (global 6-8)
                results.append([RecognizerResult("PER", 6, 8, 0.9)])
            elif ct.startswith("fghij"):
                # Same entity at position 1-3 in chunk (global 6-8)
                results.append([RecognizerResult("PER", 1, 3, 0.85)])
            else:
                results.append([])
        return results

    results = chunker.predict_batch_with_chunking(texts, mock_predict_batch)

    assert len(results) == 1
    # Should be deduplicated to 1 entity (highest score kept)
    assert len(results[0]) == 1
    assert results[0][0].score == 0.9
    assert results[0][0].start == 6
    assert results[0][0].end == 8


# ---------------------------------------------------------------------------
# 7c. HuggingFaceNerRecognizer.batch_analyze
# ---------------------------------------------------------------------------

# Path to mock the HuggingFace pipeline import
HF_PIPELINE_PATH = (
    "presidio_analyzer.predefined_recognizers.ner."
    "huggingface_ner_recognizer.hf_pipeline"
)

TEST_MODEL_NAME = "dslim/bert-base-NER"


@pytest.fixture
def hf_mock_torch_installed():
    """Fixture to mock torch as installed and configured."""
    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = True
    mock_torch.cuda.device_count.return_value = 1
    with patch(
        "presidio_analyzer.predefined_recognizers.ner."
        "huggingface_ner_recognizer.torch",
        mock_torch,
    ):
        yield


@pytest.fixture
def hf_mock_pipeline():
    """Fixture to mock HuggingFace transformers pipeline."""
    mock_pipeline_instance = MagicMock()
    with patch(HF_PIPELINE_PATH, return_value=mock_pipeline_instance):
        mock_pipeline_instance.tokenizer = MagicMock()
        yield mock_pipeline_instance


@pytest.fixture
def hf_recognizer(hf_mock_torch_installed, hf_mock_pipeline):
    """Create a HuggingFaceNerRecognizer with a mocked pipeline."""
    from presidio_analyzer.predefined_recognizers import HuggingFaceNerRecognizer

    rec = HuggingFaceNerRecognizer(
        model_name=TEST_MODEL_NAME, supported_language="en"
    )
    return rec, hf_mock_pipeline


def test_hf_batch_analyze_multiple_texts(hf_recognizer):
    """Verify batch_analyze returns correct results for multiple texts."""
    rec, mock_pipeline = hf_recognizer

    # Mock pipeline keyed on input text: chunks arrive length-sorted, so
    # positional return values would map to the wrong texts.
    predictions_by_text = {
        "My name is Taewoong Kim": [
            {"entity_group": "PER", "start": 11, "end": 23, "score": 0.95}
        ],
        "New York is great": [
            {"entity_group": "LOC", "start": 0, "end": 8, "score": 0.88}
        ],
    }

    def pipeline_side_effect(batch_texts, **kwargs):
        return [predictions_by_text[t] for t in batch_texts]

    mock_pipeline.side_effect = pipeline_side_effect

    texts = ["My name is Taewoong Kim", "New York is great"]
    entities = ["PERSON", "LOCATION"]
    artifacts = [None, None]

    results = rec.batch_analyze(texts, entities, artifacts)

    assert len(results) == 2
    assert len(results[0]) == 1
    assert results[0][0].entity_type == "PERSON"
    assert results[0][0].start == 11
    assert results[0][0].end == 23

    assert len(results[1]) == 1
    assert results[1][0].entity_type == "LOCATION"
    assert results[1][0].start == 0
    assert results[1][0].end == 8


def test_hf_batch_analyze_empty_input(hf_recognizer):
    """batch_analyze with empty list returns empty list."""
    rec, _ = hf_recognizer
    assert rec.batch_analyze([], ["PERSON"], []) == []


def test_hf_batch_analyze_fallback_on_error(hf_recognizer, caplog):
    """Verify fallback to sequential on batch prediction error."""
    import logging

    caplog.set_level(logging.WARNING)
    rec, mock_pipeline = hf_recognizer

    # Make the batch call fail
    call_count = 0

    def side_effect_fn(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("Batch failed")
        # Sequential fallback calls
        return [{"entity_group": "PER", "start": 0, "end": 4, "score": 0.9}]

    mock_pipeline.side_effect = side_effect_fn

    texts = ["test text"]
    results = rec.batch_analyze(texts, ["PERSON"], [None])

    assert "Batch NER prediction failed" in caplog.text
    assert len(results) == 1
    assert len(results[0]) == 1


def test_hf_batch_analyze_entity_filtering(hf_recognizer):
    """Verify entity filtering works per text in batch mode."""
    rec, mock_pipeline = hf_recognizer

    # Return both PERSON and LOCATION entities
    mock_pipeline.return_value = [
        [
            {"entity_group": "PER", "start": 0, "end": 5, "score": 0.9},
            {"entity_group": "LOC", "start": 10, "end": 18, "score": 0.85},
        ],
    ]

    texts = ["John from New York"]
    # Only request PERSON
    results = rec.batch_analyze(texts, ["PERSON"], [None])

    assert len(results) == 1
    # LOCATION should be filtered out since it's a supported entity not requested
    assert all(r.entity_type == "PERSON" for r in results[0])


def test_hf_batch_analyze_lazy_load(hf_recognizer):
    """Verify automatic lazy loading in batch_analyze."""
    rec, mock_pipeline = hf_recognizer
    mock_pipeline.return_value = [[]]

    rec.ner_pipeline = None

    with patch.object(rec, "load") as mock_load:
        # Need to set pipeline after load
        def load_side_effect():
            rec.ner_pipeline = mock_pipeline

        mock_load.side_effect = load_side_effect
        rec.batch_analyze(["some text"], [], [None])
        mock_load.assert_called_once()


# ---------------------------------------------------------------------------
# 7d. GLiNERRecognizer.batch_analyze
# ---------------------------------------------------------------------------

GLINER_MOCK_PATH = (
    "presidio_analyzer.predefined_recognizers.ner.gliner_recognizer.GLiNER"
)


@pytest.fixture
def mock_gliner_for_batch():
    """Fixture to mock GLiNER class for batch tests."""
    pytest.importorskip("gliner", reason="GLiNER package is not installed")
    mock_gliner_instance = MagicMock()
    mock_gliner_instance.to.return_value = mock_gliner_instance
    with patch("gliner.GLiNER.from_pretrained", return_value=mock_gliner_instance):
        yield mock_gliner_instance


def test_gliner_batch_analyze(mock_gliner_for_batch):
    """Verify batch_analyze returns correct results."""
    if sys.version_info < (3, 10):
        pytest.skip("gliner requires Python >= 3.10")

    from presidio_analyzer.predefined_recognizers import GLiNERRecognizer

    mock_gliner = mock_gliner_for_batch

    # Mock inference keyed on input text: chunks arrive length-sorted, so
    # positional return values would map to the wrong texts.
    predictions_by_text = {
        "My name is John Doe": [
            {"label": "person", "start": 11, "end": 19, "score": 0.95}
        ],
        "New York is great": [
            {"label": "location", "start": 0, "end": 8, "score": 0.85}
        ],
    }

    def inference_side_effect(texts, **kwargs):
        return [predictions_by_text[t] for t in texts]

    mock_gliner.inference.side_effect = inference_side_effect

    entity_mapping = {"person": "PERSON", "location": "LOCATION"}
    rec = GLiNERRecognizer(entity_mapping=entity_mapping)
    rec.gliner = mock_gliner

    texts = ["My name is John Doe", "New York is great"]
    entities = ["PERSON", "LOCATION"]
    artifacts = [None, None]

    results = rec.batch_analyze(texts, entities, artifacts)

    assert len(results) == 2
    assert len(results[0]) == 1
    assert results[0][0].entity_type == "PERSON"
    assert results[0][0].start == 11

    assert len(results[1]) == 1
    assert results[1][0].entity_type == "LOCATION"

    # Verify inference was called for batch
    mock_gliner.inference.assert_called_once()


def test_gliner_batch_analyze_empty(mock_gliner_for_batch):
    """batch_analyze with empty list returns empty list."""
    if sys.version_info < (3, 10):
        pytest.skip("gliner requires Python >= 3.10")

    from presidio_analyzer.predefined_recognizers import GLiNERRecognizer

    rec = GLiNERRecognizer(supported_entities=["PERSON"])
    rec.gliner = mock_gliner_for_batch

    assert rec.batch_analyze([], ["PERSON"], []) == []


def test_gliner_batch_analyze_fallback_on_error(mock_gliner_for_batch, caplog):
    """Verify fallback to sequential on batch prediction error."""
    if sys.version_info < (3, 10):
        pytest.skip("gliner requires Python >= 3.10")

    import logging

    caplog.set_level(logging.WARNING)

    from presidio_analyzer.predefined_recognizers import GLiNERRecognizer

    mock_gliner = mock_gliner_for_batch

    # Make batch call fail
    mock_gliner.inference.side_effect = RuntimeError("Batch failed")
    # Sequential fallback
    mock_gliner.predict_entities.return_value = [
        {"label": "person", "start": 0, "end": 4, "score": 0.9}
    ]

    entity_mapping = {"person": "PERSON"}
    rec = GLiNERRecognizer(entity_mapping=entity_mapping)
    rec.gliner = mock_gliner

    texts = ["test text"]
    results = rec.batch_analyze(texts, ["PERSON"], [None])

    assert "Batch GLiNER prediction failed" in caplog.text
    assert len(results) == 1
    assert len(results[0]) == 1
    assert results[0][0].entity_type == "PERSON"


def test_gliner_batch_analyze_passes_batch_size(mock_gliner_for_batch):
    """Verify inference_batch_size is passed to gliner.inference() as batch_size."""
    if sys.version_info < (3, 10):
        pytest.skip("gliner requires Python >= 3.10")

    from presidio_analyzer.predefined_recognizers import GLiNERRecognizer

    mock_gliner = mock_gliner_for_batch
    mock_gliner.inference.return_value = [
        [{"label": "person", "start": 0, "end": 4, "score": 0.9}],
    ]

    entity_mapping = {"person": "PERSON"}
    rec = GLiNERRecognizer(
        entity_mapping=entity_mapping, inference_batch_size=16
    )
    rec.gliner = mock_gliner

    rec.batch_analyze(["John Doe"], ["PERSON"], [None])

    # Verify inference was called with batch_size=16
    call_kwargs = mock_gliner.inference.call_args[1]
    assert call_kwargs["batch_size"] == 16


def test_gliner_inference_batch_size_default(mock_gliner_for_batch):
    """Verify default inference_batch_size is 8."""
    if sys.version_info < (3, 10):
        pytest.skip("gliner requires Python >= 3.10")

    from presidio_analyzer.predefined_recognizers import GLiNERRecognizer

    rec = GLiNERRecognizer(supported_entities=["PERSON"])
    assert rec.inference_batch_size == 8


def test_gliner_batch_analyze_entity_filtering(mock_gliner_for_batch):
    """Verify entity filtering works in batch mode."""
    if sys.version_info < (3, 10):
        pytest.skip("gliner requires Python >= 3.10")

    from presidio_analyzer.predefined_recognizers import GLiNERRecognizer

    mock_gliner = mock_gliner_for_batch
    mock_gliner.inference.return_value = [
        [
            {"label": "person", "start": 0, "end": 8, "score": 0.9},
            {"label": "location", "start": 14, "end": 22, "score": 0.85},
        ],
    ]

    entity_mapping = {"person": "PERSON", "location": "LOCATION"}
    rec = GLiNERRecognizer(entity_mapping=entity_mapping)
    rec.gliner = mock_gliner

    # Only request PERSON
    results = rec.batch_analyze(["John Doe from New York"], ["PERSON"], [None])

    assert len(results) == 1
    assert len(results[0]) == 1
    assert results[0][0].entity_type == "PERSON"


# ---------------------------------------------------------------------------
# 7e. HuggingFaceNerRecognizer batch_size verification
# ---------------------------------------------------------------------------


def test_hf_batch_analyze_passes_batch_size(hf_recognizer):
    """Verify inference_batch_size is passed to pipeline as batch_size."""
    rec, mock_pipeline = hf_recognizer

    mock_pipeline.return_value = [
        [{"entity_group": "PER", "start": 0, "end": 8, "score": 0.95}],
    ]

    # Recreate with custom batch size
    from presidio_analyzer.predefined_recognizers import HuggingFaceNerRecognizer

    rec2 = HuggingFaceNerRecognizer(
        model_name=TEST_MODEL_NAME,
        supported_language="en",
        inference_batch_size=32,
    )
    mock_pipeline.return_value = [
        [{"entity_group": "PER", "start": 0, "end": 8, "score": 0.95}],
    ]
    rec2.batch_analyze(["John Doe"], ["PERSON"], [None])

    # Verify pipeline was called with batch_size=32
    call_kwargs = mock_pipeline.call_args[1]
    assert call_kwargs["batch_size"] == 32


def test_hf_inference_batch_size_default(hf_recognizer):
    """Verify default inference_batch_size is 8."""
    rec, _ = hf_recognizer
    assert rec.inference_batch_size == 8


# ---------------------------------------------------------------------------
# 7f. AnalyzerEngine.analyze_batch
# ---------------------------------------------------------------------------


def test_analyze_batch_matches_individual_analyze(analyzer_engine_simple):
    """analyze_batch produces same results as [analyze(t) for t in texts]."""
    texts = [
        "My name is David",
        "Call me at 2352351232",
        "Visit https://microsoft.com",
    ]

    batch_results = analyzer_engine_simple.analyze_batch(
        texts=texts, language="en"
    )

    individual_results = [
        analyzer_engine_simple.analyze(text=t, language="en") for t in texts
    ]

    assert len(batch_results) == len(individual_results)
    for batch_res, ind_res in zip(batch_results, individual_results):
        assert len(batch_res) == len(ind_res)
        for b, i in zip(
            sorted(batch_res, key=lambda r: (r.start, r.entity_type)),
            sorted(ind_res, key=lambda r: (r.start, r.entity_type)),
        ):
            assert b.entity_type == i.entity_type
            assert b.start == i.start
            assert b.end == i.end
            assert b.score == i.score


def test_analyze_batch_empty_texts(analyzer_engine_simple):
    """analyze_batch with empty list returns empty list."""
    results = analyzer_engine_simple.analyze_batch(texts=[], language="en")
    assert results == []


def test_analyze_batch_with_score_threshold(analyzer_engine_simple):
    """analyze_batch respects score_threshold."""
    texts = ["Call me at 2352351232"]
    results = analyzer_engine_simple.analyze_batch(
        texts=texts, language="en", score_threshold=0.99
    )
    # Phone number score is 0.4, should be filtered
    assert len(results) == 1
    assert results[0] == []


def test_analyze_batch_with_entities_filter(analyzer_engine_simple):
    """analyze_batch filters to requested entities only."""
    texts = ["Call me at 2352351232"]
    results = analyzer_engine_simple.analyze_batch(
        texts=texts, language="en", entities=["CREDIT_CARD"]
    )
    # Phone number should not appear when requesting CREDIT_CARD only
    assert len(results) == 1
    assert results[0] == []


def test_analyze_batch_with_allow_list(analyzer_engine_simple):
    """analyze_batch respects allow_list."""
    texts = ["Call me at 2352351232"]
    results = analyzer_engine_simple.analyze_batch(
        texts=texts,
        language="en",
        allow_list=["2352351232"],
    )
    assert len(results) == 1
    assert results[0] == []


def test_analyze_batch_with_precomputed_artifacts(analyzer_engine_simple):
    """analyze_batch accepts precomputed nlp_artifacts_list."""
    texts = ["Call me at 2352351232"]
    artifacts = [
        analyzer_engine_simple.nlp_engine.process_text(t, "en") for t in texts
    ]

    results = analyzer_engine_simple.analyze_batch(
        texts=texts, language="en", nlp_artifacts_list=artifacts
    )

    assert len(results) == 1
    assert len(results[0]) == 1
    assert results[0][0].entity_type == "PHONE_NUMBER"


def test_analyze_batch_artifacts_length_mismatch_raises(analyzer_engine_simple):
    """analyze_batch raises ValueError on nlp_artifacts_list length mismatch."""
    with pytest.raises(ValueError, match="Length mismatch"):
        analyzer_engine_simple.analyze_batch(
            texts=["a", "b"],
            language="en",
            nlp_artifacts_list=[],  # empty — mismatch
        )


def test_analyze_batch_recognizer_wrong_length_raises(analyzer_engine_simple):
    """analyze_batch raises when a recognizer returns a misaligned result list."""
    from presidio_analyzer import EntityRecognizer

    class _BadRecognizer(EntityRecognizer):
        def load(self):
            pass

        def analyze(self, text, entities, nlp_artifacts=None):
            return []

        def batch_analyze(self, texts, entities, nlp_artifacts_list):
            return [[]]  # always one list, regardless of input length

    rec = _BadRecognizer(supported_entities=["PERSON"], supported_language="en")
    with pytest.raises(ValueError, match="one result list per input text"):
        analyzer_engine_simple.analyze_batch(
            texts=["a", "b"], language="en", ad_hoc_recognizers=[rec]
        )


# ---------------------------------------------------------------------------
# 7g. Backward compatibility — BatchAnalyzerEngine
# (The existing tests in test_batch_analyzer_engine.py cover this;
#  here we add an explicit cross-check)
# ---------------------------------------------------------------------------


def test_analyze_iterator_processes_in_batch_size_slices(analyzer_engine_simple):
    """analyze_iterator bounds memory by calling analyze_batch per slice."""
    batch_engine = BatchAnalyzerEngine(analyzer_engine=analyzer_engine_simple)
    texts = [
        "Call me at 2352351232",
        "no entities",
        "still nothing",
        "nothing here",
        "or here",
    ]

    with patch.object(
        analyzer_engine_simple,
        "analyze_batch",
        wraps=analyzer_engine_simple.analyze_batch,
    ) as spy:
        results = batch_engine.analyze_iterator(
            texts=texts, language="en", batch_size=2
        )

    assert spy.call_count == 3  # slices of 2 + 2 + 1
    assert len(results) == 5
    assert results[0][0].entity_type == "PHONE_NUMBER"
    assert all(r == [] for r in results[1:])


def test_batch_analyzer_engine_backward_compat(analyzer_engine_simple):
    """BatchAnalyzerEngine.analyze_iterator still produces same results."""
    batch_engine = BatchAnalyzerEngine(analyzer_engine=analyzer_engine_simple)

    texts = ["My name is David", "Call me at 2352351232"]
    results = batch_engine.analyze_iterator(texts=texts, language="en")

    assert len(results) == 2
    # First text: no phone/credit card/url
    assert results[0] == []
    # Second text: phone number detected
    assert len(results[1]) == 1
    assert results[1][0].entity_type == "PHONE_NUMBER"
