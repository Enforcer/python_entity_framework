from datetime import datetime
from typing import Optional, Union, Type, List, Dict

import pytest
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import DeclarativeMeta

from entity_framework import Entity, Identity, ValueObject, Repository
from entity_framework.storages.sqlalchemy import SqlAlchemyRepo
from entity_framework.storages.sqlalchemy.registry import SaRegistry


class Deadline(ValueObject):
    datetime: datetime
    penalty: int


class Goal(ValueObject):
    assignee: str
    deadline: Optional[Deadline] = None


class Board(Entity):
    id: Identity[int]
    goal: Optional[Goal] = None


BoardRepo = Repository[Board, int]


DATETIME = datetime.now()


@pytest.fixture()
def sa_repo(sa_base: DeclarativeMeta) -> Type[Union[SqlAlchemyRepo, BoardRepo]]:
    class SaBoardRepo(SqlAlchemyRepo, BoardRepo):
        base = sa_base
        registry = SaRegistry()

    return SaBoardRepo


@pytest.mark.parametrize(
    "tables, entities, rows, expected_aggregate",
    [
        (["boards"], [Board], [[{"id": 1}]], Board(id=1)),
        (["boards"], [Board], [[{"id": 1, "goal_assignee": "me"}]], Board(id=1, goal=Goal(assignee="me"))),
        (
            ["boards"],
            [Board],
            [[{"id": 1, "goal_assignee": "me", "goal_deadline_datetime": DATETIME, "goal_deadline_penalty": 2000}]],
            Board(id=1, goal=Goal(assignee="me", deadline=Deadline(datetime=DATETIME, penalty=2000))),
        ),
    ],
)
def test_gets_exemplary_data(
    sa_repo: Type[Union[SqlAlchemyRepo, BoardRepo]],
    session: Session,
    tables: List[str],
    entities: List[Type[Entity]],
    rows: List[Dict],
    expected_aggregate: Board,
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
            Board(id=1),
            {Board: [{"id": 1, "goal_assignee": None, "goal_deadline_penalty": None, "goal_deadline_datetime": None}]},
        ),
        (
            Board(id=1, goal=Goal(assignee="me")),
            {Board: [{"id": 1, "goal_assignee": "me", "goal_deadline_penalty": None, "goal_deadline_datetime": None}]},
        ),
        (
            Board(id=1, goal=Goal(assignee="me", deadline=Deadline(datetime=DATETIME, penalty=1500))),
            {
                Board: [
                    {"id": 1, "goal_assignee": "me", "goal_deadline_penalty": 1500, "goal_deadline_datetime": DATETIME}
                ]
            },
        ),
    ],
)
def test_saves_exemplary_data(
    sa_repo: Type[Union[SqlAlchemyRepo, BoardRepo]],
    session: Session,
    aggregate: Board,
    expected_db_data: Dict[Type[Entity], List[Dict]],
) -> None:
    repo = sa_repo(session)

    repo.save(aggregate)

    for entity, expected_rows in expected_db_data.items():
        model = sa_repo.registry.entities_models[entity]
        assert [dict(row) for row in session.execute(model.__table__.select()).fetchall()] == expected_rows
