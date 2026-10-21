import pytest
from common.assertions import equal_json_strings
from common.methods import analyze, analyzer_supported_entities


@pytest.mark.api
def test_given_a_correct_analyze_input_then_return_full_response():
    request_body = """
    {
        "text": "John Smith drivers license is AC432223",
        "language": "en"
    }
    """

    response_status, response_content = analyze(request_body)

    expected_response = """
    [
        {"entity_type": "PERSON", "start": 0, "end": 10, "score": 0.85, "analysis_explanation":null},
        {"entity_type": "US_DRIVER_LICENSE", "start": 30, "end": 38, "score": 0.6499999999999999, "analysis_explanation":null}
    ]
    """
    assert response_status == 200
    assert equal_json_strings(
        expected_response, response_content
    )


@pytest.mark.api
def test_given_analyze_threshold_input_then_return_result_above_threshold():
    request_body = """
    {
        "text": "John Smith drivers license is AC432223", 
        "language": "en", "score_threshold": 0.7
    }
    """

    response_status, response_content = analyze(request_body)

    expected_response = """
    [
        {"entity_type": "PERSON", "start": 0, "end": 10, "score": 0.85, 
        "analysis_explanation": null
        }
    ]
    """
    assert response_status == 200
    assert equal_json_strings(
        expected_response, response_content
    )


@pytest.mark.api
def test_given_no_analyze_text_input_then_return_error():
    request_body = "{}"

    response_status, response_content = analyze(request_body)

    expected_response = """
        {"error": "No text provided"}
    """
    assert response_status == 500
    assert equal_json_strings(expected_response, response_content)


@pytest.mark.api
def test_given_no_analyze_language_input_then_return_error():
    request_body = """
    {"language": "en"}
    """

    response_status, response_content = analyze(request_body)

    expected_response = """ 
        {"error": "No text provided"}
    """
    assert response_status == 500
    assert equal_json_strings(expected_response, response_content)


@pytest.mark.api
def test_given_analyze_text_no_language_input_then_return_error():
    request_body = """
    {
        "text": "John Smith drivers license is AC432223"
    }
    """

    response_status, response_content = analyze(request_body)

    expected_response = """ 
        {"error": "No language provided"} 
    """
    assert response_status == 500
    assert equal_json_strings(expected_response, response_content)


@pytest.mark.api
def test_given_a_incorrect_analyze_language_input_then_return_error():
    request_body = """
    {
        "text": "John Smith drivers license is AC432223", "language": "zz"
    }
    """

    response_status, response_content = analyze(request_body)

    assert response_status == 500
    expected_response = """ 
         {"error": "No matching recognizers were found to serve the request."}
    """
    assert equal_json_strings(expected_response, response_content)


@pytest.mark.api
def test_given_partially_unsupported_entities_then_return_supported_results():
    request_body = """
    {
        "text": "codice fiscale RSSMRA85M01H501Q, IBAN IT60X0542811101000000123456",
        "language": "en",
        "entities": ["IT_FISCAL_CODE", "IBAN_CODE"]
    }
    """

    response_status, response_content = analyze(request_body)

    expected_response = """
    [
        {"entity_type": "IBAN_CODE", "start": 38, "end": 65, "score": 1.0, "analysis_explanation": null}
    ]
    """
    assert response_status == 200
    assert equal_json_strings(expected_response, response_content)


@pytest.mark.api
def test_given_a_correlationid_analyze_input_then_return_normal_response():
    request_body = """
    {
        "text": "John Smith drivers license is AC432223", 
        "language": "en", "correlation_id": "123"
    }
    """

    response_status, response_content = analyze(request_body)

    assert response_status == 200


@pytest.mark.api
def test_given_a_trace_true_analyze_input_then_return_normal_response():
    request_body = """
    {
        "text": "John Smith drivers license is AC432223", 
        "language": "en", "trace": "1"
    }
    """

    response_status, response_content = analyze(request_body)

    assert response_status == 200


@pytest.mark.api
def test_given_a_trace_invalid_value_analyze_input_then_return_normal_response():
    request_body = """
    {
        "text": "John Smith drivers license is AC432223", 
        "language": "en", "trace": "somedata"
    }
    """

    response_status, response_content = analyze(request_body)

    assert response_status == 200


@pytest.mark.api
def test_given_return_decision_process_false_for_analyze_input_then_return_response_without_analysis():
    request_body = """  
    {
        "text": "John Smith drivers license is AC432223", 
        "language": "en", "return_decision_process": 0
    }
    """
    response_status, response_content = analyze(request_body)

    expected_response = """
    [
        {"entity_type": "PERSON", "start": 0, "end": 10, "score": 0.85, "analysis_explanation": null},
        {"entity_type": "US_DRIVER_LICENSE", "start": 30, "end": 38, "score": 0.6499999999999999, "analysis_explanation": null}
    ]
    """
    assert response_status == 200
    assert equal_json_strings(
        expected_response, response_content
    )


@pytest.mark.api
def test_given_decision_process_enabled_for_analyze_input_then_return_response_with_decision_process():
    request_body = """
    {
        "text": "John Smith license is AC432223", "language": "en", "return_decision_process": true
    }
    """
    response_status, response_content = analyze(request_body)

    expected_response = """
    [
        {"entity_type": "PERSON", "start": 0, "end": 10, "score": 0.85,
        "analysis_explanation": {
            "recognizer": "SpacyRecognizer", "pattern_name": null, "pattern": null, "original_score": 0.85, "score": 0.85, 
            "textual_explanation": "Identified as PERSON by Spacy's Named Entity Recognition", 
            "score_context_improvement": 0, "supportive_context_word": "", "validation_result": null 
            }
        },
        {"entity_type": "US_DRIVER_LICENSE", "start": 22, "end": 30, "score": 0.6499999999999999, 
        "analysis_explanation": {
            "recognizer": "UsLicenseRecognizer", "pattern_name": "Driver License - Alphanumeric (weak)", 
            "pattern": "\\\\b([A-Z][0-9]{3,6}|[A-Z][0-9]{5,9}|[A-Z][0-9]{6,8}|[A-Z][0-9]{4,8}|[A-Z][0-9]{9,11}|[A-Z]{1,2}[0-9]{5,6}|H[0-9]{8}|V[0-9]{6}|X[0-9]{8}|A-Z]{2}[0-9]{2,5}|[A-Z]{2}[0-9]{3,7}|[0-9]{2}[A-Z]{3}[0-9]{5,6}|[A-Z][0-9]{13,14}|[A-Z][0-9]{18}|[A-Z][0-9]{6}R|[A-Z][0-9]{9}|[A-Z][0-9]{1,12}|[0-9]{9}[A-Z]|[A-Z]{2}[0-9]{6}[A-Z]|[0-9]{8}[A-Z]{2}|[0-9]{3}[A-Z]{2}[0-9]{4}|[A-Z][0-9][A-Z][0-9][A-Z]|[0-9]{7,8}[A-Z])\\\\b", 
            "original_score": 0.3, "score": 0.6499999999999999, "textual_explanation": null, 
            "score_context_improvement": 0.3499999999999999, "supportive_context_word": "license", "validation_result": null
            }
        }
    ]
    """
    assert response_status == 200
    assert equal_json_strings(
        expected_response, response_content
    )


@pytest.mark.api
def test_given_decision_process_enabled_for_analyze_input_with_aditional_context_then_return_response_with_decision_process_and_correct_supportive_context_word():
    request_body = """
    {
        "text": "John Smith D.L. is AC432223", "language": "en", "return_decision_process": true, "context": ["Driver license"]
    }
    """
    response_status, response_content = analyze(request_body)

    expected_response = """
    [
        {
            "analysis_explanation": {
                "original_score": 0.85,
                "pattern": null,
                "pattern_name": null,
                "recognizer": "SpacyRecognizer",
                "score": 0.85,
                "score_context_improvement": 0,
                "supportive_context_word": "",
                "textual_explanation": "Identified as PERSON by Spacy\'s Named Entity Recognition",
                "validation_result": null
            },
            "end": 15,
            "entity_type": "PERSON",
            "score": 0.85,
            "start": 0
        },
        {
            "analysis_explanation": {
                "original_score": 0.3,
                "pattern": "\\\\b([A-Z][0-9]{3,6}|[A-Z][0-9]{5,9}|[A-Z][0-9]{6,8}|[A-Z][0-9]{4,8}|[A-Z][0-9]{9,11}|[A-Z]{1,2}[0-9]{5,6}|H[0-9]{8}|V[0-9]{6}|X[0-9]{8}|A-Z]{2}[0-9]{2,5}|[A-Z]{2}[0-9]{3,7}|[0-9]{2}[A-Z]{3}[0-9]{5,6}|[A-Z][0-9]{13,14}|[A-Z][0-9]{18}|[A-Z][0-9]{6}R|[A-Z][0-9]{9}|[A-Z][0-9]{1,12}|[0-9]{9}[A-Z]|[A-Z]{2}[0-9]{6}[A-Z]|[0-9]{8}[A-Z]{2}|[0-9]{3}[A-Z]{2}[0-9]{4}|[A-Z][0-9][A-Z][0-9][A-Z]|[0-9]{7,8}[A-Z])\\\\b",
                "pattern_name": "Driver License - Alphanumeric (weak)",
                "recognizer": "UsLicenseRecognizer",
                "score": 0.6499999999999999,
                "score_context_improvement": 0.3499999999999999,
                "supportive_context_word": "driver",
                "textual_explanation": null,
                "validation_result": null
            },
            "end": 27,
            "entity_type": "US_DRIVER_LICENSE",
            "score": 0.6499999999999999,
            "start": 19
        }
    ]
    """
    assert response_status == 200
    assert equal_json_strings(
        expected_response, response_content
    )


def test_given_analyze_entities_input_then_return_results_only_with_those_entities():
    request_body = """
    {
        "text": "John Smith drivers license is AC432223", "language": "en", "entities": ["PERSON"]
    }
    """

    response_status, response_content = analyze(request_body)

    expected_response = """
    [ 
        {"entity_type": "PERSON", "start": 0, "end": 10, "score": 0.85, 
        "analysis_explanation": null
        }
    ]
    """
    assert response_status == 200
    assert equal_json_strings(
        expected_response, response_content
    )


@pytest.mark.api
def test_given_a_correct_input_for_supported_entities_then_expect_a_correct_response():
    language_query_parameter = "language=en"

    response_status, response_content = analyzer_supported_entities(
        language_query_parameter
    )

    expected_response = """
        ["PHONE_NUMBER", "US_DRIVER_LICENSE", "US_PASSPORT", "SG_NRIC_FIN", "LOCATION", "CREDIT_CARD", "CRYPTO", 
        "UK_NHS", "US_SSN", "US_BANK_NUMBER", "EMAIL_ADDRESS", "DATE_TIME", "IP_ADDRESS", "PERSON", "IBAN_CODE", 
        "NRP", "US_ITIN", "MEDICAL_LICENSE", "AU_ABN", "AU_ACN", "AU_TFN", "AU_MEDICARE", "URL"]
    """
    assert response_status == 200
    assert equal_json_strings(expected_response, response_content)


@pytest.mark.api
def test_given_a_unsupported_language_for_supported_entities_then_expect_an_error():
    language_query_parameter = "language=he"

    response_status, response_content = analyzer_supported_entities(
        language_query_parameter
    )

    expected_response = """
       {"error": "No matching recognizers were found to serve the request."}
    """
    assert response_status == 500
    assert equal_json_strings(expected_response, response_content)


@pytest.mark.api
def test_given_an_illegal_input_for_supported_entities_then_igonre_and_proceed():
    language_query_parameter = "uknown=input"

    response_status, response_content = analyzer_supported_entities(
        language_query_parameter
    )

    expected_response = """ 
        ["PHONE_NUMBER", "US_DRIVER_LICENSE", "US_PASSPORT", "SG_NRIC_FIN", "LOCATION", "CREDIT_CARD", 
         "CRYPTO", "UK_NHS", "US_SSN", "US_BANK_NUMBER", "EMAIL_ADDRESS", "DATE_TIME", "IP_ADDRESS",
          "PERSON", "IBAN_CODE", "NRP", "US_ITIN", "MEDICAL_LICENSE", "AU_ABN", 
          "AU_ACN", "AU_TFN", "AU_MEDICARE", "URL"]
    """
    assert response_status == 200
    assert equal_json_strings(expected_response, response_content)


@pytest.mark.api
def test_given_ad_hoc_pattern_recognizer_the_right_entities_are_returned():
    request_body = r"""
     {
         "text": "John Smith drivers license is AC432223. Zip code: 10023",
         "language": "en",
         "ad_hoc_recognizers":[
             {
                "name": "Zip code Recognizer",
                "supported_language": "en",
                "patterns": [
                    {
                    "name": "zip code (weak)", 
                    "regex": "(\\b\\d{5}(?:\\-\\d{4})?\\b)", 
                    "score": 0.01
                    }
                ],
                "supported_entity":"ZIP"
            }
        ]
     }
     """

    response_status, response_content = analyze(request_body)

    expected_response = """
     [
         {"entity_type": "PERSON", "start": 0, "end": 10, "score": 0.85, "analysis_explanation":null},
         {"entity_type": "US_DRIVER_LICENSE", "start": 30, "end": 38, "score": 0.6499999999999999, "analysis_explanation":null},
         {"entity_type": "ZIP", "start": 50, "end": 55, "score": 0.01, "analysis_explanation":null}
     ]
     """
    assert response_status == 200
    assert equal_json_strings(
        expected_response, response_content
    )


def test_given_wrong_ad_hoc_json_exception_is_given():
    malformed_request_body = r"""
      {
          "text": "John Smith drivers license is AC432223. Zip code: 10023",
          "language": "en",
          "ad_hoc_recognizers":[
              {
                 "name": "Zip code Recognizer",
                 "supported_language": "en",
                 "patterns": [
                     {
                     "type": "zip code (weak)", 
                     "bebex": "(\\b\\d{5}(?:\\-\\d{4})?\\b)", 
                     "confidence": 0.01
                     }
                 ],
                 "supported_entity":"ZIP"
             }
         ]
      }
      """
    response_status, response_content = analyze(malformed_request_body)

    expected_response = """
    {
      "error": "Failed to parse /analyze request for AnalyzerEngine.analyze(). Pattern.__init__() got an unexpected keyword argument 'type'"
    }
    """

    assert equal_json_strings(expected_response, response_content)
    assert response_status == 400


def test_given_ad_hoc_pattern_recognizer_context_raises_confidence():
    request_body = r"""
     {
         "text": "John Smith drivers license is AC432223. Zip code: 10023",
         "language": "en",
         "ad_hoc_recognizers":[
             {
                "name": "Zip code Recognizer",
                "supported_language": "en",
                "patterns": [
                    {
                    "name": "zip code (weak)", 
                    "regex": "(\\b\\d{5}(?:\\-\\d{4})?\\b)", 
                    "score": 0.01
                    }
                ],
                "context": ["zip", "code"],
                "supported_entity":"ZIP"
            }
        ]
     }
     """

    response_status, response_content = analyze(request_body)

    expected_response = """
     [
         {"entity_type": "PERSON", "start": 0, "end": 10, "score": 0.85, "analysis_explanation":null},
         {"entity_type": "US_DRIVER_LICENSE", "start": 30, "end": 38, "score": 0.6499999999999999, "analysis_explanation":null},
         {"entity_type": "ZIP", "start": 50, "end": 55, "score": 0.4, "analysis_explanation":null}
     ]
     """
    assert response_status == 200
    assert equal_json_strings(
        expected_response, response_content
    )


@pytest.mark.api
def test_given_ad_hoc_deny_list_recognizer_the_right_entities_are_returned():
    request_body = r"""
    {
        "text": "Mr. John Smith's drivers license is AC432223",
        "language": "en",
        "ad_hoc_recognizers":[
            {
            "name": "Mr. Recognizer",
            "supported_language": "en",
            "deny_list": ["Mr.", "Mister"],
            "supported_entity":"MR_TITLE"
            },
            {
            "name": "Ms. Recognizer",
            "supported_language": "en",
            "deny_list": ["Ms.", "Miss", "Mrs."],
            "supported_entity":"MS_TITLE"
            }
        ]
    }
     """

    response_status, response_content = analyze(request_body)

    expected_response = """
     [
         {"entity_type": "PERSON", "start": 4, "end": 14, "score": 0.85, "analysis_explanation":null},
         {"entity_type": "US_DRIVER_LICENSE", "start": 36, "end": 44, "score": 0.6499999999999999, "analysis_explanation":null},
         {"entity_type": "MR_TITLE", "start": 0, "end": 3, "score": 1.0, "analysis_explanation":null}
     ]
     """
    assert response_status == 200
    assert equal_json_strings(
        expected_response, response_content
    )


@pytest.mark.api
def test_given_allow_list_then_no_entity_is_returned():
    request_body = """
    {
        "text": "email: admin@github.com", 
        "language": "en", 
        "allow_list": ["admin@github.com"]
    }
    """

    response_status, response_content = analyze(request_body)

    expected_response = """
     []
    """
    assert response_status == 200
    assert equal_json_strings(
        expected_response, response_content
    )


@pytest.mark.api
def test_given_allow_list_with_regex_match_then_no_entity_is_returned():
    request_body = """
    {
        "text": "email: admin@github.com", 
        "language": "en", 
        "allow_list": [".*@github.com"],
        "allow_list_match": "regex"
    }
    """

    response_status, response_content = analyze(request_body)

    expected_response = """
     []
    """
    assert response_status == 200
    assert equal_json_strings(
        expected_response, response_content
    )


@pytest.mark.api
def test_given_allow_list_without_setting_allow_list_match_then_normal_entity_is_returned():
    request_body = """
    {
        "text": "email: admin@github.com", 
        "language": "en", 
        "allow_list": [".*@github.com"]
    }
    """

    response_status, response_content = analyze(request_body)

    expected_response = """
     [
         {"entity_type": "EMAIL_ADDRESS", "start": 7, "end": 23, "score": 0.85, "analysis_explanation":null}
     ]
    """
    assert response_status == 200
    assert equal_json_strings(
        expected_response, response_content
    )


@pytest.mark.api
def test_given_regex_flags_and_normal_entities_are_returned():
    # case sensitive flags are turned off, GitHub != github
    request_body = """
    {
        "text": "email: admin@GitHub.com",
        "language": "en", 
        "allow_list": [".*@github.com"],
        "allow_list_match": "regex",
        "regex_flags": 0
    }
    """

    response_status, response_content = analyze(request_body)

    expected_response = """
     [
         {"entity_type": "EMAIL_ADDRESS", "start": 7, "end": 23, "score": 0.85, "analysis_explanation":null}
     ]
    """
    assert response_status == 200
    assert equal_json_strings(
        expected_response, response_content
    )

@pytest.mark.api
def test_given_a_correct_analyze_input_then_return_full_response_batched():
    request_body = """
    {
        "text": [
            "John Smith drivers license is AC432223",
            "John Smith drivers license is AC432223"
        ],
        "language": "en"
    }
    """

    response_status, response_content = analyze(request_body)

    expected_response = """
    [
        [
            {"entity_type": "PERSON", "start": 0, "end": 10, "score": 0.85, "analysis_explanation":null},
            {"entity_type": "US_DRIVER_LICENSE", "start": 30, "end": 38, "score": 0.6499999999999999, "analysis_explanation":null}
        ],
        [
            {"entity_type": "PERSON", "start": 0, "end": 10, "score": 0.85, "analysis_explanation":null},
            {"entity_type": "US_DRIVER_LICENSE", "start": 30, "end": 38, "score": 0.6499999999999999, "analysis_explanation":null}
        ]
    ]
    """
    assert response_status == 200
    assert equal_json_strings(
        expected_response, response_content
    )
