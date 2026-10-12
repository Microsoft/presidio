import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Union

from pandas import DataFrame
from presidio_anonymizer.entities import OperatorConfig
from presidio_anonymizer.operators import OperatorsFactory, OperatorType

from presidio_structured.config import StructuredAnalysis


class DataProcessorBase(ABC):
    """Abstract class to handle logic of operations over text using the operators."""

    def __init__(self) -> None:
        """Initialize DataProcessorBase object."""
        self.logger = logging.getLogger("presidio-structured")

    def operate(
        self,
        data: Any,
        structured_analysis: StructuredAnalysis,
        operators: Dict[str, OperatorConfig],
    ) -> Any:
        """
        Perform operations over the text using the operators, as per the structured analysis.

        :param data: Data to be operated on.
        :param structured_analysis: Analysis schema as per the structured data.
        :param operators: Dictionary containing operator configuration objects.
        :return: Data after being operated upon.
        """  # noqa: E501
        key_to_operator_mapping = self._generate_operator_mapping(
            structured_analysis, operators
        )
        return self._process(data, key_to_operator_mapping)

    @abstractmethod
    def _process(
        self,
        data: Union[Dict, DataFrame],
        key_to_operator_mapping: Dict[str, Callable],
    ) -> Union[Dict, DataFrame]:
        """
        Abstract method for subclasses to provide operation implementation.

        :param data: Data to be operated on.
        :param key_to_operator_mapping: Mapping of keys to operators.
        :return: Operated data.
        """
        pass

    @staticmethod
    def _create_operator_callable(operator, params):
        def operator_callable(text):
            return operator.operate(params=params, text=text)

        return operator_callable

    def _generate_operator_mapping(
        self, config, operators: Dict[str, OperatorConfig]
    ) -> Dict[str, Callable]:
        """
        Generate a mapping of keys to operator callables.

        :param config: Configuration object containing mapping of entity types to keys.
        :param operators: Dictionary containing operator configuration objects.
        :return: Dictionary mapping keys to operator callables.
        """
        key_to_operator_mapping = {}

        operators_factory = OperatorsFactory()
        for key, entity in config.entity_mapping.items():
            self.logger.debug(f"Creating operator for key {key} and entity {entity}")
            operator_config = operators.get(entity, operators.get("DEFAULT", None))
            if operator_config is None:
                raise ValueError(f"Operator for entity {entity} not found")
            # NOTE: hardcoded OperatorType.Anonymize, as this is the only one supported.
            operator = operators_factory.create_operator_class(
                operator_config.operator_name, OperatorType.Anonymize
            )
            operator_callable = self._create_operator_callable(
                operator, operator_config.params
            )
            key_to_operator_mapping[key] = operator_callable

        return key_to_operator_mapping

    def _operate_on_text(
        self,
        text_to_operate_on: str,
        operator_callable: Callable,
    ) -> str:
        """
        Operates on the provided text using the operator callable.

        :param text_to_operate_on: Text to be operated on.
        :param operator_callable: Callable that performs operation on the text.
        :return: Text after operation.
        """
        return operator_callable(text_to_operate_on)


class PandasDataProcessor(DataProcessorBase):
    """Pandas Data Processor."""

    def _process(
        self, data: DataFrame, key_to_operator_mapping: Dict[str, Callable]
    ) -> DataFrame:
        """
        Operates on the given pandas DataFrame based on the provided operators.

        :param data: DataFrame to be operated on.
        :param key_to_operator_mapping: Mapping of keys to operator callables.
        :return: DataFrame after the operation.
        """

        if not isinstance(data, DataFrame):
            raise ValueError("Data must be a pandas DataFrame")

        for key, operator_callable in key_to_operator_mapping.items():
            self.logger.debug(f"Operating on column {key}")
            for index, text_to_operate_on in data[key].items():
                operated_text = self._operate_on_text(
                    text_to_operate_on, operator_callable
                )
                data.at[index, key] = operated_text
        return data


class JsonDataProcessor(DataProcessorBase):
    """JSON Data Processor, Supports arbitrary nesting of dictionaries and lists."""

    @staticmethod
    def _get_nested_value(data: Union[Dict, List, None], path: List[str]) -> Any:
        """
        Recursively retrieves the value from nested data using a given path.

        :param data: Nested data (list or dictionary).
        :param path: List of keys/indexes representing the path.
        :return: Retrieved value.
        """
        for i, key in enumerate(path):
            if isinstance(data, list):
                if key.isdigit():
                    data = data[int(key)]
                else:
                    return [
                        JsonDataProcessor._get_nested_value(item, path[i:])
                        for item in data
                    ]
            elif isinstance(data, dict):
                data = data.get(key)
            else:
                return data
        return data

    @staticmethod
    def _set_nested_value(data: Union[Dict, List], path: List[str], value: Any) -> None:
        """
        Recursively sets a value in nested data using a given path.

        :param data: Nested data (JSON-like).
        :param path: List of keys/indexes representing the path.
        :param value: Value to be set.
        """
        for i, key in enumerate(path):
            if isinstance(data, list):
                if i + 1 < len(path) and path[i + 1].isdigit():
                    idx = int(path[i + 1])
                    while len(data) <= idx:
                        data.append({})
                    data = data[idx]
                    continue
                else:
                    for item in data:
                        JsonDataProcessor._set_nested_value(item, path[i:], value)
                    return
            elif isinstance(data, dict):
                if i == len(path) - 1:
                    data[key] = value
                else:
                    data = data.setdefault(key, {})

    def _process(
        self,
        data: Union[Dict, List],
        key_to_operator_mapping: Dict[str, Callable],
    ) -> Union[Dict, List]:
        """
        Operates on the given JSON-like data based on the provided configuration.

        :param data: JSON-like data to be operated on.
        :param key_to_operator_mapping: maps keys to Callable operators.
        :return: JSON-like data after the operation.
        """

        if not isinstance(data, (dict, list)):
            raise ValueError("Data must be a JSON-like object")

        for key, operator_callable in key_to_operator_mapping.items():
            self.logger.debug(f"Operating on key {key}")
            keys = key.split(".")
            if isinstance(data, list):
                for item in data:
                    self._process(item, key_to_operator_mapping)
            else:
                text_to_operate_on = self._get_nested_value(data, keys)
                if text_to_operate_on:
                    if isinstance(text_to_operate_on, list):
                        for text in text_to_operate_on:
                            operated_text = self._operate_on_text(
                                text, operator_callable
                            )
                            self._set_nested_value(data, keys, operated_text)
                    else:
                        operated_text = self._operate_on_text(
                            text_to_operate_on, operator_callable
                        )
                        self._set_nested_value(data, keys, operated_text)
        return data
