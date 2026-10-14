import json
import struct
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, load_only

from features.character.models.character_animation import CharacterAnimation
from features.character.models.character_model import CharacterModel, KeptFile

@dataclass
class CharacterInfo:
    id: int
    name: str
    size: int
    uploaded_at: datetime
    active: bool


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


def is_glb(data: bytes) -> bool:
    """Any glTF binary with a readable JSON part (a place, a prop, a model)."""
    if len(data) < 20 or data[:4] != b"glTF":
        return False
    length, kind = struct.unpack_from("<I4s", data, 12)
    if kind != b"JSON":
        return False
    try:
        return isinstance(json.loads(data[20 : 20 + length]), dict)
    except ValueError:
        return False


def is_vrma(data: bytes) -> bool:
    """A VRM animation is a glTF binary naming the VRMC_vrm_animation extension."""
    return "VRMC_vrm_animation" in gltf_extensions(data)


class CharacterRepository:
    """Uploaded models; with table=CharacterPlace, uploaded places (same rules)."""

    def __init__(self, engine: Engine, table: type[KeptFile] = CharacterModel) -> None:
        self.engine = engine
        self.table = table

    def list_info(self) -> list[CharacterInfo]:
        with Session(self.engine) as session:
            # Leaves the files themselves (megabytes each) in the database.
            rows = session.scalars(
                select(self.table)
                .options(
                    load_only(
                        self.table.name,
                        self.table.size,
                        self.table.uploaded_at,
                        self.table.active,
                    )
                )
                .order_by(self.table.id)
            )
            return [model_info(row) for row in rows]

    def get_info(self) -> CharacterInfo | None:
        """The model in use, or None for the template."""
        return next((info for info in self.list_info() if info.active), None)

    def get_data(self) -> bytes | None:
        with Session(self.engine) as session:
            return session.scalar(select(self.table.data).where(self.table.active.is_(True)))

    def add(self, name: str, data: bytes) -> CharacterInfo:
        """Keeps the upload and puts it in use."""
        row = self.table(name, len(data), datetime.now(timezone.utc), data, active=True)
        with Session(self.engine) as session:
            session.execute(update(self.table).values(active=False))
            session.add(row)
            session.commit()
            return model_info(row)

    def activate(self, model_id: int | None) -> bool:
        """Puts one model in use (None = the template). False if there's no such model."""
        with Session(self.engine) as session:
            if model_id is not None and session.get(self.table, model_id) is None:
                return False
            session.execute(update(self.table).values(active=self.table.id == model_id))
            session.commit()
            return True

    def delete(self, model_id: int) -> bool:
        with Session(self.engine) as session:
            row = session.get(self.table, model_id)
            if row is None:
                return False
            session.delete(row)
            session.commit()
            return True


def model_info(row: KeptFile) -> CharacterInfo:
    return CharacterInfo(row.id, row.name, row.size, row.uploaded_at, row.active)


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
