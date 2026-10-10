from features.settings.repository import SettingsRepository
from tests.database import make_test_engine


def create_repository() -> SettingsRepository:
    engine = make_test_engine()
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
