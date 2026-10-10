import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.pool import NullPool, StaticPool

# Importing every model registers its table with Base.metadata (same list as
# migrations/env.py), so create_all and drop_all see all tables.
from features.auth.models.node_device import NodeDevice  # noqa: F401
from features.auth.models.owner_account import OwnerAccount  # noqa: F401
from features.auth.models.owner_session import OwnerSession  # noqa: F401
from features.commands.models.command_record import CommandRecord  # noqa: F401
from features.conversations.models.conversation import Conversation, Message  # noqa: F401
from features.memories.models.memory import Memory  # noqa: F401
from features.personalities.models.personality import Personality  # noqa: F401
from features.projects.models.project import Project  # noqa: F401
from features.settings.models.command_mode import CommandModeSetting  # noqa: F401
from features.settings.models.llm import LlmSetting  # noqa: F401
from features.settings.models.time import TimeSetting  # noqa: F401
from features.settings.models.voice import VoiceSetting  # noqa: F401
from features.shortcuts.models.site_shortcut import SiteShortcut  # noqa: F401
from storage.base import Base

# Set to a Postgres database (name must end in _test) to run the tests
# against real Postgres, like CI does. Empty = SQLite in memory.
TEST_DATABASE_URL_NAME = "VENUS_CORE_TEST_DATABASE_URL"


def get_test_database_url() -> str:
    return os.environ.get(TEST_DATABASE_URL_NAME, "").strip()


def make_test_engine(sqlite_file: Path | None = None) -> Engine:
    """An engine on an empty database that already has every table."""
    url = get_test_database_url()
    if url:
        engine = postgres_test_engine(url)
    elif sqlite_file is not None:
        # A real file, so several threads get their own connections.
        engine = create_engine(f"sqlite+pysqlite:///{sqlite_file.as_posix()}")
    else:
        # One shared in-memory connection, usable from TestClient's thread.
        engine = create_engine(
            "sqlite+pysqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    Base.metadata.create_all(engine)
    return engine


def postgres_test_engine(url: str) -> Engine:
    database = make_url(url).database or ""
    # Every test wipes the tables, so never point this at the real database.
    if not database.endswith("_test"):
        raise ValueError(
            f"{TEST_DATABASE_URL_NAME} database name must end in _test, got {database!r}"
        )
    # NullPool closes each connection when done: hundreds of tests make
    # engines, and pooled connections would pile up on the server.
    engine = create_engine(url, poolclass=NullPool)
    Base.metadata.drop_all(engine)
    return engine


def as_utc(value: datetime) -> datetime:
    """SQLite hands dates back without a time zone, Postgres keeps UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
