from typing import Dict, List, Type, Optional

import inflection
from sqlalchemy import Column, ForeignKey
from sqlalchemy.ext.declarative import DeclarativeMeta

from entity_framework.abstract_entity_tree import (
    Visitor,
    EntityNode,
    ValueObjectNode,
    FieldNode,
    ListOfEntitiesNode,
    ListOfValueObjectsNode,
)
from entity_framework.entity import Entity
from entity_framework.storages.sqlalchemy import native_type_to_column
from entity_framework.storages.sqlalchemy.registry import SaRegistry
from entity_framework.storages.sqlalchemy.constructing_model.raw_model import RawModel


class ModelConstructingVisitor(Visitor):
    EMPTY_PREFIX = ""

    def __init__(self, base: DeclarativeMeta, registry: SaRegistry) -> None:
        self._base = base
        self._registry = registry
        self._entities_stack: List[EntityNode] = []
        self._entities_raw_models: Dict[Type[Entity], RawModel] = {}
        self._prefix = self.EMPTY_PREFIX
        self._last_optional_vo_node: Optional[ValueObjectNode] = None

    @property
    def current_entity(self) -> EntityNode:
        return self._entities_stack[-1]

    def visit_field(self, field: FieldNode) -> None:
        kwargs = {"primary_key": field.is_identity, "nullable": field.optional or self._last_optional_vo_node}
        raw_model: RawModel = self._entities_raw_models[self.current_entity.type]
        raw_model.append_column(
            f"{self._prefix}{field.name}", Column(native_type_to_column.convert(field.type), **kwargs)
        )

    def visit_entity(self, entity: EntityNode) -> None:
        if entity.type in self._entities_raw_models:
            raise NotImplementedError("Probably recursive, not supported")

        model_name = f"{entity.type.__name__}Model"
        table_name = inflection.pluralize(inflection.underscore(entity.type.__name__))

        if self._entities_stack:  # nested, include foreign key
            identity_nodes: typing.List[FieldNode] = [
                node for node in entity.children if getattr(node, "is_identity", None)
            ]
            assert len(identity_nodes) == 1, "Multiple primary keys not supported"
            identity_node = identity_nodes.pop()
            raw_model: RawModel = self._entities_raw_models[self.current_entity.type]
            raw_model.append_column(
                f"{entity.name}_{identity_node.name}",
                Column(
                    native_type_to_column.convert(identity_node.type),
                    ForeignKey(f"{table_name}.{identity_node.name}"),
                    nullable=entity.optional,
                ),
            )
            raw_model.append_relationship(entity.name, model_name, entity.optional)

        self._entities_stack.append(entity)
        self._entities_raw_models[entity.type] = RawModel(
            name=model_name, bases=(self._base,), namespace={"__tablename__": table_name}
        )

    def leave_entity(self, entity: EntityNode) -> None:
        entity_node = self._entities_stack.pop()
        raw_model: RawModel = self._entities_raw_models[entity_node.type]
        self._registry.entities_models[entity.type] = raw_model.materialize()

    def visit_value_object(self, value_object: ValueObjectNode) -> None:
        # value objects' fields are embedded into entity above it
        self._prefix = f"{value_object.name}_"
        if not self._last_optional_vo_node and value_object.optional:
            self._last_optional_vo_node = value_object

    def leave_value_object(self, value_object: ValueObjectNode) -> None:
        self._prefix = self.EMPTY_PREFIX
        if self._last_optional_vo_node == value_object:
            self._last_optional_vo_node = None

    def visit_list_of_entities(self, list_of_entities: ListOfEntitiesNode) -> None:
        raise NotImplementedError

    def leave_list_of_entities(self, list_of_entities: ListOfEntitiesNode) -> None:
        raise NotImplementedError

    def visit_list_of_value_objects(self, list_of_entities: ListOfValueObjectsNode) -> None:
        raise NotImplementedError

    def leave_list_of_value_objects(self, list_of_entities: ListOfValueObjectsNode) -> None:
        raise NotImplementedError
