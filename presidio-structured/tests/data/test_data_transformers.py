import pytest
from pandas import DataFrame
from presidio_structured.config import StructuredAnalysis
from presidio_structured.data.data_processors import (
    DataProcessorBase,
    PandasDataProcessor,
    JsonDataProcessor,
)


class TestDataProcessorBase:
    def test_abstract_init_raises(self, sample_df, tabular_analysis_builder, operators):
        with pytest.raises(TypeError):
            DataProcessorBase()


class TestPandasDataProcessor:
    def test_process(self, sample_df, operators, tabular_analysis):
        processor = PandasDataProcessor()
        result = processor.operate(sample_df, tabular_analysis, operators)
        assert isinstance(result, DataFrame)
        for key in tabular_analysis.entity_mapping:
            if key == "name":
                assert all(result[key] == "PERSON_REPLACEMENT")
            else:
                assert all(result[key] == "DEFAULT_REPLACEMENT")

    def test_process_column_name_not_an_identifier(self, operators):
        # Column names holding PII are often not valid Python identifiers
        # ("Full Name", "e-mail", ...). itertuples renamed those to positional
        # fields, so the name-based getattr lookup raised AttributeError,
        # aborting the run with any later PII columns left unredacted.
        processor = PandasDataProcessor()
        df = DataFrame(
            {
                "Full Name": ["John Doe", "Jane Doe"],
                "email": ["john@example.com", "jane@example.com"],
            }
        )
        analysis = StructuredAnalysis(
            entity_mapping={"Full Name": "PERSON", "email": "EMAIL_ADDRESS"}
        )
        result = processor.operate(df, analysis, operators)
        assert all(result["Full Name"] == "PERSON_REPLACEMENT")
        assert all(result["email"] == "DEFAULT_REPLACEMENT")

    def test_process_no_default_should_raise(self, sample_df, operators_no_default, tabular_analysis):
        processor = PandasDataProcessor()
        with pytest.raises(ValueError):
            processor.operate(sample_df, tabular_analysis, operators_no_default)

    def test_process_invalid_data(self, sample_json, tabular_analysis, operators):
        processor = PandasDataProcessor()
        with pytest.raises(ValueError):
            processor.operate(sample_json, tabular_analysis, operators)


class TestJsonDataProcessor:
    def test_process(self, sample_json, operators, json_analysis):
        processor = JsonDataProcessor()
        result = processor.operate(sample_json, json_analysis, operators)
        assert isinstance(result, dict)
        for key, value in json_analysis.entity_mapping.items():
            keys = key.split(".")
            nested_value = sample_json
            for inner_key in keys:
                nested_value = nested_value[inner_key]
            if value == "PERSON":
                assert nested_value == "PERSON_REPLACEMENT"
            else:
                assert nested_value == "DEFAULT_REPLACEMENT"

    def test_process_no_default_should_raise(self, sample_json, operators_no_default, json_analysis):
        processor = JsonDataProcessor()
        with pytest.raises(ValueError):
            processor.operate(sample_json, json_analysis, operators_no_default)

    def test_process_invalid_data(self, sample_df, json_analysis, operators):
        processor = JsonDataProcessor()
        with pytest.raises(ValueError):
            processor.operate(sample_df, json_analysis, operators)
