from typing import List, Union, Any

from entity_framework.abstract_entity_tree import (
    Visitor,
    FieldNode,
    EntityNode,
    ValueObjectNode,
    ListOfEntitiesNode,
    ListOfValueObjectsNode,
)
from entity_framework.entity import EntityOrVo
from entity_framework.storages.sqlalchemy.registry import SaRegistry


class ModelPopulatingVisitor(Visitor):
    EMPTY_PREFIX = ""

    def __init__(self, aggregate: EntityOrVo, registry: SaRegistry) -> None:
        self._aggregate = aggregate
        self._registry = registry
        self._complex_objects_stack: List[EntityOrVo] = []
        self._entities_stack: List[EntityNode] = []
        self._ef_objects_stack: List[Union[EntityNode, ValueObjectNode]] = []
        self._models_dicts_stack: List[dict] = []
        self._result: Any = None
        self._stacked_vo: List[ValueObjectNode] = []

    @property
    def _prefix(self) -> str:
        if not self._stacked_vo:
            return self.EMPTY_PREFIX
        return "_".join(vo.name for vo in self._stacked_vo) + "_"

    @property
    def result(self) -> Any:
        return self._result

    def visit_field(self, field: FieldNode) -> None:
        if isinstance(self._ef_objects_stack[-1], EntityNode):
            field_name = field.name
        else:
            field_name = f"{self._prefix}{field.name}"

        if self._complex_objects_stack[-1]:  # may be none if optional
            self._models_dicts_stack[-1][field_name] = getattr(self._complex_objects_stack[-1], field.name)

    def visit_entity(self, entity: EntityNode) -> None:
        self._entities_stack.append(entity)
        self._stack_complex_object(entity)
        self._models_dicts_stack.append({})

    def leave_entity(self, entity: EntityNode) -> None:
        self._entities_stack.pop()
        self._construct_model(entity)
        self._complex_objects_stack.pop()

    def visit_value_object(self, value_object: ValueObjectNode) -> None:
        self._stacked_vo.append(value_object)
        self._stack_complex_object(value_object)

    def leave_value_object(self, value_object: ValueObjectNode) -> None:
        self._stacked_vo.pop()
        self._complex_objects_stack.pop()

    def _stack_complex_object(self, vo_or_entity: Union[ValueObjectNode, EntityNode]) -> None:
        self._ef_objects_stack.append(vo_or_entity)
        if not self._complex_objects_stack:
            self._complex_objects_stack.append(self._aggregate)
        else:
            current = self._complex_objects_stack[-1]
            if current is None:
                another = None
            else:
                another = getattr(current, vo_or_entity.name)

            self._complex_objects_stack.append(another)

    def _construct_model(self, entity: EntityNode) -> None:
        self._ef_objects_stack.pop()
        entity_dict = self._models_dicts_stack.pop()
        if entity.optional and entity_dict and all(v is None for v in entity_dict.values()):
            # One is not able to tell the difference between optional object with all its fields = None or
            # an absence of entire vo_or_entity
            instance = None
        else:
            model_cls = self._registry.entities_models[entity.type]
            instance = model_cls(**entity_dict)
        if self._models_dicts_stack:
            self._models_dicts_stack[-1][entity.name] = instance
        else:
            self._result = instance

    def visit_list_of_entities(self, list_of_entities: ListOfEntitiesNode) -> None:
        raise NotImplementedError

    def leave_list_of_entities(self, list_of_entities: ListOfEntitiesNode) -> None:
        raise NotImplementedError

    def visit_list_of_value_objects(self, list_of_value_objects: ListOfValueObjectsNode) -> None:
        raise NotImplementedError

    def leave_list_of_value_objects(self, list_of_value_objects: ListOfValueObjectsNode) -> None:
        raise NotImplementedError
