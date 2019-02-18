import abc
import typing

import attr


class EntityWithoutIdentity(TypeError):
    pass


class ValueObjectWithIdentity(TypeError):
    pass


T = typing.TypeVar("T")


class Identity(typing.Generic[T]):
    @classmethod
    def is_identity(cls, field: attr.Attribute) -> None:
        return getattr(field.type, "__origin__", None) == cls


class EntityMeta(abc.ABCMeta):
    def __new__(mcs, name: str, bases: tuple, namespace: dict):
        cls = super().__new__(mcs, name, bases, namespace)
        if name == "Entity":
            return cls
        attr_cls = attr.s(auto_attribs=True)(cls)
        if not any(Identity.is_identity(field) for field in attr.fields(attr_cls)):
            raise EntityWithoutIdentity
        return attr_cls


class Entity(metaclass=EntityMeta):
    pass


class ValueObjectMeta(abc.ABCMeta):
    def __new__(mcs, name: str, bases: tuple, namespace: dict):
        cls = super().__new__(mcs, name, bases, namespace)
        if name == "ValueObject":
            return cls
        attr_cls = attr.s(auto_attribs=True)(cls)
        if any(Identity.is_identity(field) for field in attr.fields(attr_cls)):
            raise ValueObjectWithIdentity
        return attr_cls


class ValueObject(metaclass=ValueObjectMeta):
    pass


EntityOrVo = typing.Union[Entity, ValueObject]
EntityOrVoType = typing.Union[typing.Type[Entity], typing.Type[ValueObject]]
