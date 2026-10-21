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

    def test_process_array_of_records_masks_each_record(self):
        # Every element of a list crossed by the path is a separate leaf, so each
        # record keeps the value derived from its own text instead of all of them
        # receiving the one computed for the last record. A text-sensitive operator
        # is needed to see the difference: a constant replacement looks the same
        # either way.
        processor = JsonDataProcessor()
        operators = {
            "PERSON": OperatorConfig(
                "mask", {"masking_char": "#", "chars_to_mask": 5, "from_end": False}
            )
        }
        data = {
            "users": [
                {"id": 1, "name": "John Doe"},
                {"id": 2, "name": "Jane Smith"},
            ]
        }
        analysis = StructuredAnalysis(entity_mapping={"users.name": "PERSON"})
        result = processor.operate(data, analysis, operators)

        assert [user["name"] for user in result["users"]] == [
            "#####Doe",
            "#####Smith",
        ]
        assert [user["id"] for user in result["users"]] == [1, 2]

    def test_process_array_of_scalars_keeps_every_element(self, operators):
        # The list itself is the value at the path: it must stay a list of the
        # same length, with each element replaced on its own.
        processor = JsonDataProcessor()
        data = {
            "contact": {"emails": ["a@example.com", "b@example.com", "c@example.com"]}
        }
        analysis = StructuredAnalysis(
            entity_mapping={"contact.emails": "EMAIL_ADDRESS"}
        )
        result = processor.operate(data, analysis, operators)

        assert result["contact"]["emails"] == [
            "DEFAULT_REPLACEMENT",
            "DEFAULT_REPLACEMENT",
            "DEFAULT_REPLACEMENT",
        ]

    def test_process_explicit_index_masks_only_that_element(
        self, sample_json_with_array, operators
    ):
        # A numeric segment addresses one element. It must not create a "1" key
        # inside the sibling records, and those siblings must keep their text.
        processor = JsonDataProcessor()
        analysis = StructuredAnalysis(entity_mapping={"users.1.name": "PERSON"})
        result = processor.operate(sample_json_with_array, analysis, operators)

        assert result["users"][0] == {"id": 1, "name": "John Doe"}
        assert result["users"][1] == {"id": 2, "name": "PERSON_REPLACEMENT"}

    def test_process_nested_array_of_arrays(self, operators):
        # Two list levels in a row: the inner list survives as a list, so the
        # surrounding structure is not flattened or turned into a concatenation.
        processor = JsonDataProcessor()
        data = {"org": {"teams": [{"members": ["John Doe", "Jane Doe"]}]}}
        analysis = StructuredAnalysis(entity_mapping={"org.teams.members": "PERSON"})
        result = processor.operate(data, analysis, operators)

        assert result["org"]["teams"][0]["members"] == [
            "PERSON_REPLACEMENT",
            "PERSON_REPLACEMENT",
        ]
