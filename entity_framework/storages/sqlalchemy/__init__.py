import typing

from sqlalchemy.orm import Session, Query, exc
from sqlalchemy.ext.declarative import DeclarativeMeta

from entity_framework.repository import EntityType, IdentityType
from entity_framework.storages.sqlalchemy import native_type_to_column, types
from entity_framework.storages.sqlalchemy.populating_aggregates.visitor import BuildingAggregateVisitor
from entity_framework.storages.sqlalchemy.constructing_model.visitor import ModelBuildingVisitor
from entity_framework.storages.sqlalchemy.querying.visitor import QueryBuildingVisitor
from entity_framework.storages.sqlalchemy.registry import SaRegistry


class SqlAlchemyRepo:
    base: DeclarativeMeta = None
    registry: SaRegistry = None

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
        aet = cls.registry.entities_to_aets[entity_cls]
        ModelBuildingVisitor(cls.base, cls.registry).traverse_from(aet.root)

    @property
    def query(self) -> Query:
        if not SqlAlchemyRepo._query:
            aet = self.registry.entities_to_aets[self.entity]
            visitor = QueryBuildingVisitor(self.registry)
            visitor.traverse_from(aet.root)
            SqlAlchemyRepo._query = visitor.query

        return SqlAlchemyRepo._query

    # TODO: sqlalchemy class could have an utility for creating IDS
    # Or it could be put into a separate utility function that would accept repo, then would get descendant classes
    # and got the new id.

    def get(self, identity: IdentityType) -> EntityType:
        # TODO: memoize populating func
        result = self.query.with_session(self._session).get(identity)
        if not result:
            # TODO: Raise more specialized exception
            raise exc.NoResultFound

        converting_visitor = BuildingAggregateVisitor(result)
        aet = self.registry.entities_to_aets[self.entity]
        converting_visitor.traverse_from(aet.root)
        return converting_visitor.result

    def save(self, entity: EntityType) -> None:
        pass
