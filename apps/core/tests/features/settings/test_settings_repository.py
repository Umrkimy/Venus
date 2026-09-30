from features.settings.models.command_mode import CommandModeSetting  # noqa: F401 registers the table
from features.settings.repository import SettingsRepository
from storage.base import Base
from storage.database import create_database_engine


def create_repository() -> SettingsRepository:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return SettingsRepository(engine)


def test_mode_defaults_to_confirm():
    repository = create_repository()

    assert repository.get_mode() == "confirm"


def test_set_mode_is_remembered():
    repository = create_repository()

    repository.set_mode("full")
    assert repository.get_mode() == "full"

    # The second write updates the same row instead of inserting another.
    repository.set_mode("confirm")
    assert repository.get_mode() == "confirm"
