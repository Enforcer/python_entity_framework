import abc
import inspect
import typing

from entity_framework.abstract_entity_tree import AbstractEntityTree, build
from entity_framework.entity import EntityOrVoType


EntityType = typing.TypeVar("EntityType")
IdentityType = typing.TypeVar("IdentityType")


class RepositoryMeta(typing.GenericMeta):
    entities_to_aets: typing.Dict[EntityOrVoType, AbstractEntityTree] = {}

    def __new__(
        mcs,
        name: str,
        bases: typing.Tuple[typing.Type, ...],
        namespace: dict,
        tvars=None,
        args=None,
        origin=None,
        extra=None,
        orig_bases=None,
    ) -> typing.Type:
        cls = super().__new__(
            mcs, name, bases, namespace, tvars=tvars, args=args, origin=origin, extra=extra, orig_bases=orig_bases
        )
        if not inspect.isabstract(cls):
            last_base_class_origin = getattr(bases[-1], "__origin__", None)
            assert last_base_class_origin is ReadOnlyRepository or last_base_class_origin is Repository
            if hasattr(cls, "prepare"):
                entity_cls, _identity_cls = bases[-1].__args__
                cls.prepare(entity_cls)
        if args:
            entity_cls, _identity_cls = args
            if entity_cls not in mcs.entities_to_aets:
                mcs.entities_to_aets[entity_cls] = build(entity_cls)
        return cls


class ReadOnlyRepository(typing.Generic[EntityType, IdentityType], metaclass=RepositoryMeta):
    @classmethod
    @abc.abstractmethod
    def prepare(self) -> None:
        pass

    @abc.abstractmethod
    def get(self, identity: IdentityType) -> EntityType:
        pass


class Repository(typing.Generic[EntityType, IdentityType], metaclass=RepositoryMeta):
    @classmethod
    @abc.abstractmethod
    def prepare(self) -> None:
        pass

    @abc.abstractmethod
    def get(self, identity: IdentityType) -> EntityType:
        pass

    @abc.abstractmethod
    def save(self, entity: EntityType) -> None:
        pass
