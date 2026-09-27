from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI

from api.router import api_router
from features.commands.repository import CommandRecordRepository
from storage.database import get_database_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    command_records = CommandRecordRepository(get_database_engine())
    command_records.mark_all_dispatched_unknown(
        checked_at=datetime.now(timezone.utc),
    )

    yield


app = FastAPI(lifespan=lifespan)
app.include_router(api_router)
