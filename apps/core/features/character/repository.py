import json
import struct
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, load_only

from features.character.models.character_animation import CharacterAnimation
from features.character.models.character_model import CharacterModel

ROW_ID = 1


@dataclass
class CharacterInfo:
    name: str
    size: int
    uploaded_at: datetime


@dataclass
class AnimationInfo:
    id: int
    name: str
    use: str
    size: int
    uploaded_at: datetime


def gltf_extensions(data: bytes) -> dict:
    """The extensions in a glTF binary's JSON part ({} if it isn't one).

    glTF binary: "glTF", version, length, then a chunk: its length, "JSON", the text.
    """
    if len(data) < 20 or data[:4] != b"glTF":
        return {}
    length, kind = struct.unpack_from("<I4s", data, 12)
    if kind != b"JSON":
        return {}
    try:
        extensions = json.loads(data[20 : 20 + length]).get("extensions", {})
    except (ValueError, AttributeError):
        return {}
    return extensions if isinstance(extensions, dict) else {}


def is_vrm(data: bytes) -> bool:
    """A VRM is a glTF binary whose JSON part names a VRM extension."""
    extensions = gltf_extensions(data)
    # "VRMC_vrm" is VRM 1.0; "VRM" is the older 0.x.
    return "VRMC_vrm" in extensions or "VRM" in extensions


def is_vrma(data: bytes) -> bool:
    """A VRM animation is a glTF binary naming the VRMC_vrm_animation extension."""
    return "VRMC_vrm_animation" in gltf_extensions(data)


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


class AnimationRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def list_info(self) -> list[AnimationInfo]:
        with Session(self.engine) as session:
            # Leaves the files themselves in the database.
            rows = session.scalars(
                select(CharacterAnimation)
                .options(
                    load_only(
                        CharacterAnimation.name,
                        CharacterAnimation.use,
                        CharacterAnimation.size,
                        CharacterAnimation.uploaded_at,
                    )
                )
                .order_by(CharacterAnimation.id)
            )
            return [animation_info(row) for row in rows]

    def get_data(self, animation_id: int) -> bytes | None:
        with Session(self.engine) as session:
            return session.scalar(select(CharacterAnimation.data).where(CharacterAnimation.id == animation_id))

    def add(self, name: str, use: str, data: bytes) -> AnimationInfo:
        row = CharacterAnimation(name, use, len(data), datetime.now(timezone.utc), data)
        with Session(self.engine) as session:
            session.add(row)
            session.commit()
            return animation_info(row)

    def set_use(self, animation_id: int, use: str) -> AnimationInfo | None:
        with Session(self.engine) as session:
            row = session.get(CharacterAnimation, animation_id)
            if row is None:
                return None
            row.use = use
            session.commit()
            return animation_info(row)

    def delete(self, animation_id: int) -> bool:
        with Session(self.engine) as session:
            row = session.get(CharacterAnimation, animation_id)
            if row is None:
                return False
            session.delete(row)
            session.commit()
            return True


def animation_info(row: CharacterAnimation) -> AnimationInfo:
    return AnimationInfo(row.id, row.name, row.use, row.size, row.uploaded_at)
