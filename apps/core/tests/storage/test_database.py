from sqlalchemy.engine import make_url

from storage.database import create_database_engine


def test_create_database_engine_uses_database_url():
    database_url = (
        "postgresql+psycopg://venus:test-password@127.0.0.1:5432/venus"
    )

    engine = create_database_engine(database_url)

    assert engine.url == make_url(database_url)

    engine.dispose()