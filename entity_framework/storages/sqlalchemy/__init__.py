import typing
from collections import defaultdict

import attr
import inflection
from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import Session, Query, joinedload, relationship
from sqlalchemy.ext.declarative import DeclarativeMeta

from entity_framework.entity import Entity, ValueObject
from entity_framework.abstract_entity_tree import (
    AbstractEntityTree,
    Visitor,
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

    def append_relationship(self, name: str, related_model_name: str, nullable: bool) -> None:
        self.namespace[name] = relationship(related_model_name, innerjoin=not nullable)

    def materialize(self) -> typing.Type:
        return type(self.name, self.bases, self.namespace)


class Registry:
    entities_models: typing.Dict[typing.Type[Entity], typing.Type[DeclarativeMeta]] = {}


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
        if entity.type in self._entities_raw_models:
            raise NotImplementedError("Probably recursive, not supported")

        model_name = f"{entity.type.__name__}Model"
        table_name = inflection.pluralize(inflection.underscore(entity.type.__name__))

        if self._entities_stack:  # nested, include foreign key
            identity_nodes: typing.List[FieldNode] = [
                node for node in entity.children if getattr(node, 'is_identity', None)
            ]
            assert len(identity_nodes) == 1, 'Multiple primary keys not supported'
            identity_node = identity_nodes.pop()
            raw_model: RawModel = self._entities_raw_models[self.current_entity.type]
            raw_model.append_column(
                f"{entity.name}_{identity_node.name}",
                Column(
                    native_type_to_column.convert(identity_node.type),
                    ForeignKey(f"{table_name}.{identity_node.name}"),
                    nullable=entity.nullable
                )
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
            raise Exception('No root model')

        return Query(self._root_model).options(
            joinedload(getattr(self._root_model, rel_name))
            for rel_name in self._models_to_join[self._root_model]
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


class SqlAlchemyRepo:
    base: DeclarativeMeta = None
    _classes_to_models: typing.Dict[EntityOrVoType, typing.Type]

    def __init__(self, session: Session) -> None:
        self._session = session

    @classmethod
    def prepare(cls, entity_cls: typing.Type[EntityType]) -> None:
        assert cls.base, "Must set cls base to an instance of DeclarativeMeta!"
        if not getattr(cls, 'entity', None):
            cls.entity = entity_cls
            cls._abstract_entity_tree_to_model(entity_cls)

    @classmethod
    def _abstract_entity_tree_to_model(cls, entity_cls: typing.Type[EntityType]) -> None:
        aet: AbstractEntityTree = type(cls).entities_to_aets[entity_cls]
        ModelBuildingVisitor(cls.base).traverse_from(aet.root)

    # TODO: sqlalchemy class could have an utility for creating IDS
    # Or it could be put into a separate utility function that would accept repo, then would get descendant classes
    # and got the new id.

    def get(self, identity: IdentityType) -> EntityType:
        # TODO: memoize query
        aet: AbstractEntityTree = type(self.__class__).entities_to_aets[self.entity]
        visitor = QueryBuildingVisitor()
        visitor.traverse_from(aet.root)

        result = visitor.query.with_session(self._session).one()
        import pdb;pdb.set_trace()
        return

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
