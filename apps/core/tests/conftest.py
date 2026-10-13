import pytest

from main import app
from storage.database import get_database_engine
from tests.database import make_test_engine


@pytest.fixture(autouse=True)
def never_the_real_database():
    """A test that forgets to swap in its own repository gets an empty test
    database, never the owner's real Venus (get_database_engine reads .env)."""
    engine = None

    def test_engine():
        nonlocal engine
        if engine is None:  # Only made when something actually asks.
            engine = make_test_engine()
        return engine

    app.dependency_overrides[get_database_engine] = test_engine
    yield
    app.dependency_overrides.pop(get_database_engine, None)
    if engine is not None:
        engine.dispose()
