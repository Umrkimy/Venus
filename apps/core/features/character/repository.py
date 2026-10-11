import json
import struct
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, load_only

from features.character.models.character_model import CharacterModel

ROW_ID = 1


@dataclass
class CharacterInfo:
    name: str
    size: int
    uploaded_at: datetime


def is_vrm(data: bytes) -> bool:
    """A VRM is a glTF binary whose JSON part names a VRM extension.

    glTF binary: "glTF", version, length, then a chunk: its length, "JSON", the text.
    """
    if len(data) < 20 or data[:4] != b"glTF":
        return False
    length, kind = struct.unpack_from("<I4s", data, 12)
    if kind != b"JSON":
        return False
    try:
        extensions = json.loads(data[20 : 20 + length]).get("extensions", {})
    except ValueError:
        return False
    # "VRMC_vrm" is VRM 1.0; "VRM" is the older 0.x.
    return "VRMC_vrm" in extensions or "VRM" in extensions


class CharacterRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def get_info(self) -> CharacterInfo | None:
        with Session(self.engine) as session:
            # Leaves the file itself (megabytes) in the database.
            row = session.scalar(
                select(CharacterModel)
                .where(CharacterModel.id == ROW_ID)
                .options(load_only(CharacterModel.name, CharacterModel.size, CharacterModel.uploaded_at))
            )
            if row is None:
                return None
            return CharacterInfo(row.name, row.size, row.uploaded_at)

    def get_data(self) -> bytes | None:
        with Session(self.engine) as session:
            return session.scalar(select(CharacterModel.data).where(CharacterModel.id == ROW_ID))

    def save(self, name: str, data: bytes) -> CharacterInfo:
        uploaded_at = datetime.now(timezone.utc)
        with Session(self.engine) as session:
            row = session.get(CharacterModel, ROW_ID)
            if row is None:
                session.add(CharacterModel(ROW_ID, name, len(data), uploaded_at, data))
            else:
                row.name, row.size, row.uploaded_at, row.data = name, len(data), uploaded_at, data
            session.commit()
        return CharacterInfo(name, len(data), uploaded_at)

    def delete(self) -> None:
        with Session(self.engine) as session:
            row = session.get(CharacterModel, ROW_ID)
            if row is not None:
                session.delete(row)
                session.commit()
