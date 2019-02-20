import typing

import attr
import inflection
from sqlalchemy import Column
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import DeclarativeMeta

from entity_framework.entity import Entity, ValueObject
from entity_framework.abstract_entity_tree import (
    AbstractEntityTree,
    Visitor,
    Node,
    FieldNode,
    EntityNode,
    ValueObjectNode,
    ListOfEntitiesNode,
    ListOfValueObjectsNode,
    _is_nullable_entity_or_vo,
    _get_wrapped_type,
    _is_list_of_entities_or_vos,
    _is_generic,
)
from entity_framework.repository import EntityType, IdentityType, EntityOrVoType
from entity_framework.storages.sqlalchemy import native_type_to_column, types


@attr.s(auto_attribs=True)
class RawModel:
    name: str
    bases: typing.Tuple[typing.Type, ...]
    namespace: typing.Dict

    def append_column(self, name: str, column: Column) -> None:
        self.namespace[name] = column

    def materialize(self) -> typing.Type:
        return type(self.name, self.bases, self.namespace)


class ModelBuildingVisitor(Visitor):
    EMPTY_PREFIX = ""

    def __init__(self, base: DeclarativeMeta) -> None:
        self._base = base
        self._entities_stack: typing.List[EntityNode] = []
        self._entities_raw_models: typing.Dict[typing.Type[Entity], RawModel] = {}
        self._prefix = self.EMPTY_PREFIX

    @property
    def current_entity(self) -> EntityNode:
        return self._entities_stack[-1]

    def visit_field(self, field: "FieldNode") -> None:
        kwargs = {"primary_key": field.is_identity, "nullable": field.nullable}
        raw_model: RawModel = self._entities_raw_models[self.current_entity.type]
        raw_model.append_column(
            f"{self._prefix}{field.name}", Column(native_type_to_column.convert(field.type), **kwargs)
        )

    def leave_field(self, field: "FieldNode") -> None:
        pass

    def visit_entity(self, entity: "EntityNode") -> None:
        self._entities_stack.append(entity)
        if entity.type in self._entities_raw_models:
            raise NotImplementedError("Probably recursive, not supported")

        table_name = inflection.pluralize(inflection.underscore(entity.type.__name__))
        self._entities_raw_models[entity.type] = RawModel(
            name=f"{entity.type.__name__}Model", bases=(self._base,), namespace={"__tablename__": table_name}
        )

    def leave_entity(self, entity: "EntityNode") -> None:
        entity_node = self._entities_stack.pop()
        raw_model: RawModel = self._entities_raw_models[entity_node.type]
        raw_model.materialize()

    def visit_value_object(self, value_object: "ValueObjectNode") -> None:
        # value objects' fields are embedded into entity above it
        self._prefix = f"{value_object.name}_"

    def leave_value_object(self, value_object: "ValueObjectNode") -> None:
        self._prefix = self.EMPTY_PREFIX

    def visit_list_of_entities(self, list_of_entities: "ListOfEntitiesNode") -> None:
        raise NotImplementedError

    def leave_list_of_entities(self, list_of_entities: "ListOfEntitiesNode") -> None:
        raise NotImplementedError

    def visit_list_of_value_objects(self, list_of_entities: "ListOfValueObjectsNode") -> None:
        raise NotImplementedError

    def leave_list_of_value_objects(self, list_of_entities: "ListOfValueObjectsNode") -> None:
        raise NotImplementedError


class SqlAlchemyRepo:
    base: DeclarativeMeta = None
    _classes_to_models: typing.Dict[EntityOrVoType, typing.Type]

    def __init__(self, session: Session) -> None:
        self._session = session

    @classmethod
    def prepare(cls, entity_cls: typing.Type[EntityType]) -> None:
        assert cls.base, "Must set cls base to an instance of DeclarativeMeta!"
        table_name = inflection.pluralize(inflection.underscore(entity_cls.__name__))
        if table_name not in cls.base.metadata.tables:
            cls.entity = entity_cls
            cls.model = cls._abstract_entity_tree_to_model(entity_cls, table_name)

    @classmethod
    def _abstract_entity_tree_to_model(cls, entity_cls: typing.Type[EntityType], table_name: str):
        aet: AbstractEntityTree = type(cls).entities_to_aets[entity_cls]
        ModelBuildingVisitor(cls.base).traverse_from(aet.root)

    def get(self, identity: IdentityType) -> EntityType:
        model = self._session.query(self.model).get(identity)

        T = typing.TypeVar("T")

        def read_fields_from_model(entity_cls: typing.Type[T], prefix: str = None) -> typing.Optional[T]:
            values = {}
            for field_name, field in attr.fields_dict(entity_cls).items():
                field_type = field.type
                if _is_nullable_entity_or_vo(field):
                    field_type = _get_wrapped_type(field)

                if _is_generic(field) and _is_list_of_entities_or_vos(field):
                    values[field.name] = []
                    continue  # TODO: support lists

                if issubclass(field_type, (Entity, ValueObject)):
                    if prefix:
                        new_prefix = f"{prefix}_{field_name}"
                    else:
                        new_prefix = field_name
                    values[field_name] = read_fields_from_model(field_type, new_prefix)
                else:
                    if prefix:
                        field_name = f"{prefix}_{field_name}"
                    values[field.name] = types.from_storage(getattr(model, field_name), field)

            # TODO: return None if all values are None AND entity is optional (can't know that deeper, must be passed)
            return entity_cls(**values)

        return read_fields_from_model(self.entity)

    def save(self, entity: EntityType) -> None:
        # TODO: consider traversing aet instead of parsing attr.dict
        # TODO: consider writing iterator for AET (VISITOR!!!)
        values = {}

        def flatten_dict(d: dict, prefix: str = "") -> None:
            for key, value in d.items():
                if prefix:
                    key = f"{prefix}_{key}"

                if isinstance(value, dict):
                    flatten_dict(value, f"{key}")
                elif isinstance(value, list):
                    pass  # TODO: support lists
                else:
                    values[key] = types.to_storage(value)

        flatten_dict(attr.asdict(entity))

        self._session.merge(self.model(**values))
        self._session.flush()
