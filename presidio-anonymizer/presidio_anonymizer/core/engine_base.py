"""Handle the entire text operations using the operators."""

import logging
from abc import ABC
from typing import Dict, List

from presidio_anonymizer.core.text_replace_builder import TextReplaceBuilder
from presidio_anonymizer.entities import (
    EngineResult,
    OperatorConfig,
    OperatorResult,
    PIIEntity,
)
from presidio_anonymizer.operators import OperatorsFactory, OperatorType


class EngineBase(ABC):
    """Handle the logic of operations over the text using the operators."""

    def __init__(self):
        self.logger = logging.getLogger("presidio-anonymizer")
        self.operators_factory = OperatorsFactory()

    def _operate(
        self,
        text: str,
        pii_entities: List[PIIEntity],
        operators_metadata: Dict[str, OperatorConfig],
        operator_type: OperatorType,
        **operator_kwargs: Dict,
    ) -> EngineResult:
        """
        Operate will do the operations required by the user over the text.

        :param text: the text we need to operate on.
        :param pii_entities: data about the text entities we want to operate over.
        :param operators_metadata: dictionary where the key is the entity_type and what
        :type operator_type: either anonymize or deanonymize
        we want to perform over this entity_type.
        :param operator_kwargs: Additional keyword arguments to pass to operators
        :return:
        """
        text_replace_builder = TextReplaceBuilder(original_text=text)
        engine_result = EngineResult()
        sorted_pii_entities = sorted(pii_entities, reverse=True)

        for entity in sorted_pii_entities:
            text_to_operate_on = text_replace_builder.get_text_in_position(
                entity.start, entity.end
            )

            self.logger.debug(f"performing operation {entity}")
            operator_metadata = self.__get_entity_operator_metadata(
                entity.entity_type, operators_metadata
            )
            changed_text = self.__operate_on_text(
                entity,
                text_to_operate_on,
                operator_metadata,
                operator_type,
                operator_kwargs,
            )
            index_from_end = text_replace_builder.replace_text_get_insertion_index(
                changed_text, entity.start, entity.end
            )

            # The following creates an intermediate list of result entities,
            # ordered from end to start, and the indexes will be normalized
            # from start to end once the loop ends and the text length is deterministic.
            result_item = OperatorResult(
                0,
                index_from_end,
                entity.entity_type,
                changed_text,
                operator_metadata.operator_name,
                score=getattr(entity, "score", None),
            )
            engine_result.add_item(result_item)

        engine_result.set_text(text_replace_builder.output_text)
        engine_result.normalize_item_indexes()
        return engine_result

    def __operate_on_text(
        self,
        text_metadata: PIIEntity,
        text_to_operate_on: str,
        operator_metadata: OperatorConfig,
        operator_type: OperatorType,
        operator_kwargs: Dict,
    ) -> str:
        entity_type = text_metadata.entity_type
        self.logger.debug(f"getting operator for {entity_type}")
        operator = self.operators_factory.create_operator_class(
            operator_metadata.operator_name, operator_type
        )
        self.logger.debug(f"validating operator {operator} for {entity_type}")

        # Make a copy of params to avoid modifying the original config
        params = operator_metadata.params.copy()
        params["entity_type"] = entity_type

        operator.validate(params=params)

        self.logger.debug(f"operating on {entity_type} with {operator}")
        operated_on_text = operator.operate(params=params, text=text_to_operate_on)

        return operated_on_text

    @staticmethod
    def __get_entity_operator_metadata(
        entity_type: str, operators_metadata: Dict = None
    ) -> OperatorConfig:
        # We try to get the operator from the list by entity_type.
        # If it does not exist, we get the default from the list.
        if operators_metadata is None:
            operators_metadata = {}
        operator = operators_metadata.get(entity_type)
        if operator:
            return operator
        else:
            return operators_metadata.get("DEFAULT")
