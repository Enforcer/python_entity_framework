import enum
import typing
import uuid
from datetime import date

import attr
import inflection
from sqlalchemy import Column, Date, Integer, String, Enum
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects import postgresql as postgresql_dialect

# TODO: add __all__
# from entity_framework.entity import Entity, Identity, ValueObject
# from entity_framework.repository import Repository, Registry


def create_model_cls(base: declarative_base, entity_cls: typing.Type):
    model_name = f"{entity_cls.__name__}Model"
    bases = (base,)
    cls_dict = {}
    for field in attr.fields(entity_cls):
        result = _field_to_column(field)
        cls_dict.update(result)

    cls_dict["__tablename__"] = inflection.pluralize(inflection.underscore(entity_cls.__name__))

    return type(model_name, bases, cls_dict)


def _field_to_column(field: attr.Attribute, nested=False) -> typing.Dict[str, Column]:
    # TODO: get rid of nested -> omfg, dirty hack for the sake of 'presentation'
    # TODO: support relation (I guess)
    # TODO: strip underscores from start
    field_type = field.type
    kwargs = {"nullable": False}

    if hasattr(field_type, "__origin__"):
        if getattr(field_type, "__origin__") == typing.Union:
            type_one, type_two = field_type.__args__
            if (type_one is type(None)) != (type_two is type(None)):
                kwargs["nullable"] = True
                if type_one is type(None):
                    field_type = type_two
                else:
                    field_type = type_one
            else:
                raise Exception(f"Not supported union of {type_one}, {type_two}!")
        elif getattr(field_type, "__origin__") == Identity:
            field_type, = field_type.__args__
            kwargs["primary_key"] = True

    if field.default != attr.NOTHING:
        kwargs["server_default"] = str(field.default)  # LAME

    if nested:
        kwargs["nullable"] = True

    if issubclass(field_type, Entity):
        # TODO: support nested structures
        prefix = inflection.underscore(field_type.__name__)
        return {
            f"{prefix}_{nested_field.name}": _field_to_column(nested_field, True)[nested_field.name]
            for nested_field in attr.fields(field_type)
        }

    if field_type == uuid.UUID:
        column = Column(postgresql_dialect.UUID, **kwargs)
    elif field_type == int:
        column = Column(Integer, **kwargs)
    elif field_type == str:
        column = Column(String(255), **kwargs)
    elif field_type == date:
        column = Column(Date)
    elif issubclass(field_type, enum.Enum):
        column = Column(Enum(field.type, name=f"{field.name}_enum"), **kwargs)
    else:
        raise Exception(f"Unsupported type {field_type}")

    return {field.name: column}


# Mixins? Get/Save?


class BaseRepo:
    model = None
    entity = None  # rather should be postfixed cls or sth

    def __init__(self, session: Session) -> None:
        self.session = session
        self._fetched_models = []  # just to keep models' objects alive! Session's identity_map is a WeakValueDictionary

    def get(self, pk: typing.Type) -> None:  # todo - generics...
        if isinstance(pk, uuid.UUID):
            pk = str(pk)
        model = self.session.query(self.model).get(pk)
        instance_dict = {}

        def get_field_value_from_model(model, field, field_name):
            field_type = field.type
            if getattr(field_type, "__origin__", None) == Identity:
                field_type, = field_type.__args__

            value = getattr(model, field_name)
            if value is None:
                return value
            if field_type == uuid.UUID:
                value = uuid.UUID(value)
            return value

        for field_name, field in attr.fields_dict(self.entity).items():
            if hasattr(field.type, "__args__") and issubclass(field.type.__args__[0], Entity):
                # TODO: does not support not nullable nested...
                sub_entity_cls = field.type.__args__[0]
                prefix = inflection.underscore(sub_entity_cls.__name__)
                sub_entity_fields_dict = attr.fields_dict(sub_entity_cls)
                model_field_names_nested_fields_names = [
                    (f"{prefix}_{nested_field_name}", nested_field_name) for nested_field_name in sub_entity_fields_dict
                ]
                sub_entity_dict = {
                    nested_field_name: get_field_value_from_model(
                        model, sub_entity_fields_dict[nested_field_name], model_field_name
                    )
                    for model_field_name, nested_field_name in model_field_names_nested_fields_names
                }
                if all([v is None for v in sub_entity_dict.values()]):
                    instance_dict[field_name] = None
                else:
                    instance_dict[field_name] = sub_entity_cls(**sub_entity_dict)
            else:
                instance_dict[field_name] = get_field_value_from_model(model, field, field_name)

        self._fetched_models.append(model)
        return self.entity(**instance_dict)

    def save(self, entity) -> None:  # todo - generics...
        fields_dict = {field.name: field for field in attr.fields(self.entity)}

        nested_dict_repr = attr.asdict(entity)
        flattened_dict_repr = {}
        for field_name, field in nested_dict_repr.items():
            # if a sub-entity is nullable, then all its fields has to be nullable :D
            nullable_sub_entity = getattr(
                fields_dict[field_name].type, "__origin__", None
            ) == typing.Union and issubclass(fields_dict[field_name].type.__args__[0], Entity)
            if field is None and nullable_sub_entity:  # still, do it nicer maybe
                continue

            if not isinstance(field, dict):
                flattened_dict_repr[field_name] = field
            else:
                flattened_dict_repr.update(
                    {
                        f"{field_name}_{nested_field_name}": nested_field
                        for nested_field_name, nested_field in field.items()
                    }
                )

        flattened_dict_repr = {k: v if not isinstance(v, uuid.UUID) else str(v) for k, v in flattened_dict_repr.items()}
        identity_key = self.model, (str(entity.id),), None
        if identity_key in self.session.identity_map:
            old_model = self.session.identity_map[identity_key]
            for field, value in flattened_dict_repr.items():
                setattr(old_model, field, value)
        else:
            self.session.merge(self.model(**flattened_dict_repr))
        self.session.flush()


def create_repo(base: declarative_base, entity_cls: typing.Type, entity_pk_type: typing.Type) -> typing.Type[BaseRepo]:
    model_cls = create_model_cls(base, entity_cls)
    return type(f"{model_cls.__name__}Repo", (BaseRepo,), {"model": model_cls, "entity": entity_cls})


def create_declarative_repo_base(
    base: declarative_base
) -> typing.Dict[typing.Tuple[typing.Type, typing.Type], typing.Type[BaseRepo]]:
    class declarative_repo_base(dict):
        def __missing__(self, entity_cls_pk: typing.Tuple[typing.Type, typing.Type]) -> typing.Type[BaseRepo]:
            entity_cls, pk_type = entity_cls_pk
            return create_repo(base, entity_cls, pk_type)

    return declarative_repo_base()


# TODO: what to do with SQLAlchemy's UoW? Wrap it, trick it (ouch), ignore it?
# Maybe one could alter entities to become PROXY OBJECTS for models, so that one
# does not have to update all fields at once neither use merge with load=True
# PoC done: data is copied to entity inside identity map, but one has to keep around another reference to the entity
# or Garbage Collector deletes it.

# TODO: support custom Value Objects, map them onto columns in DB back and forth. Single-dispatch?

# TODO: Value objects will still have to have IDs in underlying DB, does not matter if it is PostgreSQL or MongoDB
