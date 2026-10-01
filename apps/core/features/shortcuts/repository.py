from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from features.shortcuts.models.site_shortcut import SiteShortcut


class ShortcutRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def list_all(self) -> list[SiteShortcut]:
        with Session(self.engine) as session:
            rows = session.scalars(select(SiteShortcut).order_by(SiteShortcut.keyword))
            return list(rows)

    def get(self, keyword: str) -> SiteShortcut | None:
        with Session(self.engine) as session:
            return session.get(SiteShortcut, keyword)

    def add(self, shortcut: SiteShortcut) -> None:
        # Keep the values readable after commit; the route returns them.
        with Session(self.engine, expire_on_commit=False) as session:
            session.add(shortcut)
            session.commit()

    def delete(self, keyword: str) -> bool:
        with Session(self.engine) as session:
            shortcut = session.get(SiteShortcut, keyword)
            if shortcut is None:
                return False
            session.delete(shortcut)
            session.commit()
            return True

    def update(
        self,
        keyword: str,
        label: str,
        home_url: str,
        search_url: str | None,
    ) -> SiteShortcut | None:
        # Keep the values readable after commit; the route returns them.
        with Session(self.engine, expire_on_commit=False) as session:
            shortcut = session.get(SiteShortcut, keyword)
            if shortcut is None:
                return None
            shortcut.label = label
            shortcut.home_url = home_url
            shortcut.search_url = search_url
            session.commit()
            return shortcut
