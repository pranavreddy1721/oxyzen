"""Scheduled AQI alerts for every saved location, delivered by email and in-dashboard."""
import asyncio
import logging
import os
from datetime import datetime, timezone, timedelta

import requests
import aqi_data

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)

POLL_SECONDS = max(60, int(os.environ.get("AQI_ALERT_POLL_SECONDS", "300")))
MAX_READING_AGE = timedelta(hours=2)
BREVO_URL = "https://api.brevo.com/v3/smtp/email"


def is_email_configured():
    return bool(
        os.environ.get("BREVO_API_KEY", "").strip()
        and os.environ.get("BREVO_SENDER_EMAIL", "").strip()
    )


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
    response = requests.post(
        BREVO_URL,
        headers={
            "api-key": os.environ["BREVO_API_KEY"].strip(),
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={
            "sender": {
                "name": os.environ.get("BREVO_SENDER_NAME", "OXYZEN").strip() or "OXYZEN",
                "email": os.environ["BREVO_SENDER_EMAIL"].strip(),
            },
            "to": [{"email": to}],
            "subject": subject,
            "textContent": body,
        },
        timeout=15,
    )
    response.raise_for_status()


def _notification_content(state, location, snapshot, threshold):
    aqi = int(snapshot["aqi"])
    station = snapshot.get("source", {}).get("station") or "Air-quality data provider"
    updated = snapshot.get("providerUpdatedAt") or "Timestamp unavailable"
    if state == "above":
        subject = f"OXYZEN AQI alert: {aqi} at {location}"
        title = f"AQI threshold exceeded in {location}"
        message = (
            f"The latest available AQI reading for {location} is {aqi} "
            f"({snapshot.get('category', 'Unknown')}), at or above your threshold of {threshold}.\n\n"
        )
    else:
        subject = f"OXYZEN: Air quality recovered at {location}"
        title = f"Air quality recovered in {location}"
        message = (
            f"The latest available AQI reading for {location} is {aqi}, "
            f"below your threshold of {threshold}.\n\n"
        )
    message += (
        f"Monitoring source: {station}\n"
        f"Station updated: {updated}\n\n"
        "This is an environmental-awareness notification, not medical advice."
    )
    return {
        "subject": subject,
        "title": title,
        "message": message,
        "aqi": aqi,
        "category": snapshot.get("category", "Unknown"),
        "threshold": threshold,
        "station": station,
        "providerUpdatedAt": snapshot.get("providerUpdatedAt"),
    }


async def _deliver_pending_emails(db, user, logger):
    """Retry pending email deliveries without creating duplicate dashboard alerts."""
    recipient = (user.get("email") or "").strip()
    if not recipient:
        logger.warning("User %s has no email address; dashboard alerts remain available", str(user["_id"]))
        return
    pending = await db.aqi_notifications.find({
        "userId": str(user["_id"]),
        "emailStatus": "pending",
    }).to_list(100)
    for notification in pending:
        try:
            await asyncio.to_thread(
                _send_email,
                recipient,
                notification["subject"],
                notification["message"],
            )
            await db.aqi_notifications.update_one(
                {"_id": notification["_id"], "emailStatus": "pending"},
                {"$set": {"emailStatus": "sent", "emailSentAt": datetime.now(timezone.utc).isoformat()}},
            )
            logger.info(
                "AQI alert email sent for user=%s location=%s",
                str(user["_id"]), notification.get("locationName"),
            )
        except Exception:
            logger.exception(
                "AQI alert email delivery failed for user=%s notification=%s",
                str(user["_id"]), str(notification["_id"]),
            )


async def _record_transition(db, user, saved_location, state, snapshot, threshold, logger):
    uid = str(user["_id"])
    location_id = str(saved_location.get("locationId") or saved_location.get("_id"))
    state_id = f"{uid}:{location_id}"
    previous = await db.aqi_alert_states.find_one({"_id": state_id})
    previous_state = previous.get("state", "clear") if previous else "clear"
    if previous_state == state:
        return

    now = datetime.now(timezone.utc).isoformat()
    state_doc = {
        "_id": state_id,
        "userId": uid,
        "locationId": location_id,
        "locationName": saved_location.get("name", "Saved location"),
        "state": state,
        "aqi": int(snapshot["aqi"]),
        "threshold": threshold,
        "providerUpdatedAt": snapshot.get("providerUpdatedAt"),
        "updatedAt": now,
    }
    await db.aqi_alert_states.update_one(
        {"_id": state_id},
        {"$set": state_doc},
        upsert=True,
    )

    details = _notification_content(state, state_doc["locationName"], snapshot, threshold)
    event_key = f"{state_id}:{state}:{snapshot.get('providerUpdatedAt') or now}"
    notification = {
        "eventKey": event_key,
        "userId": uid,
        "locationId": location_id,
        "locationName": state_doc["locationName"],
        "state": state,
        "title": details["title"],
        "message": details["message"],
        "subject": details["subject"],
        "aqi": details["aqi"],
        "category": details["category"],
        "threshold": threshold,
        "station": details["station"],
        "providerUpdatedAt": details["providerUpdatedAt"],
        "createdAt": now,
        "read": False,
        "emailStatus": "pending",
    }
    await db.aqi_notifications.update_one(
        {"eventKey": event_key},
        {"$setOnInsert": notification},
        upsert=True,
    )
    logger.info(
        "Recorded %s AQI transition for user=%s location=%s AQI=%s threshold=%s",
        state, uid, state_doc["locationName"], snapshot["aqi"], threshold,
    )


async def check_user(db, user, logger):
    if not user.get("alertsEnabled", True) or not user.get("monitoringEnabled"):
        logger.info("Skipping user %s: saved-location monitoring or email alerts are disabled", str(user.get("_id")))
        return

    saved_locations = await db.saved_locations.find({"userId": str(user["_id"])}).to_list(100)
    if not saved_locations:
        logger.info("User %s has no saved locations to monitor", str(user.get("_id")))
        return

    threshold = int(user.get("alertThreshold", 150))
    for saved in saved_locations:
        location_name = saved.get("name") or "Saved location"
        try:
            location = aqi_data.make_custom_location(
                float(saved["lat"]),
                float(saved["lon"]),
                location_name,
                saved.get("country", ""),
            )
            snapshot = await asyncio.to_thread(aqi_data.current_snapshot, location)
        except Exception as exc:
            logger.warning(
                "AQI fetch failed for user=%s location=%s: %s",
                str(user["_id"]), location_name, exc,
            )
            continue

        updated = _provider_timestamp(snapshot)
        now = datetime.now(timezone.utc)
        if (
            updated is None
            or now - updated > MAX_READING_AGE
            or updated - now > timedelta(minutes=5)
        ):
            logger.warning(
                "Ignoring stale/missing AQI timestamp for user=%s location=%s timestamp=%r",
                str(user["_id"]), location_name, snapshot.get("providerUpdatedAt"),
            )
            continue

        state = "above" if int(snapshot["aqi"]) >= threshold else "clear"
        await _record_transition(db, user, saved, state, snapshot, threshold, logger)

    # Delivery is retried independently of the next AQI state transition.
    await _deliver_pending_emails(db, user, logger)


async def monitor_loop(db, logger):
    logger.info("OXYZEN saved-location AQI monitor started; interval=%s seconds", POLL_SECONDS)
    while True:
        try:
            users = await db.users.find({
                "monitoringEnabled": True,
                "alertsEnabled": True,
            }).to_list(1000)
            for user in users:
                await check_user(db, user, logger)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("AQI monitor cycle failed")
        await asyncio.sleep(POLL_SECONDS)


async def run_once():
    """Run one scheduled monitoring cycle and exit cleanly."""
    from motor.motor_asyncio import AsyncIOMotorClient

    mongo_url = os.environ.get("MONGO_URL", "").strip()
    db_name = os.environ.get("DB_NAME", "").strip()
    if not mongo_url or not db_name:
        raise RuntimeError("MONGO_URL and DB_NAME must be configured for the scheduled AQI worker")
    if not os.environ.get("WAQI_TOKEN", "").strip():
        raise RuntimeError("WAQI_TOKEN must be configured for the scheduled AQI worker")
    if not is_email_configured():
        raise RuntimeError("BREVO_API_KEY and BREVO_SENDER_EMAIL must be configured for the scheduled AQI worker")

    client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=15000)
    logger = logging.getLogger("oxyzen.alert_worker")
    try:
        db = client[db_name]
        await db.command("ping")
        users = await db.users.find({
            "monitoringEnabled": True,
            "alertsEnabled": True,
        }).to_list(1000)
        logger.info("Scheduled AQI check starting for %s opted-in users", len(users))
        for user in users:
            await check_user(db, user, logger)
        logger.info("Scheduled AQI check completed")
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(run_once())
