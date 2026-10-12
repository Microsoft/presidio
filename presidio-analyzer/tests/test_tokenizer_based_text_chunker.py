"""Tests for TokenizerBasedTextChunker."""
from unittest.mock import MagicMock

import pytest

from presidio_analyzer.chunkers.tokenizer_based_text_chunker import (
    TokenizerBasedTextChunker,
)


def _make_tokenizer(tokens: list, offsets: list, model_max_length: int = 512):
    """Build a minimal mock tokenizer that returns fixed token/offset data."""
    tokenizer = MagicMock()
    tokenizer.model_max_length = model_max_length
    tokenizer.num_special_tokens_to_add = lambda pair=False: 0
    tokenizer.return_value = {
        "input_ids": tokens,
        "offset_mapping": offsets,
    }
    return tokenizer


def test_short_text_returns_single_chunk():
    """Text shorter than max_tokens produces exactly one chunk covering full text."""
    text = "Hello world"
    # 2 tokens, well within max_tokens=512
    tokens = [1, 2]
    offsets = [(0, 5), (6, 11)]
    tokenizer = _make_tokenizer(tokens, offsets)

    chunker = TokenizerBasedTextChunker(tokenizer=tokenizer, max_tokens=512)
    chunks = chunker.chunk(text)

    assert len(chunks) == 1
    assert chunks[0].start == 0
    assert chunks[0].end == len(text)
    assert chunks[0].text == text


def test_empty_text_returns_no_chunks():
    tokenizer = _make_tokenizer([], [])
    chunker = TokenizerBasedTextChunker(tokenizer=tokenizer, max_tokens=10, overlap_tokens=2)
    assert chunker.chunk("") == []


def test_long_text_splits_into_multiple_chunks():
    """Text with more tokens than max_tokens is split into overlapping chunks."""
    # 10 tokens, each occupying 2 chars: "aa bb cc dd ee ff gg hh ii jj"
    text = "aa bb cc dd ee ff gg hh ii jj"
    offsets = [
        (0, 2), (3, 5), (6, 8), (9, 11), (12, 14),
        (15, 17), (18, 20), (21, 23), (24, 26), (27, 29),
    ]
    tokens = list(range(10))
    tokenizer = _make_tokenizer(tokens, offsets)

    chunker = TokenizerBasedTextChunker(tokenizer=tokenizer, max_tokens=4, overlap_tokens=1)
    chunks = chunker.chunk(text)

    # step = 4 - 1 = 3 tokens per advance
    # chunk 0: tokens 0-3  -> chars 0..11
    # chunk 1: tokens 3-6  -> chars 9..20
    # chunk 2: tokens 6-9  -> chars 18..29
    assert len(chunks) == 3
    assert chunks[0].start == 0
    assert chunks[0].end == offsets[3][1]
    assert chunks[1].start == offsets[3][0]
    assert chunks[2].end == offsets[9][1]


def test_chunks_have_correct_text_content():
    text = "hello world foo"
    offsets = [(0, 5), (6, 11), (12, 15)]
    tokens = [1, 2, 3]
    tokenizer = _make_tokenizer(tokens, offsets)

    chunker = TokenizerBasedTextChunker(tokenizer=tokenizer, max_tokens=2, overlap_tokens=0)
    chunks = chunker.chunk(text)

    assert chunks[0].text == text[chunks[0].start:chunks[0].end]
    assert chunks[1].text == text[chunks[1].start:chunks[1].end]


def test_default_max_tokens_fallback_for_absurd_value():
    """Tokenizers with unrealistic model_max_length fall back to 512."""
    tokenizer = _make_tokenizer([], [], model_max_length=int(1e30))
    chunker = TokenizerBasedTextChunker(tokenizer=tokenizer)
    assert chunker.max_tokens == 512


def test_default_max_tokens_uses_model_max_length():
    """Tokenizers with reasonable model_max_length are respected."""
    tokenizer = _make_tokenizer([], [], model_max_length=1024)
    chunker = TokenizerBasedTextChunker(tokenizer=tokenizer)
    assert chunker.max_tokens == 1024


def test_default_max_tokens_uses_small_model_max_length():
    tokenizer = _make_tokenizer([], [], model_max_length=128)
    chunker = TokenizerBasedTextChunker(tokenizer=tokenizer, overlap_tokens=10)
    assert chunker.max_tokens == 128


def test_invalid_max_tokens_raises():
    tokenizer = _make_tokenizer([], [])
    with pytest.raises(ValueError, match="max_tokens must be greater than 0"):
        TokenizerBasedTextChunker(tokenizer=tokenizer, max_tokens=0)


def test_invalid_overlap_raises():
    tokenizer = _make_tokenizer([], [])
    with pytest.raises(ValueError, match="overlap_tokens"):
        TokenizerBasedTextChunker(tokenizer=tokenizer, max_tokens=10, overlap_tokens=10)


def test_default_max_tokens_reserves_special_tokens():
    """Auto-derived max_tokens subtracts special tokens (e.g. [CLS], [SEP])."""
    tokenizer = _make_tokenizer([], [], model_max_length=512)
    tokenizer.num_special_tokens_to_add = lambda pair=False: 2
    chunker = TokenizerBasedTextChunker(tokenizer=tokenizer)
    assert chunker.max_tokens == 510


def test_explicit_max_tokens_does_not_reserve_special_tokens():
    """User-provided max_tokens is used as-is without subtracting special tokens."""
    tokenizer = _make_tokenizer([], [], model_max_length=512)
    tokenizer.num_special_tokens_to_add = lambda pair=False: 2
    chunker = TokenizerBasedTextChunker(tokenizer=tokenizer, max_tokens=500)
    assert chunker.max_tokens == 500


def test_text_chunker_provider_creates_tokenizer_chunker():
    """TextChunkerProvider with chunker_type='tokenizer' creates TokenizerBasedTextChunker."""
    from presidio_analyzer.chunkers.text_chunker_provider import TextChunkerProvider

    mock_tokenizer = _make_tokenizer([], [], model_max_length=512)

    provider = TextChunkerProvider(
        {"chunker_type": "tokenizer", "tokenizer": mock_tokenizer, "max_tokens": 256, "overlap_tokens": 16}
    )
    chunker = provider.create_chunker()

    assert isinstance(chunker, TokenizerBasedTextChunker)
    assert chunker.max_tokens == 256
    assert chunker.overlap_tokens == 16


def test_text_chunker_provider_unknown_type_raises():
    """TextChunkerProvider with unknown chunker_type raises ValueError."""
    from presidio_analyzer.chunkers.text_chunker_provider import TextChunkerProvider

    provider = TextChunkerProvider({"chunker_type": "unknown"})
    with pytest.raises(ValueError, match="Unknown chunker_type"):
        provider.create_chunker()


def test_invalid_text_chunker_dict_rejected_by_pydantic():
    """Invalid text_chunker dict is rejected by Pydantic validation layer."""
    from pydantic import ValidationError
    from presidio_analyzer.input_validation.yaml_recognizer_models import (
        HuggingFaceRecognizerConfig,
    )

    with pytest.raises(ValidationError, match="chunker_type"):
        HuggingFaceRecognizerConfig(
            name="HuggingFaceNerRecognizer",
            text_chunker={"chunker_type": "nonexistent"},
        )


def test_slow_tokenizer_raises():
    """Passing a slow tokenizer (is_fast=False) raises ValueError at init."""
    tokenizer = _make_tokenizer([], [], model_max_length=512)
    tokenizer.is_fast = False
    with pytest.raises(ValueError, match="fast tokenizer"):
        TokenizerBasedTextChunker(tokenizer=tokenizer)


def test_overlap_clamped_for_small_auto_derived_max_tokens():
    """overlap_tokens is clamped when auto-derived max_tokens is smaller than default overlap."""
    tokenizer = _make_tokenizer([], [], model_max_length=30)
    # default overlap_tokens=32, but max_tokens will be 30 → overlap clamped to 29
    chunker = TokenizerBasedTextChunker(tokenizer=tokenizer)
    assert chunker.max_tokens == 30
    assert chunker.overlap_tokens == 29


def test_deferred_mode_without_tokenizer():
    """Omitting tokenizer creates a deferred chunker."""
    chunker = TokenizerBasedTextChunker(max_tokens=256, overlap_tokens=16)
    assert chunker.is_deferred
    assert chunker.tokenizer is None
    assert chunker.max_tokens == 256
    assert chunker.overlap_tokens == 16


def test_deferred_chunk_raises_before_resolve():
    """Calling chunk() on a deferred chunker raises RuntimeError."""
    chunker = TokenizerBasedTextChunker(max_tokens=256)
    with pytest.raises(RuntimeError, match="no tokenizer"):
        chunker.chunk("hello")


def test_deferred_resolve_with_tokenizer():
    """resolve() initializes the chunker with the provided tokenizer."""
    chunker = TokenizerBasedTextChunker(max_tokens=256, overlap_tokens=16)
    assert chunker.is_deferred

    tokenizer = _make_tokenizer([1, 2], [(0, 5), (6, 11)], model_max_length=512)
    chunker.resolve(tokenizer)

    assert not chunker.is_deferred
    assert chunker.tokenizer is tokenizer
    assert chunker.max_tokens == 256
    assert chunker.overlap_tokens == 16


def test_deferred_resolve_auto_derives_max_tokens():
    """resolve() with max_tokens=None derives from tokenizer's model_max_length."""
    chunker = TokenizerBasedTextChunker()  # all defaults, deferred
    assert chunker.is_deferred

    tokenizer = _make_tokenizer([], [], model_max_length=1024)
    chunker.resolve(tokenizer)

    assert chunker.max_tokens == 1024


def test_deferred_chunker_works_after_resolve():
    """A deferred chunker chunks correctly after resolve()."""
    text = "Hello world"
    tokens = [1, 2]
    offsets = [(0, 5), (6, 11)]
    tokenizer = _make_tokenizer(tokens, offsets, model_max_length=512)

    chunker = TokenizerBasedTextChunker(max_tokens=512)
    chunker.resolve(tokenizer)

    chunks = chunker.chunk(text)
    assert len(chunks) == 1
    assert chunks[0].text == text


def test_provider_creates_deferred_without_tokenizer():
    """TextChunkerProvider creates deferred chunker when tokenizer is omitted."""
    from presidio_analyzer.chunkers.text_chunker_provider import TextChunkerProvider

    provider = TextChunkerProvider(
        {"chunker_type": "tokenizer", "max_tokens": 384, "overlap_tokens": 16}
    )
    chunker = provider.create_chunker()

    assert isinstance(chunker, TokenizerBasedTextChunker)
    assert chunker.is_deferred
    assert chunker.max_tokens == 384


def test_missing_offset_mapping_raises():
    """Tokenizer that doesn't return offset_mapping raises ValueError."""
    tokenizer = MagicMock()
    tokenizer.model_max_length = 512
    tokenizer.num_special_tokens_to_add = lambda pair=False: 0
    # Return encoding without offset_mapping
    tokenizer.return_value = {"input_ids": [1, 2]}

    chunker = TokenizerBasedTextChunker(tokenizer=tokenizer, max_tokens=512)
    with pytest.raises(ValueError, match="offset_mapping"):
        chunker.chunk("hello world")
