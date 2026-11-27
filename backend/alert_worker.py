"""Opt-in current-location AQI email monitoring via Brevo."""
import asyncio
import logging
import os
from datetime import datetime, timezone, timedelta

import requests
import aqi_data

POLL_SECONDS = max(60, int(os.environ.get("AQI_ALERT_POLL_SECONDS", "900")))
MAX_READING_AGE = timedelta(hours=2)
BREVO_URL = "https://api.brevo.com/v3/smtp/email"


def is_email_configured():
    return bool(os.environ.get("BREVO_API_KEY", "").strip() and os.environ.get("BREVO_SENDER_EMAIL", "").strip())


def _provider_timestamp(snapshot):
    raw = snapshot.get("providerUpdatedAt")
    if not raw:
        return None
    try:
        value = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _send_email(to, subject, body):
    api_key = os.environ["BREVO_API_KEY"].strip()
    sender_email = os.environ["BREVO_SENDER_EMAIL"].strip()
    sender_name = os.environ.get("BREVO_SENDER_NAME", "OXYZEN").strip() or "OXYZEN"
    response = requests.post(
        BREVO_URL,
        headers={"api-key": api_key, "accept": "application/json", "Content-Type": "application/json"},
        json={
            "sender": {"name": sender_name, "email": sender_email},
            "to": [{"email": to}],
            "subject": subject,
            "textContent": body,
        },
        timeout=15,
    )
    response.raise_for_status()


async def _send_transition(db, user, state, snapshot, logger):
    uid = user["_id"]
    threshold = int(user.get("alertThreshold", 150))
    current_state = user.get("monitorState", "clear")
    if state == current_state:
        return

    state_filter = (
        {"$or": [{"monitorState": "clear"}, {"monitorState": {"$exists": False}}]}
        if current_state == "clear"
        else {"monitorState": current_state}
    )
    result = await db.users.update_one(
        {"_id": uid, **state_filter},
        {"$set": {"monitorState": state, "lastAlertEvaluatedAt": datetime.now(timezone.utc).isoformat()}},
    )
    if result.modified_count != 1:
        return

    location = user.get("monitorLocationName") or "your current location"
    if state == "above":
        subject = f"OXYZEN AQI alert: {snapshot['aqi']} at {location}"
        message = (
            f"The latest available AQI reading for {location} is {snapshot['aqi']} "
            f"({snapshot.get('category', 'Unknown')}), at or above your alert threshold of {threshold}.\n\n"
            f"Monitoring station: {snapshot.get('source', {}).get('station', 'WAQI station')}\n"
            f"Station updated: {snapshot.get('providerUpdatedAt')}\n"
            "This is an environmental-awareness notification, not medical advice."
        )
    else:
        subject = f"OXYZEN: Air quality recovered at {location}"
        message = (
            f"The latest available AQI reading for {location} is {snapshot['aqi']}, "
            f"below your alert threshold of {threshold}.\n\n"
            f"Monitoring station: {snapshot.get('source', {}).get('station', 'WAQI station')}\n"
            f"Station updated: {snapshot.get('providerUpdatedAt')}\n"
            "This is an environmental-awareness notification, not medical advice."
        )

    try:
        recipient = (user.get("email") or "").strip()
        if not recipient:
            raise ValueError("User has no registered email address")
        await asyncio.to_thread(_send_email, recipient, subject, message)
        logger.info("AQI %s email sent for user %s", state, str(uid))
    except Exception:
        await db.users.update_one({"_id": uid, "monitorState": state}, {"$set": {"monitorState": current_state}})
        logger.exception("AQI alert email delivery failed for user %s", str(uid))


async def check_user(db, user, logger):
    if not user.get("alertsEnabled", True) or not user.get("monitoringEnabled"):
        return
    lat, lon = user.get("monitorLat"), user.get("monitorLon")
    if lat is None or lon is None:
        return
    location = aqi_data.make_custom_location(
        float(lat), float(lon),
        user.get("monitorLocationName") or None,
        user.get("monitorLocationCountry") or "",
    )
    try:
        snapshot = await asyncio.to_thread(aqi_data.current_snapshot, location)
    except Exception as exc:
        logger.warning("AQI monitor fetch failed for user %s: %s", str(user["_id"]), exc)
        return

    updated = _provider_timestamp(snapshot)
    if updated is None or datetime.now(timezone.utc) - updated > MAX_READING_AGE:
        logger.info("Skipping stale/undated WAQI reading for user %s", str(user["_id"]))
        return

    threshold = int(user.get("alertThreshold", 150))
    next_state = "above" if int(snapshot["aqi"]) >= threshold else "clear"
    await _send_transition(db, user, next_state, snapshot, logger)


async def monitor_loop(db, logger):
    logger.info("OXYZEN current-location AQI monitor started; interval=%s seconds", POLL_SECONDS)
    while True:
        try:
            users = await db.users.find({
                "monitoringEnabled": True,
                "alertsEnabled": True,
                "monitorLat": {"$exists": True},
                "monitorLon": {"$exists": True},
            }).to_list(1000)
            for user in users:
                await check_user(db, user, logger)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("AQI monitor cycle failed")
        await asyncio.sleep(POLL_SECONDS)
