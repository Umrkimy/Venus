from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from features.settings.models.command_mode import CommandModeSetting

MODE_ROW_ID = 1


class SettingsRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def get_mode(self) -> str:
        with Session(self.engine) as session:
            setting = session.get(CommandModeSetting, MODE_ROW_ID)
            if setting is None:
                return "confirm"
            return setting.mode

    def set_mode(self, mode: str) -> None:
        with Session(self.engine) as session:
            # merge inserts the row the first time and updates it afterwards.
            session.merge(CommandModeSetting(id=MODE_ROW_ID, mode=mode))
            session.commit()
