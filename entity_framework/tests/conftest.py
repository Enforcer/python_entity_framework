from _pytest.config.argparsing import Parser


def pytest_addoption(parser: Parser) -> None:
    parser.addoption("--sqlalchemy-postgres-url", action="store", default=None)
