"""Test the analysis builder"""

import pandas as pd
import pytest

from presidio_analyzer import AnalyzerEngine

from presidio_structured import JsonAnalysisBuilder, PandasAnalysisBuilder

# NOTE: we won't go into depth unit-testing all analyzers, as that is covered in the presidio-analyzer tests


def test_generate_analysis_tabular(tabular_analysis_builder, sample_df):
    structured_analysis = tabular_analysis_builder.generate_analysis(sample_df)

    assert structured_analysis.entity_mapping["name"] == "PERSON"
    assert structured_analysis.entity_mapping["email"] == "EMAIL_ADDRESS"
    assert structured_analysis.entity_mapping["phone"] == "PHONE_NUMBER"


def test_generate_analysis_tabular_with_sampling(tabular_analysis_builder, sample_df):
    structured_analysis = tabular_analysis_builder.generate_analysis(sample_df, n=2)

    assert len(structured_analysis.entity_mapping) == 3
    assert structured_analysis.entity_mapping["name"] == "PERSON"
    assert structured_analysis.entity_mapping["email"] == "EMAIL_ADDRESS"
    assert structured_analysis.entity_mapping["phone"] == "PHONE_NUMBER"


def test_generate_analysis_tabular_with_invalid_sampling(tabular_analysis_builder, sample_df):
    with pytest.raises(ValueError):
        tabular_analysis_builder.generate_analysis(sample_df, n=-1)


def test_generate_analysis_tabular_default_strategy_detects_email_address(
    tabular_analysis_builder, sample_df_strategy
):
    # Regression test for #1316: with the default strategy, a column of email
    # addresses was misidentified as URL, because the confidence-blind
    # most_common vote let six URL detections at 0.5 beat three EMAIL_ADDRESS
    # detections at 1.0. The default mixed strategy must prefer the confident
    # detection.
    structured_analysis = tabular_analysis_builder.generate_analysis(
        sample_df_strategy
    )

    assert structured_analysis.entity_mapping["name"] == "PERSON"
    assert structured_analysis.entity_mapping["email"] == "EMAIL_ADDRESS"
    assert structured_analysis.entity_mapping["city"] == "LOCATION"


def test_find_most_common_entity(tabular_analysis_builder, sample_df_strategy):
    key_recognizer_result_map = tabular_analysis_builder._generate_key_rec_results_map(
        sample_df_strategy, "en", selection_strategy="most_common"
    )
    assert len(key_recognizer_result_map) == 5
    assert key_recognizer_result_map["name"].entity_type == "PERSON"
    assert key_recognizer_result_map["email"].entity_type == "URL"
    assert key_recognizer_result_map["city"].entity_type == "LOCATION"
    assert key_recognizer_result_map["non_pii"].entity_type == "NON_PII"


def test_find_highest_confidence_entity(tabular_analysis_builder, sample_df_strategy):
    key_recognizer_result_map = tabular_analysis_builder._generate_key_rec_results_map(
        sample_df_strategy, "en", selection_strategy="highest_confidence"
    )
    assert len(key_recognizer_result_map) == 5
    assert key_recognizer_result_map["name"].entity_type == "PERSON"
    assert key_recognizer_result_map["email"].entity_type == "EMAIL_ADDRESS"
    assert key_recognizer_result_map["city"].entity_type == "LOCATION"
    assert key_recognizer_result_map["non_pii"].entity_type == "NON_PII"


def test_find_mixed_strategy_entity(tabular_analysis_builder, sample_df_strategy):
    key_recognizer_result_map = tabular_analysis_builder._generate_key_rec_results_map(
        sample_df_strategy, "en", selection_strategy="mixed"
    )
    assert len(key_recognizer_result_map) == 5
    assert key_recognizer_result_map["name"].entity_type == "PERSON"
    assert key_recognizer_result_map["email"].entity_type == "EMAIL_ADDRESS"
    assert key_recognizer_result_map["city"].entity_type == "LOCATION"
    assert key_recognizer_result_map["non_pii"].entity_type == "NON_PII"


def test_find_mixed_strategy_entity_with_custom_mixed_strategy_threshold(tabular_analysis_builder, sample_df):
    key_recognizer_result_map = tabular_analysis_builder._generate_key_rec_results_map(
        sample_df, "en", selection_strategy="mixed", mixed_strategy_threshold=0.4
    )
    assert len(key_recognizer_result_map) == 3
    assert key_recognizer_result_map["name"].entity_type == "PERSON"
    assert key_recognizer_result_map["email"].entity_type == "EMAIL_ADDRESS"
    assert key_recognizer_result_map["phone"].entity_type == "PHONE_NUMBER"


def test_find_entity_with_invalid_strategy_raises_exception(tabular_analysis_builder, sample_df_strategy):
    selection_strategy = "invalid"
    with pytest.raises(ValueError) as excinfo:
        key_recognizer_result_map = tabular_analysis_builder._generate_key_rec_results_map(
            sample_df_strategy, "en", selection_strategy=selection_strategy
        )

    assert f"Unsupported entity selection strategy: {selection_strategy}." in str(excinfo.value)


def test_find_most_common_entity_with_empty_df(tabular_analysis_builder):
    df = pd.DataFrame()
    key_recognizer_result_map = tabular_analysis_builder._generate_key_rec_results_map(df, "en")

    assert len(key_recognizer_result_map) == 0


def test_analysis_tabular_when_default_threshold_is_half_then_phone_does_not_pass(
    sample_df,
):
    analyzer_engine = AnalyzerEngine(default_score_threshold=0.5)
    tabular_analysis_builder = PandasAnalysisBuilder(analyzer_engine)
    structured_analysis = tabular_analysis_builder.generate_analysis(sample_df)

    assert len(structured_analysis.entity_mapping) == 2


def test_analysis_tabular_when_default_threshold_is_zero_then_all_results_pass(
    sample_df,
):
    analyzer_engine = AnalyzerEngine(default_score_threshold=0)
    tabular_analysis_builder = PandasAnalysisBuilder(analyzer_engine)
    structured_analysis = tabular_analysis_builder.generate_analysis(sample_df)

    assert len(structured_analysis.entity_mapping) == 3


def test_analysis_tabular_when_multiprocess_then_results_are_correct(
    sample_df,
):
    analyzer_engine = AnalyzerEngine(default_score_threshold=0)
    tabular_analysis_builder = PandasAnalysisBuilder(analyzer_engine,
                                                     n_process=4,
                                                     batch_size=2)
    structured_analysis = tabular_analysis_builder.generate_analysis(sample_df)

    assert len(structured_analysis.entity_mapping) == 3



def test_generate_analysis_json(json_analysis_builder, sample_json):
    structured_analysis = json_analysis_builder.generate_analysis(sample_json)

    assert structured_analysis.entity_mapping["name"] == "PERSON"
    assert structured_analysis.entity_mapping["address.city"] == "LOCATION"


def test_generate_analysis_json_with_list_should_raise(json_analysis_builder, sample_json_with_array):
    # this feature is not supported by the BatchAnalyzerEngine used in the JsonAnalysisBuilder
    with pytest.raises(ValueError):
        json_analysis_builder.generate_analysis(sample_json_with_array)


def test_generate_analysis_json_with_empty_data(json_analysis_builder):
    data = {}
    structured_analysis = json_analysis_builder.generate_analysis(data)

    assert len(structured_analysis.entity_mapping) == 0


def test_analysis_json_when_default_threshold_is_high_then_only_email_passes(
    sample_json,
):
    analyzer_engine = AnalyzerEngine(default_score_threshold=0.9, log_decision_process=True)
    json_analysis_builder = JsonAnalysisBuilder(analyzer_engine)
    structured_analysis = json_analysis_builder.generate_analysis(sample_json)

    assert len(structured_analysis.entity_mapping) == 1
