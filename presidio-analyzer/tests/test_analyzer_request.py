import regex as re
from presidio_analyzer import AnalyzerRequest, PatternRecognizer


class TestAnalyzerRequest:
    """Tests for AnalyzerRequest class."""

    def test_analyzer_request_basic_fields(self):
        """Test basic field initialization."""
        req_data = {
            "text": "My phone number is 555-1234",
            "language": "en",
            "entities": ["PHONE_NUMBER"],
            "correlation_id": "test-123",
            "score_threshold": 0.5,
            "return_decision_process": True,
        }

        request = AnalyzerRequest(req_data)

        assert request.text == "My phone number is 555-1234"
        assert request.language == "en"
        assert request.entities == ["PHONE_NUMBER"]
        assert request.correlation_id == "test-123"
        assert request.score_threshold == 0.5
        assert request.return_decision_process is True

    def test_analyzer_request_with_context(self):
        """Test context field initialization (line 37)."""
        req_data = {
            "text": "Test text",
            "language": "en",
            "context": ["previous message", "current message"]
        }

        request = AnalyzerRequest(req_data)

        assert request.context == ["previous message", "current message"]

    def test_analyzer_request_with_allow_list(self):
        """Test allow_list field initialization (line 38)."""
        req_data = {
            "text": "Test text",
            "language": "en",
            "allow_list": ["John", "Microsoft", "Seattle"]
        }

        request = AnalyzerRequest(req_data)

        assert request.allow_list == ["John", "Microsoft", "Seattle"]

    def test_analyzer_request_with_allow_list_match_default(self):
        """Test allow_list_match field with default value (line 39)."""
        req_data = {
            "text": "Test text",
            "language": "en",
        }

        request = AnalyzerRequest(req_data)

        # Should default to "exact"
        assert request.allow_list_match == "exact"

    def test_analyzer_request_with_allow_list_match_custom(self):
        """Test allow_list_match field with custom value (line 39)."""
        req_data = {
            "text": "Test text",
            "language": "en",
            "allow_list_match": "partial"
        }

        request = AnalyzerRequest(req_data)

        assert request.allow_list_match == "partial"

    def test_analyzer_request_with_regex_flags_default(self):
        """Test regex_flags field with default value (line 40)."""
        req_data = {
            "text": "Test text",
            "language": "en",
        }

        request = AnalyzerRequest(req_data)

        # Should default to DOTALL | MULTILINE | IGNORECASE
        expected_flags = re.DOTALL | re.MULTILINE | re.IGNORECASE
        assert request.regex_flags == expected_flags

    def test_analyzer_request_with_regex_flags_custom(self):
        """Test regex_flags field with custom value (line 40)."""
        custom_flags = re.IGNORECASE | re.UNICODE
        req_data = {
            "text": "Test text",
            "language": "en",
            "regex_flags": custom_flags
        }

        request = AnalyzerRequest(req_data)

        assert request.regex_flags == custom_flags

    def test_analyzer_request_without_context(self):
        """Test that context is None when not provided."""
        req_data = {
            "text": "Test text",
            "language": "en",
        }

        request = AnalyzerRequest(req_data)

        assert request.context is None

    def test_analyzer_request_without_allow_list(self):
        """Test that allow_list is None when not provided."""
        req_data = {
            "text": "Test text",
            "language": "en",
        }

        request = AnalyzerRequest(req_data)

        assert request.allow_list is None

    def test_analyzer_request_all_fields(self):
        """Test initialization with all fields including lines 37-40."""
        req_data = {
            "text": "My name is John and my email is john@example.com",
            "language": "en",
            "entities": ["PERSON", "EMAIL_ADDRESS"],
            "correlation_id": "full-test-456",
            "score_threshold": 0.7,
            "return_decision_process": False,
            "ad_hoc_recognizers": [
                {
                    "supported_entity": "CUSTOM_ENTITY",
                    "supported_language": "en",
                    "patterns": [
                        {
                            "name": "custom_pattern",
                            "regex": r"\d{3}-\d{3}",
                            "score": 0.5
                        }
                    ]
                }
            ],
            "context": ["user profile", "chat history"],
            "allow_list": ["John", "Microsoft"],
            "allow_list_match": "fuzzy",
            "regex_flags": re.IGNORECASE
        }

        request = AnalyzerRequest(req_data)

        assert request.text == "My name is John and my email is john@example.com"
        assert request.language == "en"
        assert request.entities == ["PERSON", "EMAIL_ADDRESS"]
        assert request.correlation_id == "full-test-456"
        assert request.score_threshold == 0.7
        assert request.return_decision_process is False
        assert len(request.ad_hoc_recognizers) == 1
        assert isinstance(request.ad_hoc_recognizers[0], PatternRecognizer)
        assert request.context == ["user profile", "chat history"]
        assert request.allow_list == ["John", "Microsoft"]
        assert request.allow_list_match == "fuzzy"
        assert request.regex_flags == re.IGNORECASE

    def test_analyzer_request_with_ad_hoc_recognizers(self):
        """Test ad_hoc_recognizers field initialization."""
        req_data = {
            "text": "Test text",
            "language": "en",
            "ad_hoc_recognizers": [
                {
                    "supported_entity": "CUSTOM_ID",
                    "supported_language": "en",
                    "patterns": [
                        {
                            "name": "id_pattern",
                            "regex": r"ID-\d{5}",
                            "score": 0.8
                        }
                    ]
                }
            ]
        }

        request = AnalyzerRequest(req_data)

        assert len(request.ad_hoc_recognizers) == 1
        assert isinstance(request.ad_hoc_recognizers[0], PatternRecognizer)
        assert request.ad_hoc_recognizers[0].supported_entities == ["CUSTOM_ID"]

    def test_analyzer_request_with_ad_hoc_recognizer_capture_group(self):
        """Test that a pattern capture_group reaches the ad-hoc recognizer."""
        req_data = {
            "text": "Employee ID-12345",
            "language": "en",
            "ad_hoc_recognizers": [
                {
                    "supported_entity": "CUSTOM_ID",
                    "supported_language": "en",
                    "patterns": [
                        {
                            "name": "id_pattern",
                            "regex": r"ID-(\d{5})",
                            "score": 0.8,
                            "capture_group": 1
                        }
                    ]
                }
            ]
        }

        request = AnalyzerRequest(req_data)

        recognizer = request.ad_hoc_recognizers[0]
        assert recognizer.patterns[0].capture_group == 1
        results = recognizer.analyze(request.text, ["CUSTOM_ID"])
        assert [(result.start, result.end) for result in results] == [(12, 17)]

    def test_analyzer_request_without_ad_hoc_recognizers(self):
        """Test that ad_hoc_recognizers is empty list when not provided."""
        req_data = {
            "text": "Test text",
            "language": "en",
        }

        request = AnalyzerRequest(req_data)

        assert request.ad_hoc_recognizers == []

    def test_analyzer_request_empty_dict(self):
        """Test initialization with empty dictionary."""
        req_data = {}

        request = AnalyzerRequest(req_data)

        assert request.text is None
        assert request.language is None
        assert request.entities is None
        assert request.correlation_id is None
        assert request.score_threshold is None
        assert request.return_decision_process is None
        assert request.ad_hoc_recognizers == []
        assert request.context is None
        assert request.allow_list is None
        assert request.allow_list_match == "exact"
        assert request.regex_flags == (re.DOTALL | re.MULTILINE | re.IGNORECASE)

    def test_analyzer_request_with_complex_context(self):
        """Test context field with various data types."""
        req_data = {
            "text": "Test text",
            "language": "en",
            "context": {
                "user_id": "12345",
                "session": "abc",
                "metadata": {"key": "value"}
            }
        }

        request = AnalyzerRequest(req_data)

        assert request.context == {
            "user_id": "12345",
            "session": "abc",
            "metadata": {"key": "value"}
        }

    def test_analyzer_request_with_multiple_regex_flags(self):
        """Test regex_flags with multiple combined flags."""
        custom_flags = re.IGNORECASE | re.MULTILINE | re.DOTALL | re.VERBOSE
        req_data = {
            "text": "Test text",
            "language": "en",
            "regex_flags": custom_flags
        }

        request = AnalyzerRequest(req_data)

        assert request.regex_flags == custom_flags
        # Verify individual flags are present
        assert request.regex_flags & re.IGNORECASE
        assert request.regex_flags & re.MULTILINE
        assert request.regex_flags & re.DOTALL
        assert request.regex_flags & re.VERBOSE

    def test_analyzer_request_allow_list_match_variations(self):
        """Test various allow_list_match values."""
        test_cases = [
            "exact",
            "partial",
            "fuzzy",
            "regex",
            "custom_match_type"
        ]

        for match_type in test_cases:
            req_data = {
                "text": "Test text",
                "language": "en",
                "allow_list_match": match_type
            }

            request = AnalyzerRequest(req_data)
            assert request.allow_list_match == match_type

