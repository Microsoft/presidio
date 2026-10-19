import pytest
from pandas import DataFrame
from presidio_anonymizer.entities import OperatorConfig
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

    def test_process_numeric_column(self, operators):
        # read_csv parses NPI and phone columns as int64. Writing the operated
        # text back into the int64 column raised a TypeError, and mask/hash
        # failed on the int itself.
        processor = PandasDataProcessor()
        df = DataFrame({"npi": [1245319599, 1679576722], "phone": [2124567890, 2134567590]})
        analysis = StructuredAnalysis(entity_mapping={"npi": "US_NPI", "phone": "PHONE_NUMBER"})
        operators = {
            "US_NPI": OperatorConfig("mask", {"masking_char": "*", "chars_to_mask": 6, "from_end": False}),
            "DEFAULT": OperatorConfig("replace", {"new_value": "DEFAULT_REPLACEMENT"}),
        }
        result = processor.operate(df, analysis, operators)
        assert result["npi"].tolist() == ["******9599", "******6722"]
        assert result["phone"].tolist() == ["DEFAULT_REPLACEMENT", "DEFAULT_REPLACEMENT"]

    def test_process_keeps_missing_values(self):
        processor = PandasDataProcessor()
        df = DataFrame({"name": ["John Smith", None, "Jane Doe"]})
        analysis = StructuredAnalysis(entity_mapping={"name": "PERSON"})
        operators = {
            "DEFAULT": OperatorConfig("mask", {"masking_char": "*", "chars_to_mask": 4, "from_end": False}),
        }
        result = processor.operate(df, analysis, operators)
        assert result["name"].isna().tolist() == [False, True, False]
        assert result["name"][0] == "**** Smith"
        assert result["name"][2] == "**** Doe"

    def test_process_duplicated_index(self):
        # Concatenating two extracts without ignore_index repeats index labels.
        # A cell write through .at hit every row with the same label, so rows
        # ended up holding another record's value.
        processor = PandasDataProcessor()
        df = DataFrame(
            {"name": ["John Smith", "Ann Lee", "Jane Doe", "Bob Ray"]},
            index=[0, 1, 0, 1],
        )
        analysis = StructuredAnalysis(entity_mapping={"name": "PERSON"})
        operators = {"DEFAULT": OperatorConfig("custom", {"lambda": lambda text: text.upper()})}
        result = processor.operate(df, analysis, operators)
        assert result["name"].tolist() == ["JOHN SMITH", "ANN LEE", "JANE DOE", "BOB RAY"]

    def test_process_keep_and_custom_receive_original_value(self):
        processor = PandasDataProcessor()
        df = DataFrame({"npi": [1245319599, 1679576722], "zip": [10001, 94105]})
        analysis = StructuredAnalysis(entity_mapping={"npi": "US_NPI", "zip": "ZIP"})
        operators = {
            "US_NPI": OperatorConfig("keep"),
            "DEFAULT": OperatorConfig("custom", {"lambda": lambda value: type(value).__name__}),
        }
        result = processor.operate(df, analysis, operators)
        assert result["npi"].tolist() == [1245319599, 1679576722]
        assert result["npi"].dtype == "int64"
        assert result["zip"].tolist() == ["int", "int"]

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

    def test_process_numeric_value(self):
        processor = JsonDataProcessor()
        data = {"provider": {"name": "John Smith", "npi": 1245319599}}
        analysis = StructuredAnalysis(entity_mapping={"provider.npi": "US_NPI"})
        operators = {
            "DEFAULT": OperatorConfig("mask", {"masking_char": "*", "chars_to_mask": 6, "from_end": False}),
        }
        result = processor.operate(data, analysis, operators)
        assert result == {"provider": {"name": "John Smith", "npi": "******9599"}}

    def test_process_no_default_should_raise(self, sample_json, operators_no_default, json_analysis):
        processor = JsonDataProcessor()
        with pytest.raises(ValueError):
            processor.operate(sample_json, json_analysis, operators_no_default)

    def test_process_invalid_data(self, sample_df, json_analysis, operators):
        processor = JsonDataProcessor()
        with pytest.raises(ValueError):
            processor.operate(sample_df, json_analysis, operators)
