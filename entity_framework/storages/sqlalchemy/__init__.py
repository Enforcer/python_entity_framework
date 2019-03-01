import typing

from sqlalchemy.orm import Session, Query
from sqlalchemy.ext.declarative import DeclarativeMeta

from entity_framework.abstract_entity_tree import AbstractEntityTree
from entity_framework.repository import EntityType, IdentityType, EntityOrVoType
from entity_framework.storages.sqlalchemy import native_type_to_column, types
from entity_framework.storages.sqlalchemy.populating_aggregates.visitor import BuildingAggregateVisitor
from entity_framework.storages.sqlalchemy.constructing_model.visitor import ModelBuildingVisitor
from entity_framework.storages.sqlalchemy.querying.visitor import QueryBuildingVisitor
from entity_framework.storages.sqlalchemy.registry import Registry


class SqlAlchemyRepo:
    base: DeclarativeMeta = None
    _classes_to_models: typing.Dict[EntityOrVoType, typing.Type]
    _query: typing.Optional[Query] = None

    def __init__(self, session: Session) -> None:
        self._session = session

    @classmethod
    def prepare(cls, entity_cls: typing.Type[EntityType]) -> None:
        assert cls.base, "Must set cls base to an instance of DeclarativeMeta!"
        if not getattr(cls, "entity", None):
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
        # TODO: memoize populating func
        aet: AbstractEntityTree = type(self.__class__).entities_to_aets[self.entity]
        if not SqlAlchemyRepo._query:
            visitor = QueryBuildingVisitor()
            visitor.traverse_from(aet.root)
            SqlAlchemyRepo._query = visitor.query

        # TODO: apply filter PROPERLY, not by hardcoded 'id'
        result = self._query.with_session(self._session).filter_by(id=identity).one()

        converting_visitor = BuildingAggregateVisitor(result)
        converting_visitor.traverse_from(aet.root)
        return converting_visitor.result

    def save(self, entity: EntityType) -> None:
        pass
