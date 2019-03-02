from typing import Optional, Generator, Union, Type, List, Dict

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base

from entity_framework import Entity, Identity, ValueObject, Repository
from entity_framework.storages.sqlalchemy import SqlAlchemyRepo
from entity_framework.storages.sqlalchemy.registry import SaRegistry


SubscriberId = int
PlanId = int


class Plan(Entity):
    id: Identity[PlanId]
    discount: float


class Subscription(ValueObject):
    plan_id: PlanId
    start_at: int


class Subscriber(Entity):
    id: Identity[SubscriberId]
    plan: Plan
    current_subscription: Optional[Subscription] = None
    lifetime_subscription: Optional[Subscription] = None

    def subscribe(self, subscription: Subscription) -> None:
        if not self.current_subscription:
            self.current_subscription = subscription
        else:
            raise Exception("Impossible")


SubscriberRepo = Repository[Subscriber, SubscriberId]


@pytest.fixture()
def sa_base() -> DeclarativeMeta:
    return declarative_base()


@pytest.fixture()
def sa_repo(sa_base: DeclarativeMeta) -> Type[Union[SqlAlchemyRepo, SubscriberRepo]]:
    class SqlSubscriberRepo(SqlAlchemyRepo, SubscriberRepo):
        base = sa_base
        registry = SaRegistry()

    return SqlSubscriberRepo


@pytest.fixture()
def session(sa_base: DeclarativeMeta, engine: Engine) -> Generator[Session, None, None]:
    sa_base.metadata.drop_all(engine)
    sa_base.metadata.create_all(engine)
    session_factory = sessionmaker(engine)
    yield session_factory()
    session_factory.close_all()
    sa_base.metadata.drop_all(engine)


@pytest.mark.parametrize(
    "tables, entities, rows, expected_aggregate",
    [
        (
            ["plans", "subscribers"],
            [Plan, Subscriber],
            [[{"id": 1, "discount": 0.5}], [{"id": 1, "plan_id": 1}]],
            Subscriber(id=1, plan=Plan(id=1, discount=0.5)),
        ),
        (
            ["plans", "subscribers"],
            [Plan, Subscriber],
            [
                [{"id": 1, "discount": 0.5}],
                [{"id": 1, "plan_id": 1, "current_subscription_plan_id": 1, "current_subscription_start_at": 0}],
            ],
            Subscriber(id=1, plan=Plan(id=1, discount=0.5), current_subscription=Subscription(1, 0)),
        ),
    ],
)
def test_gets_exemplary_data(
    sa_repo: Type[Union[SqlAlchemyRepo, SubscriberRepo]],
    session: Session,
    tables: List[str],
    entities: List[Type[Entity]],
    rows: List[Dict],
    expected_aggregate: Subscriber,
) -> None:
    repo = sa_repo(session)

    for table_name, entity, mappings in zip(tables, entities, rows):
        model = sa_repo.registry.entities_models[entity]
        assert table_name == model.__tablename__
        session.bulk_insert_mappings(model, mappings)

    assert repo.get(expected_aggregate.id) == expected_aggregate


@pytest.mark.parametrize(
    "aggregate, expected_db_data",
    [
        (
            Subscriber(id=1, plan=Plan(id=1, discount=0.5), current_subscription=Subscription(1, 0)),
            {
                Plan: [{"id": 1, "discount": 0.5}],
                Subscriber: [{"id": 1, "current_subscription_start_at": 0, "current_subscription_plan_id": 1}],
            },
        )
    ],
)
def test_saves_exemplary_data(
    sa_repo: Type[Union[SqlAlchemyRepo, SubscriberRepo]],
    session: Session,
    aggregate: Subscriber,
    expected_db_data: Dict[Type[Entity], List[Dict]],
) -> None:
    repo = sa_repo(session)

    repo.save(aggregate)

    for entity, expected_rows in expected_db_data.items():
        model = sa_repo.registry.entities_models[entity]
        assert session.execute(model.__table__.select()).fetchall() == expected_rows
