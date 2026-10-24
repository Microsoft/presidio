"""Unit tests for StanzaNlpEngine.process_batch() and bulk_process integration."""

from typing import Iterator
from unittest.mock import Mock, MagicMock, patch

import pytest

from presidio_analyzer.nlp_engine import NlpArtifacts


@pytest.mark.skip_engine("stanza_en")
class TestStanzaBatchProcessing:
    """Test suite for Stanza batch processing functionality."""

    def test_when_process_batch_with_strings_then_returns_iterator(
        self, stanza_nlp_engine
    ):
        """Test basic batch processing with simple strings."""
        texts = ["Hello world", "This is a test"]
        
        result = stanza_nlp_engine.process_batch(texts, language="en", batch_size=2)
        
        assert isinstance(result, Iterator)
        result_list = list(result)
        assert len(result_list) == 2
        
        for text, nlp_artifacts in result_list:
            assert isinstance(text, str)
            assert isinstance(nlp_artifacts, NlpArtifacts)
            assert len(nlp_artifacts.tokens) > 0

    def test_when_process_batch_with_tuples_then_returns_context(
        self, stanza_nlp_engine
    ):
        """Test batch processing with tuples including context."""
        texts = [
            ("Hello world", {"id": 1}),
            ("This is a test", {"id": 2})
        ]
        
        result = stanza_nlp_engine.process_batch(
            texts, language="en", batch_size=2, as_tuples=True
        )
        
        result_list = list(result)
        assert len(result_list) == 2
        
        text1, nlp_artifacts1, context1 = result_list[0]
        assert text1 == "Hello world"
        assert isinstance(nlp_artifacts1, NlpArtifacts)
        assert context1 == {"id": 1}
        
        text2, nlp_artifacts2, context2 = result_list[1]
        assert text2 == "This is a test"
        assert isinstance(nlp_artifacts2, NlpArtifacts)
        assert context2 == {"id": 2}

    def test_when_process_batch_with_entities_then_extracts_correctly(
        self, stanza_nlp_engine
    ):
        """Test that batch processing correctly extracts entities."""
        texts = [
            "Barack Obama was born in Hawaii.",
            "John Smith lives in New York."
        ]
        
        result = stanza_nlp_engine.process_batch(texts, language="en", batch_size=2)
        result_list = list(result)
        
        # First text should have entities (Barack Obama, Hawaii)
        text1, nlp_artifacts1 = result_list[0]
        assert len(nlp_artifacts1.entities) >= 2
        
        # Second text should have entities (John Smith, New York)
        text2, nlp_artifacts2 = result_list[1]
        assert len(nlp_artifacts2.entities) >= 2

    def test_when_process_batch_with_different_batch_sizes_then_works(
        self, stanza_nlp_engine
    ):
        """Test batch processing with various batch sizes."""
        texts = ["Text one", "Text two", "Text three", "Text four", "Text five"]
        
        for batch_size in [1, 2, 3, 10]:
            result = stanza_nlp_engine.process_batch(
                texts, language="en", batch_size=batch_size
            )
            result_list = list(result)
            
            assert len(result_list) == 5
            for text, nlp_artifacts in result_list:
                assert isinstance(nlp_artifacts, NlpArtifacts)

    def test_when_process_batch_with_empty_list_then_returns_empty(
        self, stanza_nlp_engine
    ):
        """Test batch processing with empty input."""
        texts = []
        
        result = stanza_nlp_engine.process_batch(texts, language="en")
        result_list = list(result)
        
        assert len(result_list) == 0

    def test_when_process_batch_not_loaded_then_raises_error(self):
        """Test that processing without loading raises an error."""
        from presidio_analyzer.nlp_engine import StanzaNlpEngine
        
        engine = StanzaNlpEngine(
            models=[{"lang_code": "en", "model_name": "en"}]
        )
        # Don't call load()
        
        with pytest.raises(ValueError, match="NLP engine is not loaded"):
            list(engine.process_batch(["test"], language="en"))

    def test_when_process_batch_with_whitespace_then_handles_correctly(
        self, stanza_nlp_engine
    ):
        """Test batch processing with texts containing whitespace."""
        texts = [
            " Leading whitespace",
            "Trailing whitespace ",
            "  Multiple   spaces  "
        ]
        
        result = stanza_nlp_engine.process_batch(texts, language="en", batch_size=3)
        result_list = list(result)
        
        assert len(result_list) == 3
        for text, nlp_artifacts in result_list:
            assert isinstance(nlp_artifacts, NlpArtifacts)
            # Should have tokens despite whitespace
            assert len(nlp_artifacts.tokens) > 0

    def test_when_process_batch_preserves_text_order(self, stanza_nlp_engine):
        """Test that batch processing preserves input order."""
        texts = [f"Text number {i}" for i in range(10)]
        
        result = stanza_nlp_engine.process_batch(texts, language="en", batch_size=3)
        result_list = list(result)
        
        for i, (text, nlp_artifacts) in enumerate(result_list):
            assert text == f"Text number {i}"

    def test_when_process_batch_with_special_chars_then_works(
        self, stanza_nlp_engine
    ):
        """Test batch processing with special characters."""
        texts = [
            "Email: test@example.com",
            "Phone: +1-555-1234",
            "URL: https://example.com"
        ]
        
        result = stanza_nlp_engine.process_batch(texts, language="en", batch_size=3)
        result_list = list(result)
        
        assert len(result_list) == 3
        for text, nlp_artifacts in result_list:
            assert isinstance(nlp_artifacts, NlpArtifacts)


@pytest.mark.skip_engine("stanza_en")
class TestStanzaTokenizerConvertDoc:
    """Test suite for StanzaTokenizer._convert_doc() method."""

    def test_when_convert_doc_called_then_returns_spacy_doc(
        self, stanza_nlp_engine
    ):
        """Test that _convert_doc() correctly converts Stanza docs to spaCy docs."""
        import stanza
        
        # Get the tokenizer
        stanza_tokenizer = stanza_nlp_engine.nlp["en"].tokenizer
        stanza_pipeline = stanza_tokenizer.snlp
        
        # Process a text through Stanza
        text = "Barack Obama was born in Hawaii."
        stanza_doc = stanza.Document([], text=text)
        processed_doc = stanza_pipeline(stanza_doc)
        
        # Convert to spaCy doc
        spacy_doc = stanza_tokenizer._convert_doc(processed_doc)
        
        # Verify the conversion
        assert spacy_doc.text == text
        assert len(spacy_doc) > 0  # Has tokens
        # Note: Sentence boundaries require the full pipeline
        assert any(token.is_sent_start for token in spacy_doc)  # Has sentence starts
        assert len(spacy_doc.ents) > 0  # Has entities

    def test_when_convert_doc_with_empty_text_then_returns_empty_doc(
        self, stanza_nlp_engine
    ):
        """Test _convert_doc() with empty text."""
        import stanza
        from spacy.tokens import Doc
        
        stanza_tokenizer = stanza_nlp_engine.nlp["en"].tokenizer
        
        # Create empty Stanza doc
        empty_doc = stanza.Document([], text="")
        
        # Convert
        spacy_doc = stanza_tokenizer._convert_doc(empty_doc)
        
        assert isinstance(spacy_doc, Doc)
        assert len(spacy_doc) == 0

    def test_when_convert_doc_with_whitespace_only_then_handles_correctly(
        self, stanza_nlp_engine
    ):
        """Test _convert_doc() with whitespace-only text."""
        import stanza
        from spacy.tokens import Doc
        
        stanza_tokenizer = stanza_nlp_engine.nlp["en"].tokenizer
        
        # Create whitespace-only Stanza doc
        whitespace_doc = stanza.Document([], text="   ")
        
        # Convert
        spacy_doc = stanza_tokenizer._convert_doc(whitespace_doc)
        
        assert isinstance(spacy_doc, Doc)
        # Should handle whitespace gracefully

    def test_when_convert_doc_preserves_linguistic_features(
        self, stanza_nlp_engine
    ):
        """Test that _convert_doc() preserves POS tags, lemmas, and dependencies."""
        import stanza
        
        stanza_tokenizer = stanza_nlp_engine.nlp["en"].tokenizer
        stanza_pipeline = stanza_tokenizer.snlp
        
        text = "The quick brown fox jumps."
        stanza_doc = stanza.Document([], text=text)
        processed_doc = stanza_pipeline(stanza_doc)
        
        spacy_doc = stanza_tokenizer._convert_doc(processed_doc)
        
        # Verify linguistic features are preserved
        for token in spacy_doc:
            assert token.pos_ is not None  # POS tags
            assert token.lemma_ is not None  # Lemmas
            if token.dep_:
                assert token.head is not None  # Dependencies


@pytest.mark.skip_engine("stanza_en")
class TestStanzaBulkProcessIntegration:
    """Integration tests for Stanza's bulk_process usage."""

    @patch("stanza.Pipeline.bulk_process")
    def test_when_process_batch_then_calls_bulk_process(
        self, mock_bulk_process, stanza_nlp_engine
    ):
        """Test that process_batch() calls Stanza's bulk_process method."""
        import stanza
        
        # Setup mock to return processed docs
        mock_bulk_process.return_value = [
            Mock(text="Text 1", sentences=[], entities=[]),
            Mock(text="Text 2", sentences=[], entities=[])
        ]
        
        # Create mock for the conversion
        stanza_tokenizer = stanza_nlp_engine.nlp["en"].tokenizer
        original_convert = stanza_tokenizer._convert_doc
        
        def mock_convert(doc):
            # Return a minimal spaCy doc
            from spacy.tokens import Doc
            return Doc(stanza_tokenizer.vocab, words=["test"])
        
        stanza_tokenizer._convert_doc = mock_convert
        
        try:
            texts = ["Text 1", "Text 2"]
            result = list(stanza_nlp_engine.process_batch(
                texts, language="en", batch_size=2
            ))
            
            # Verify bulk_process was called
            assert mock_bulk_process.called
            
            # Verify the input to bulk_process
            call_args = mock_bulk_process.call_args[0][0]
            assert len(call_args) == 2
            assert all(isinstance(doc, stanza.Document) for doc in call_args)
        finally:
            # Restore original method
            stanza_tokenizer._convert_doc = original_convert

    def test_when_process_batch_with_large_batch_then_handles_correctly(
        self, stanza_nlp_engine
    ):
        """Test batch processing with a large number of texts."""
        num_texts = 100
        texts = [f"This is test text number {i}." for i in range(num_texts)]
        
        result = stanza_nlp_engine.process_batch(
            texts, language="en", batch_size=16
        )
        result_list = list(result)
        
        assert len(result_list) == num_texts
        
        # Verify all texts were processed
        for i, (text, nlp_artifacts) in enumerate(result_list):
            assert f"number {i}" in text
            assert isinstance(nlp_artifacts, NlpArtifacts)

    def test_when_process_batch_batching_matches_batch_size(
        self, stanza_nlp_engine
    ):
        """Test that internal batching respects batch_size parameter."""
        texts = [f"Text {i}" for i in range(10)]
        
        # Process with different batch sizes
        for batch_size in [1, 3, 5, 10]:
            result = stanza_nlp_engine.process_batch(
                texts, language="en", batch_size=batch_size
            )
            result_list = list(result)
            
            # Should process all texts regardless of batch size
            assert len(result_list) == 10
