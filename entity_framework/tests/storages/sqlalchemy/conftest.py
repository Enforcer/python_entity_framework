from typing import Generator

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base


@pytest.fixture()
def sa_base() -> DeclarativeMeta:
    return declarative_base()


@pytest.fixture()
def session(sa_base: DeclarativeMeta, engine: Engine) -> Generator[Session, None, None]:
    sa_base.metadata.drop_all(engine)
    sa_base.metadata.create_all(engine)
    session_factory = sessionmaker(engine)
    yield session_factory()
    session_factory.close_all()
    sa_base.metadata.drop_all(engine)
