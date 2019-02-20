import operator
import typing
from collections import defaultdict

import attr
import inflection
from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import Session, Query, joinedload, relationship
from sqlalchemy.ext.declarative import DeclarativeMeta

from entity_framework.entity import Entity, ValueObject
from entity_framework.abstract_entity_tree import (
    Visitor,
    FieldNode,
    EntityNode,
    ValueObjectNode,
    ListOfEntitiesNode,
    ListOfValueObjectsNode,
)
from entity_framework.storages.sqlalchemy import native_type_to_column


class Registry:
    entities_models: typing.Dict[typing.Type[Entity], typing.Type[DeclarativeMeta]] = {}


@attr.s(auto_attribs=True)
class RawModel:
    name: str
    bases: typing.Tuple[typing.Type, ...]
    namespace: typing.Dict

    def append_column(self, name: str, column: Column) -> None:
        self.namespace[name] = column

    def append_relationship(self, name: str, related_model_name: str, nullable: bool) -> None:
        self.namespace[name] = relationship(related_model_name, innerjoin=not nullable)

    def materialize(self) -> typing.Type:
        return type(self.name, self.bases, self.namespace)


class ModelBuildingVisitor(Visitor):
    EMPTY_PREFIX = ""

    def __init__(self, base: DeclarativeMeta) -> None:
        self._base = base
        self._entities_stack: typing.List[EntityNode] = []
        self._entities_raw_models: typing.Dict[typing.Type[Entity], RawModel] = {}
        self._prefix = self.EMPTY_PREFIX
        self._last_nullable_vo_node: typing.Optional[ValueObjectNode] = None

    @property
    def current_entity(self) -> EntityNode:
        return self._entities_stack[-1]

    def visit_field(self, field: "FieldNode") -> None:
        kwargs = {"primary_key": field.is_identity, "nullable": field.nullable or self._last_nullable_vo_node}
        raw_model: RawModel = self._entities_raw_models[self.current_entity.type]
        raw_model.append_column(
            f"{self._prefix}{field.name}", Column(native_type_to_column.convert(field.type), **kwargs)
        )

    def visit_entity(self, entity: "EntityNode") -> None:
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
                    nullable=entity.nullable,
                ),
            )
            raw_model.append_relationship(entity.name, model_name, entity.nullable)

        self._entities_stack.append(entity)
        self._entities_raw_models[entity.type] = RawModel(
            name=model_name, bases=(self._base,), namespace={"__tablename__": table_name}
        )

    def leave_entity(self, entity: "EntityNode") -> None:
        entity_node = self._entities_stack.pop()
        raw_model: RawModel = self._entities_raw_models[entity_node.type]
        Registry.entities_models[entity.type] = raw_model.materialize()

    def visit_value_object(self, value_object: "ValueObjectNode") -> None:
        # value objects' fields are embedded into entity above it
        self._prefix = f"{value_object.name}_"
        if not self._last_nullable_vo_node and value_object.nullable:
            self._last_nullable_vo_node = value_object

    def leave_value_object(self, value_object: "ValueObjectNode") -> None:
        self._prefix = self.EMPTY_PREFIX
        if self._last_nullable_vo_node == value_object:
            self._last_nullable_vo_node = None

    def visit_list_of_entities(self, list_of_entities: "ListOfEntitiesNode") -> None:
        raise NotImplementedError

    def leave_list_of_entities(self, list_of_entities: "ListOfEntitiesNode") -> None:
        raise NotImplementedError

    def visit_list_of_value_objects(self, list_of_entities: "ListOfValueObjectsNode") -> None:
        raise NotImplementedError

    def leave_list_of_value_objects(self, list_of_entities: "ListOfValueObjectsNode") -> None:
        raise NotImplementedError


class QueryBuildingVisitor(Visitor):
    def __init__(self) -> None:
        self._root_model: typing.Optional[typing.Type] = None
        self._models_stack: typing.List[typing.Type] = []
        self._models_to_join: typing.DefaultDict[typing.Type, typing.List[str]] = defaultdict(list)
        self._all_models: typing.Set[typing.Type] = set()
        self._query: typing.Optional[Query] = None

    @property
    def query(self) -> Query:
        if not self._root_model:
            raise Exception("No root model")

        return Query(self._root_model).options(
            joinedload(getattr(self._root_model, rel_name)) for rel_name in self._models_to_join[self._root_model]
        )

    def visit_entity(self, entity: "EntityNode") -> None:
        # TODO: decide what to do with fields used magically, like entity.name which is really just a node name
        # Should I wrap with sth?
        model = Registry.entities_models[entity.type]
        if not self._root_model:
            self._root_model = model
        elif self._models_stack:
            self._models_to_join[self._models_stack[-1]].append(entity.name)

        self._models_stack.append(model)
        self._all_models.add(model)

    def leave_entity(self, entity: "EntityNode") -> None:
        self._models_stack.pop()


class ConvertingToEntityVisitor(Visitor):
    EMPTY_PREFIX = ""

    def __init__(self, db_result: object) -> None:
        # TODO: this probably won't work with nullable's
        self._db_result = db_result
        self._prefix = self.EMPTY_PREFIX
        self._entities_stack: typing.List[EntityNode] = []
        self._ef_objects_stack: typing.List[typing.Union[EntityNode, ValueObjectNode]] = []
        self._ef_dicts_stack: typing.List[dict] = []
        self._result: typing.Any = None

    @property
    def result(self) -> typing.Any:
        return self._result

    def visit_field(self, field: "FieldNode") -> None:
        if isinstance(self._ef_objects_stack[-1], EntityNode):
            field_name = field.name
        else:
            field_name = f"{self._prefix}{field.name}"

        db_object = self._db_result
        for index, entity in enumerate(self._entities_stack[:-1]):
            next_entity = self._entities_stack[index + 1]
            db_object = getattr(db_object, next_entity.name)

        self._ef_dicts_stack[-1][field.name] = getattr(db_object, field_name)

    def visit_entity(self, entity: "EntityNode") -> None:
        self._entities_stack.append(entity)
        self._stack_complex_object(entity)

    def leave_entity(self, entity: "EntityNode") -> None:
        self._entities_stack.pop()
        self._construct_complex_object(entity)

    def visit_value_object(self, value_object: "ValueObjectNode") -> None:
        self._prefix = f"{value_object.name}_"
        self._stack_complex_object(value_object)

    def leave_value_object(self, value_object: "ValueObjectNode") -> None:
        self._prefix = self.EMPTY_PREFIX
        self._construct_complex_object(value_object)

    def _stack_complex_object(self, vo_or_entity: typing.Union[ValueObjectNode, EntityNode]) -> None:
        self._ef_objects_stack.append(vo_or_entity)
        self._ef_dicts_stack.append({})

    def _construct_complex_object(self, vo_or_entity: typing.Union[ValueObjectNode, EntityNode]) -> None:
        self._ef_objects_stack.pop()
        entity_dict = self._ef_dicts_stack.pop()
        instance = vo_or_entity.type(**entity_dict)
        if self._ef_dicts_stack:
            self._ef_dicts_stack[-1][vo_or_entity.name] = instance
        else:
            self._result = instance

    def visit_list_of_entities(self, list_of_entities: "ListOfEntitiesNode") -> None:
        raise NotImplementedError

    def leave_list_of_entities(self, list_of_entities: "ListOfEntitiesNode") -> None:
        raise NotImplementedError

    def visit_list_of_value_objects(self, list_of_value_objects: "ListOfValueObjectsNode") -> None:
        raise NotImplementedError

    def leave_list_of_value_objects(self, list_of_value_objects: "ListOfValueObjectsNode") -> None:
        raise NotImplementedError
