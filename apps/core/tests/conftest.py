import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from main import app
from storage.base import Base
from storage.database import get_database_engine
from tests import database  # noqa: F401  (imports every model, so create_all knows them)


@pytest.fixture(autouse=True)
def never_the_real_database():
    """A test that forgets to swap in its own repository gets an empty database,
    never the owner's real Venus (get_database_engine reads .env).

    Always a private in-memory SQLite: on the Postgres CI run, making another
    test engine would wipe the tables the test itself just filled.
    """
    engine = None

    def blank_engine():
        nonlocal engine
        if engine is None:  # Only made when something actually asks.
            engine = create_engine("sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
            Base.metadata.create_all(engine)
        return engine

    app.dependency_overrides[get_database_engine] = blank_engine
    yield
    app.dependency_overrides.pop(get_database_engine, None)
    if engine is not None:
        engine.dispose()
