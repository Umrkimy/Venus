from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from features.settings.models.command_mode import CommandModeSetting
from features.settings.models.llm import LlmSetting
from features.settings.models.voice import VoiceSetting

MODE_ROW_ID = 1
LLM_ROW_ID = 1
VOICE_ROW_ID = 1


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

    def get_llm(self) -> LlmSetting | None:
        with Session(self.engine) as session:
            return session.get(LlmSetting, LLM_ROW_ID)

    def set_llm(
        self,
        provider: str,
        model: str,
        api_key_encrypted: str | None,
    ) -> None:
        with Session(self.engine) as session:
            row = session.get(LlmSetting, LLM_ROW_ID)
            if row is None:
                session.add(
                    LlmSetting(
                        id=LLM_ROW_ID,
                        provider=provider,
                        model=model,
                        api_key_encrypted=api_key_encrypted,
                    ),
                )
            else:
                row.provider = provider
                row.model = model
                # No new key means "keep the saved one".
                if api_key_encrypted is not None:
                    row.api_key_encrypted = api_key_encrypted
            session.commit()

    def get_voice(self) -> VoiceSetting | None:
        with Session(self.engine) as session:
            return session.get(VoiceSetting, VOICE_ROW_ID)

    def set_voice(
        self,
        voice_id: str,
        model: str,
        api_key_encrypted: str | None,
    ) -> None:
        with Session(self.engine) as session:
            row = session.get(VoiceSetting, VOICE_ROW_ID)
            if row is None:
                session.add(
                    VoiceSetting(
                        id=VOICE_ROW_ID,
                        voice_id=voice_id,
                        model=model,
                        api_key_encrypted=api_key_encrypted,
                    ),
                )
            else:
                row.voice_id = voice_id
                row.model = model
                # No new key means "keep the saved one".
                if api_key_encrypted is not None:
                    row.api_key_encrypted = api_key_encrypted
            session.commit()
