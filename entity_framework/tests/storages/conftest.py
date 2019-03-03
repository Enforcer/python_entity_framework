import pytest
from _pytest.fixtures import SubRequest
from sqlalchemy.engine import Engine, create_engine


@pytest.fixture()
def engine(request: SubRequest) -> Engine:
    connection_url = request.config.getoption("--sqlalchemy-postgres-url")
    assert connection_url, "You have to define --sqlalchemy-postgres-url cmd line option!"
    return create_engine(connection_url)
