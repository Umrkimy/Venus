from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import CoreSettings, get_settings
from features.auth.dependencies import get_auth_repository
from features.auth.repository import AuthRepository
from features.settings.dependencies import get_settings_repository
from features.settings.repository import SettingsRepository
from features.usage.dependencies import get_usage_repository
from features.usage.models.llm_usage import LlmUsage
from features.usage.prices import cost
from features.usage.repository import UsageRepository
from features.usage.router import period_starts
from main import app
from tests.database import make_test_engine

TEST_OWNER_TOKEN = "test-owner-token"
OWNER_HEADERS = {"Authorization": f"Bearer {TEST_OWNER_TOKEN}"}

client = TestClient(app)


def chat_usage(input_tokens: int, cached_tokens: int, output_tokens: int):
    # Shaped like the SDK's ResponseUsage.
    return SimpleNamespace(
        input_tokens=input_tokens,
        input_tokens_details=SimpleNamespace(cached_tokens=cached_tokens),
        output_tokens=output_tokens,
    )


def made_days_ago(usage: UsageRepository, days: int) -> None:
    # Move every row saved so far back in time.
    with Session(usage.engine) as session:
        for row in session.scalars(select(LlmUsage)):
            row.created_at -= timedelta(days=days)
        session.commit()


@pytest.fixture
def usage():
    engine = make_test_engine()
    repository = UsageRepository(engine)
    app.dependency_overrides[get_settings] = lambda: CoreSettings(
        dev_node_token="test-node-token",
        dev_owner_token=TEST_OWNER_TOKEN,
        database_url="postgresql+psycopg://venus:test-password@127.0.0.1:5432/venus",
    )
    app.dependency_overrides[get_auth_repository] = lambda: AuthRepository(engine)
    app.dependency_overrides[get_settings_repository] = lambda: SettingsRepository(engine)
    app.dependency_overrides[get_usage_repository] = lambda: repository
    yield repository
    app.dependency_overrides.clear()
    engine.dispose()


def test_cost_bills_cached_tokens_at_the_cheaper_rate():
    # gpt-6-luna: $0.10 input, $0.01 cached, $0.50 output per million.
    dollars = cost("gpt-6-luna", 1_000_000, 400_000, 100_000)

    assert dollars == pytest.approx(0.06 + 0.004 + 0.05)


def test_cost_of_a_model_without_a_price_is_unknown():
    assert cost("gpt-made-up", 1000, 0, 100) is None


def test_record_saves_chat_tokens_with_the_cached_part(usage):
    usage.record("chat", "gpt-6-luna", chat_usage(3000, 1024, 80))

    total = usage.total_since(None)

    assert (total.input_tokens, total.cached_tokens, total.output_tokens) == (3000, 1024, 80)


def test_record_saves_a_transcription_without_cached_tokens(usage):
    # A transcription's usage has no input_tokens_details.
    usage.record(
        "transcribe", "gpt-4o-mini-transcribe",
        SimpleNamespace(input_tokens=50, output_tokens=5),
    )

    total = usage.total_since(None)

    assert (total.input_tokens, total.cached_tokens, total.output_tokens) == (50, 0, 5)


def test_record_skips_a_call_that_sent_no_usage(usage):
    usage.record("chat", "gpt-6-luna", None)
    # Older transcription models report seconds, not tokens.
    usage.record("transcribe", "whisper-1", SimpleNamespace(seconds=3.0))

    assert usage.total_since(None).input_tokens == 0


def test_total_leaves_unpriced_models_out_of_the_cost_and_names_them(usage):
    usage.record("chat", "gpt-6-luna", chat_usage(1_000_000, 0, 0))
    usage.record("chat", "gpt-made-up", chat_usage(1_000_000, 0, 0))

    total = usage.total_since(None)

    assert total.cost_usd == pytest.approx(0.10)
    assert total.unpriced_models == ["gpt-made-up"]
    assert total.input_tokens == 2_000_000


def test_total_since_leaves_out_older_calls(usage):
    usage.record("chat", "gpt-6-luna", chat_usage(100, 0, 10))
    made_days_ago(usage, 3)
    usage.record("chat", "gpt-6-luna", chat_usage(200, 0, 20))

    recent = usage.total_since(datetime.now(timezone.utc) - timedelta(days=1))

    assert recent.input_tokens == 200
    assert usage.total_since(None).input_tokens == 300


def test_period_starts_use_the_owners_day_not_utc():
    # 23:30 UTC on Oct 31 is already Nov 1 in Kuala Lumpur (UTC+8).
    now = datetime(2026, 10, 31, 23, 30, tzinfo=timezone.utc)

    today, month = period_starts(now, "Asia/Kuala_Lumpur")

    assert today == datetime(2026, 10, 31, 16, 0, tzinfo=timezone.utc)
    assert month == datetime(2026, 10, 31, 16, 0, tzinfo=timezone.utc)


def test_period_starts_fall_back_to_utc_without_a_time_zone():
    now = datetime(2026, 10, 11, 9, 15, tzinfo=timezone.utc)

    today, month = period_starts(now, None)

    assert today == datetime(2026, 10, 11, tzinfo=timezone.utc)
    assert month == datetime(2026, 10, 1, tzinfo=timezone.utc)


def test_usage_endpoint_gives_today_month_and_all_time(usage):
    usage.record("chat", "gpt-6-luna", chat_usage(1_000_000, 0, 0))
    made_days_ago(usage, 400)
    usage.record("chat", "gpt-6-luna", chat_usage(2_000_000, 0, 0))

    response = client.get("/usage", headers=OWNER_HEADERS)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["today"]["input_tokens"] == 2_000_000
    assert body["month"]["input_tokens"] == 2_000_000
    assert body["all_time"]["input_tokens"] == 3_000_000
    assert body["all_time"]["cost_usd"] == pytest.approx(0.30)
    assert body["today"]["unpriced_models"] == []


def test_usage_endpoint_needs_the_owner(usage):
    response = client.get("/usage")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
