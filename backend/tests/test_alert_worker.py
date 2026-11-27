import asyncio
import logging
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import alert_worker


def test_provider_timestamp_rejects_missing_and_invalid_values():
    assert alert_worker._provider_timestamp({}) is None
    assert alert_worker._provider_timestamp({"providerUpdatedAt": "not-a-date"}) is None


def test_provider_timestamp_normalizes_utc():
    value = alert_worker._provider_timestamp({"providerUpdatedAt": "2026-11-27T10:00:00Z"})
    assert value.tzinfo is not None
    assert value.utcoffset() == timedelta(0)


class _Cursor:
    def __init__(self, values):
        self.values = values

    async def to_list(self, _limit):
        return list(self.values)


class _Collection:
    def __init__(self, values=None):
        self.values = list(values or [])
        self.docs = {}
        self.inserted = []

    def find(self, query):
        return _Cursor([d for d in self.values if all(d.get(k) == v for k, v in query.items())])

    async def find_one(self, query):
        return self.docs.get(query["_id"])

    async def update_one(self, query, update, upsert=False):
        key = query.get("_id") or query.get("eventKey")
        existing = self.docs.get(key)
        is_new = existing is None
        if is_new and upsert:
            existing = {"_id": key}
            self.docs[key] = existing
        if existing is not None:
            existing.update(update.get("$set", {}))
            if "$setOnInsert" in update and is_new:
                existing.update(update["$setOnInsert"])
            if is_new:
                self.values.append(existing)
            self.inserted.append(dict(existing))
        return None


class _DB:
    def __init__(self, saved):
        self.saved_locations = _Collection(saved)
        self.aqi_alert_states = _Collection()
        self.aqi_notifications = _Collection()


def test_check_user_checks_every_saved_location_and_records_transitions(monkeypatch):
    calls = []
    now = datetime.now(timezone.utc).isoformat()
    saved = [
        {"_id": "loc-1", "locationId": "delhi-id", "name": "Delhi", "lat": 28.6, "lon": 77.2, "country": "India", "userId": "user-1"},
        {"_id": "loc-2", "locationId": "mumbai-id", "name": "Mumbai", "lat": 19.0, "lon": 72.8, "country": "India", "userId": "user-1"},
    ]
    db = _DB(saved)

    monkeypatch.setattr(
        alert_worker.aqi_data,
        "make_custom_location",
        lambda lat, lon, name, country: {"lat": lat, "lon": lon, "name": name},
    )

    def snapshot(location):
        calls.append(location["name"])
        value = 180 if location["name"] == "Delhi" else 70
        return {
            "aqi": value,
            "category": "Unhealthy" if value >= 150 else "Good",
            "providerUpdatedAt": now,
            "source": {"station": location["name"] + " station"},
        }

    monkeypatch.setattr(alert_worker.aqi_data, "current_snapshot", snapshot)
    monkeypatch.setattr(alert_worker, "_send_email", lambda *_args: None)

    user = {
        "_id": "user-1",
        "email": "user@example.com",
        "alertsEnabled": True,
        "monitoringEnabled": True,
        "alertThreshold": 150,
    }

    asyncio.run(alert_worker.check_user(db, user, logging.getLogger("test")))

    assert calls == ["Delhi", "Mumbai"]
    assert db.aqi_alert_states.docs["user-1:delhi-id"]["state"] == "above"
    assert db.aqi_alert_states.docs["user-1:mumbai-id"]["state"] == "clear"
    assert any(d.get("locationName") == "Delhi" for d in db.aqi_notifications.inserted)


def test_check_user_skips_stale_readings(monkeypatch):
    calls = []
    db = _DB([{
        "_id": "loc-1", "locationId": "sangli-id", "name": "Sangli",
        "lat": 16.85, "lon": 74.58, "country": "India", "userId": "user-1",
    }])
    monkeypatch.setattr(
        alert_worker.aqi_data,
        "make_custom_location",
        lambda *args: {"name": args[2]},
    )
    monkeypatch.setattr(
        alert_worker.aqi_data,
        "current_snapshot",
        lambda _location: {
            "aqi": 190,
            "providerUpdatedAt": (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat(),
        },
    )
    monkeypatch.setattr(alert_worker, "_send_email", lambda *_args: calls.append("email"))

    user = {
        "_id": "user-1", "email": "user@example.com",
        "alertsEnabled": True, "monitoringEnabled": True, "alertThreshold": 150,
    }
    asyncio.run(alert_worker.check_user(db, user, logging.getLogger("test")))

    assert db.aqi_alert_states.docs == {}
    assert db.aqi_notifications.inserted == []
    assert calls == []


def test_check_user_respects_alert_opt_in(monkeypatch):
    db = _DB([{"locationId": "x", "name": "X", "lat": 1, "lon": 1, "userId": "user-1"}])
    calls = []
    monkeypatch.setattr(alert_worker.aqi_data, "current_snapshot", lambda _loc: calls.append("fetch"))
    user = {"_id": "user-1", "alertsEnabled": False, "monitoringEnabled": True}
    asyncio.run(alert_worker.check_user(db, user, logging.getLogger("test")))
    assert calls == []


def test_notification_content_includes_location_and_threshold():
    details = alert_worker._notification_content(
        "above",
        "Delhi",
        {"aqi": 127, "category": "Unhealthy for Sensitive Groups", "providerUpdatedAt": "2026-11-27T10:00:00Z", "source": {"station": "Delhi station"}},
        110,
    )
    assert "Delhi" in details["subject"]
    assert "127" in details["message"]
    assert "110" in details["message"]
