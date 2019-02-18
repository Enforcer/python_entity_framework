import typing

import attr
import inflection
from sqlalchemy import Column
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import DeclarativeMeta

from entity_framework.entity import Entity, ValueObject
from entity_framework.abstract_entity_tree import (
    AbstractEntityTree,
    _is_nullable_entity_or_vo,
    _get_wrapped_type,
    _is_list_of_entities_or_vos,
    _is_generic,
)
from entity_framework.repository import EntityType, IdentityType
from entity_framework.storages.sqlalchemy import native_type_to_column, types


class SqlAlchemyRepo:
    base: DeclarativeMeta = None

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
        model_cls_name = f"{entity_cls.__name__}Model"
        model_bases = (cls.base,)
        namespace = {"__tablename__": table_name}
        for field_name, field_type in aet.fields.items():
            kwargs = {}
            if field_name in aet.identity:
                kwargs["primary_key"] = True
            else:
                kwargs["nullable"] = field_name in aet.nullables
            namespace[field_name] = Column(native_type_to_column.convert(field_type), **kwargs)

        # if aet.nested_lists:
        #     import pdb;pdb.set_trace()
        #     raise Exception('Nested lists are not (YET) supported')

        for nested_list_name, nested_list_item_type in aet.nested_lists.items():
            if issubclass(nested_list_item_type, Entity):
                pass
            elif issubclass(nested_list_item_type, ValueObject):
                # TODO: attach 'virtual' identities, keep mapping under repository using Weak Dictionary
                pass
            else:
                raise Exception(f"Unsupported type on nested list - {nested_list_item_type}")

        return type(model_cls_name, model_bases, namespace)

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
