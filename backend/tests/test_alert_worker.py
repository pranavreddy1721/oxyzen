import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import alert_worker


def test_provider_timestamp_rejects_missing_and_invalid_values():
    assert alert_worker._provider_timestamp({}) is None
    assert alert_worker._provider_timestamp({"providerUpdatedAt": "not-a-date"}) is None


def test_provider_timestamp_normalizes_utc():
    value = alert_worker._provider_timestamp(
        {"providerUpdatedAt": "2026-11-27T10:00:00Z"}
    )
    assert value.tzinfo is not None
    assert value.utcoffset() == timedelta(0)


def test_check_user_skips_stale_reading(monkeypatch):
    calls = []

    monkeypatch.setattr(
        alert_worker.aqi_data,
        "make_custom_location",
        lambda *args, **kwargs: {"lat": args[0], "lon": args[1]},
    )
    monkeypatch.setattr(
        alert_worker.aqi_data,
        "current_snapshot",
        lambda _location: {
            "aqi": 190,
            "providerUpdatedAt": (
                datetime.now(timezone.utc) - timedelta(hours=3)
            ).isoformat(),
        },
    )

    async def record_transition(*args, **kwargs):
        calls.append(args)

    monkeypatch.setattr(alert_worker, "_send_transition", record_transition)
    user = {
        "_id": "test-user",
        "alertsEnabled": True,
        "monitoringEnabled": True,
        "monitorLat": 16.7,
        "monitorLon": 74.2,
        "alertThreshold": 150,
        "monitorState": "clear",
    }

    asyncio.run(alert_worker.check_user(None, user, alert_worker.logging.getLogger("test")))
    assert calls == []


def test_check_user_detects_threshold_crossing(monkeypatch):
    calls = []
    now = datetime.now(timezone.utc).isoformat()

    monkeypatch.setattr(
        alert_worker.aqi_data,
        "make_custom_location",
        lambda *args, **kwargs: {"lat": args[0], "lon": args[1]},
    )
    monkeypatch.setattr(
        alert_worker.aqi_data,
        "current_snapshot",
        lambda _location: {
            "aqi": 175,
            "category": "Unhealthy",
            "providerUpdatedAt": now,
            "source": {},
        },
    )

    async def record_transition(_db, _user, state, _snapshot, _logger):
        calls.append(state)

    monkeypatch.setattr(alert_worker, "_send_transition", record_transition)
    user = {
        "_id": "test-user",
        "alertsEnabled": True,
        "monitoringEnabled": True,
        "monitorLat": 16.7,
        "monitorLon": 74.2,
        "alertThreshold": 150,
        "monitorState": "clear",
    }

    asyncio.run(alert_worker.check_user(None, user, alert_worker.logging.getLogger("test")))
    assert calls == ["above"]
