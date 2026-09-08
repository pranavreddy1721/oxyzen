from dotenv import load_dotenv
from pathlib import Path
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr
from bson import ObjectId

import aqi_data
import health_risk
from auth import (
    hash_password, verify_password, create_access_token,
    create_refresh_token, decode_token,
)

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="OxyZen API")
api = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("oxyzen")

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
AI_PROVIDER = os.environ.get("AI_MODEL_PROVIDER", "gemini")
AI_MODEL = os.environ.get("AI_MODEL_NAME", "gemini-3-flash-preview")


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class RegisterInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class SavedLocationInput(BaseModel):
    locationId: str
    name: str
    country: str = ""
    lat: float
    lon: float
    label: str = ""


class ExposureInput(BaseModel):
    aqi: int
    environment: str = "outdoor"
    activity: str = "resting"
    duration: str = "1-3h"


class ChatInput(BaseModel):
    message: str
    sessionId: str
    context: Optional[dict] = None


class AlertPrefInput(BaseModel):
    threshold: int = 150
    enabled: bool = True


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
def _public_user(u: dict) -> dict:
    return {
        "id": str(u["_id"]),
        "name": u.get("name", ""),
        "email": u.get("email", ""),
        "role": u.get("role", "user"),
        "alertThreshold": u.get("alertThreshold", 150),
        "alertsEnabled": u.get("alertsEnabled", True),
        "createdAt": u.get("created_at").isoformat() if isinstance(u.get("created_at"), datetime) else u.get("created_at"),
    }


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except HTTPException:
        raise
    except jwt_err() as e:  # type: ignore
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def jwt_err():
    import jwt
    return (jwt.ExpiredSignatureError, jwt.InvalidTokenError)


def _set_cookies(response: Response, access: str, refresh: str):
    response.set_cookie("access_token", access, httponly=True, secure=True, samesite="none", max_age=604800, path="/")
    response.set_cookie("refresh_token", refresh, httponly=True, secure=True, samesite="none", max_age=2592000, path="/")


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------
@api.post("/auth/register")
async def register(body: RegisterInput, response: Response):
    email = body.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="An account with this email already exists.")
    doc = {
        "name": body.name.strip(),
        "email": email,
        "password_hash": hash_password(body.password),
        "role": "user",
        "alertThreshold": 150,
        "alertsEnabled": True,
        "created_at": datetime.now(timezone.utc),
    }
    res = await db.users.insert_one(doc)
    uid = str(res.inserted_id)
    access, refresh = create_access_token(uid, email), create_refresh_token(uid)
    _set_cookies(response, access, refresh)
    doc["_id"] = res.inserted_id
    return {"user": _public_user(doc), "token": access}


@api.post("/auth/login")
async def login(body: LoginInput, response: Response):
    email = body.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    uid = str(user["_id"])
    access, refresh = create_access_token(uid, email), create_refresh_token(uid)
    _set_cookies(response, access, refresh)
    return {"user": _public_user(user), "token": access}


@api.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"ok": True}


@api.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return {"user": _public_user(user)}


@api.post("/auth/refresh")
async def refresh_token_route(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = decode_token(token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        uid = payload["sub"]
        user = await db.users.find_one({"_id": ObjectId(uid)})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        access = create_access_token(uid, user["email"])
        response.set_cookie("access_token", access, httponly=True, secure=True, samesite="none", max_age=604800, path="/")
        return {"token": access}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@api.patch("/auth/alerts")
async def update_alerts(body: AlertPrefInput, user: dict = Depends(get_current_user)):
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"alertThreshold": body.threshold, "alertsEnabled": body.enabled}},
    )
    updated = await db.users.find_one({"_id": user["_id"]})
    return {"user": _public_user(updated)}


# ---------------------------------------------------------------------------
# Location routes
# ---------------------------------------------------------------------------
@api.get("/location/search")
async def location_search(q: str = "", limit: int = 8):
    results = aqi_data.search_locations(q, limit)
    fields = ("id", "name", "country", "admin1", "lat", "lon")
    return {"results": [{k: c.get(k, "") for k in fields} for c in results]}


@api.get("/location/reverse")
async def location_reverse(lat: float, lon: float):
    near = aqi_data.nearest_location(lat, lon)
    dist2 = (near["lat"] - lat) ** 2 + (near["lon"] - lon) ** 2
    # if far from any catalogue city, build a custom coordinate location
    loc = near if dist2 < 4.0 else aqi_data.make_custom_location(lat, lon)
    return {"location": {k: loc[k] for k in ("id", "name", "country", "lat", "lon")}}


# ---------------------------------------------------------------------------
# AQI routes
# ---------------------------------------------------------------------------
def _resolve_location(location_id: str, lat: Optional[float], lon: Optional[float], location_name: str = "", location_country: str = "") -> dict:
    if location_id:
        loc = aqi_data.find_by_id(location_id)
        if loc:
            return loc
    if lat is not None and lon is not None:
        near = aqi_data.nearest_location(lat, lon)
        dist2 = (near["lat"] - lat) ** 2 + (near["lon"] - lon) ** 2
        if dist2 < 4.0:
            return near
        return aqi_data.make_custom_location(lat, lon, location_name or None, location_country)
    raise HTTPException(status_code=400, detail="A location or coordinates are required.")


async def _log_history(loc: dict, snap: dict, user_id: Optional[str]):
    try:
        await db.aqi_records.insert_one({
            "locationId": loc["id"], "locationName": loc["name"],
            "aqi": snap["aqi"], "category": snap["category"],
            "pollutants": snap["pollutants"], "userId": user_id,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        logger.warning(f"history log failed: {e}")


@api.get("/aqi/current")
async def aqi_current(request: Request, locationId: str = "", lat: Optional[float] = None, lon: Optional[float] = None, locationName: str = "", locationCountry: str = ""):
    loc = _resolve_location(locationId, lat, lon, locationName, locationCountry)
    snap = aqi_data.current_snapshot(loc)
    snap["scale"] = aqi_data.AQI_CATEGORIES
    snap["pollutantMeta"] = aqi_data.POLLUTANT_META
    uid = None
    try:
        u = await get_current_user(request)
        uid = str(u["_id"])
    except HTTPException:
        pass
    await _log_history(loc, snap, uid)
    return snap


@api.get("/aqi/history")
async def aqi_history(locationId: str = "", lat: Optional[float] = None, lon: Optional[float] = None, range: str = "24h", locationName: str = "", locationCountry: str = ""):
    loc = _resolve_location(locationId, lat, lon, locationName, locationCountry)
    if range not in ("24h", "7d", "30d"):
        range = "24h"
    return {"range": range, "points": aqi_data.history(loc, range),
            "location": {k: loc[k] for k in ("id", "name", "country")}}


@api.get("/aqi/forecast")
async def aqi_forecast(locationId: str = "", lat: Optional[float] = None, lon: Optional[float] = None, days: int = 5, locationName: str = "", locationCountry: str = ""):
    loc = _resolve_location(locationId, lat, lon, locationName, locationCountry)
    days = max(2, min(7, days))
    return {"forecast": aqi_data.forecast(loc, days),
            "location": {k: loc[k] for k in ("id", "name", "country")}}


@api.get("/aqi/pollutant/{pollutant}")
async def pollutant_detail(pollutant: str, locationId: str = "", lat: Optional[float] = None, lon: Optional[float] = None, locationName: str = "", locationCountry: str = ""):
    if pollutant not in aqi_data.POLLUTANT_META:
        raise HTTPException(status_code=404, detail="Unknown pollutant")
    loc = _resolve_location(locationId, lat, lon, locationName, locationCountry)
    snap = aqi_data.current_snapshot(loc)
    hist = aqi_data.history(loc, "24h")
    meta = aqi_data.POLLUTANT_META[pollutant]
    current = snap["pollutants"][pollutant]
    ratio = current / meta["reference"]
    if ratio <= 1:
        severity = "Good"
    elif ratio <= 2:
        severity = "Moderate"
    elif ratio <= 3.5:
        severity = "High"
    else:
        severity = "Very High"
    return {
        "meta": meta,
        "current": current,
        "reference": meta["reference"],
        "severity": severity,
        "trend": [{"label": p["label"], "value": p[pollutant]} for p in hist],
    }


# ---------------------------------------------------------------------------
# Health risk routes
# ---------------------------------------------------------------------------
@api.get("/health-risk")
async def get_health_risk(request: Request, locationId: str = "", lat: Optional[float] = None, lon: Optional[float] = None, locationName: str = "", locationCountry: str = ""):
    loc = _resolve_location(locationId, lat, lon, locationName, locationCountry)
    snap = aqi_data.current_snapshot(loc)
    result = health_risk.assess(snap["aqi"], snap["pollutants"])
    result["location"] = {k: loc[k] for k in ("id", "name", "country")}
    uid = None
    try:
        u = await get_current_user(request)
        uid = str(u["_id"])
    except HTTPException:
        pass
    try:
        await db.health_risk_records.insert_one({
            "locationId": loc["id"], "locationName": loc["name"],
            "riskScore": result["riskScore"], "riskLevel": result["riskLevel"],
            "aqi": snap["aqi"], "userId": uid,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        pass
    return result


@api.post("/exposure")
async def exposure(body: ExposureInput):
    return health_risk.exposure_guidance(body.aqi, body.environment, body.activity, body.duration)


# ---------------------------------------------------------------------------
# Map / globe
# ---------------------------------------------------------------------------
@api.get("/map")
async def map_data():
    return {"locations": aqi_data.map_overview(), "scale": aqi_data.AQI_CATEGORIES}


# ---------------------------------------------------------------------------
# Saved locations & dashboard
# ---------------------------------------------------------------------------
@api.get("/users/locations")
async def list_locations(user: dict = Depends(get_current_user)):
    docs = await db.saved_locations.find({"userId": str(user["_id"])}).to_list(100)
    out = []
    for d in docs:
        out.append({
            "id": str(d["_id"]), "locationId": d["locationId"], "name": d["name"],
            "country": d.get("country", ""), "lat": d["lat"], "lon": d["lon"],
            "label": d.get("label", ""),
        })
    return {"locations": out}


@api.post("/users/locations")
async def add_location(body: SavedLocationInput, user: dict = Depends(get_current_user)):
    uid = str(user["_id"])
    existing = await db.saved_locations.find_one({"userId": uid, "locationId": body.locationId})
    if existing:
        raise HTTPException(status_code=400, detail="Location already saved.")
    doc = body.model_dump()
    doc["userId"] = uid
    doc["createdAt"] = datetime.now(timezone.utc).isoformat()
    res = await db.saved_locations.insert_one(doc)
    return {"id": str(res.inserted_id), **body.model_dump()}


@api.delete("/users/locations/{loc_id}")
async def delete_location(loc_id: str, user: dict = Depends(get_current_user)):
    res = await db.saved_locations.delete_one({"_id": ObjectId(loc_id), "userId": str(user["_id"])})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Location not found.")
    return {"ok": True}


@api.get("/users/dashboard")
async def dashboard(user: dict = Depends(get_current_user)):
    uid = str(user["_id"])
    saved = await db.saved_locations.find({"userId": uid}).to_list(100)
    locations = []
    for d in saved:
        loc = aqi_data.find_by_id(d["locationId"]) or aqi_data.make_custom_location(d["lat"], d["lon"], d["name"])
        snap = aqi_data.current_snapshot(loc)
        risk = health_risk.assess(snap["aqi"], snap["pollutants"])
        locations.append({
            "id": str(d["_id"]), "locationId": d["locationId"], "name": d["name"],
            "label": d.get("label", ""), "country": d.get("country", ""),
            "lat": d["lat"], "lon": d["lon"],
            "aqi": snap["aqi"], "category": snap["category"], "color": snap["color"],
            "riskLevel": risk["riskLevel"], "riskScore": risk["riskScore"], "riskColor": risk["riskColor"],
        })
    recent = await db.aqi_records.find({"userId": uid}).sort("createdAt", -1).limit(8).to_list(8)
    recent_out = [{"locationName": r["locationName"], "aqi": r["aqi"], "category": r["category"], "createdAt": r["createdAt"]} for r in recent]
    return {"savedLocations": locations, "recentSearches": recent_out,
            "alertThreshold": user.get("alertThreshold", 150), "alertsEnabled": user.get("alertsEnabled", True)}


# ---------------------------------------------------------------------------
# AI assistant (OxyZen AI) — streaming
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "You are OxyZen AI, a knowledgeable and responsible air-quality and environmental-health assistant. "
    "You help people understand AQI, pollutants (PM2.5, PM10, O3, NO2, SO2, CO), pollution sources, "
    "health impacts, precautions, indoor air quality, outdoor exposure, activity guidance, and general "
    "information about how particulate-filtering masks work. "
    "IMPORTANT RULES: You are NOT a doctor and must never diagnose disease or give clinical medical advice. "
    "Use careful, non-diagnostic language (e.g. 'high pollution may increase health risks, especially for "
    "sensitive individuals'). You must NOT recommend which specific mask to buy or run a mask-recommendation "
    "workflow — only explain general concepts. Keep answers concise, clear, and practical. Use plain language."
)


@api.post("/ai/chat")
async def ai_chat(body: ChatInput):
    context_note = ""
    if body.context:
        c = body.context
        parts = []
        if c.get("name"):
            parts.append(f"location: {c.get('name')}")
        if c.get("aqi") is not None:
            parts.append(f"AQI: {c.get('aqi')} ({c.get('category','')})")
        if c.get("dominantPollutant"):
            parts.append(f"dominant pollutant: {c.get('dominantPollutant')}")
        if c.get("riskLevel"):
            parts.append(f"health risk: {c.get('riskLevel')}")
        if parts:
            context_note = "\n\nCURRENT USER CONTEXT (use it when relevant): " + "; ".join(parts) + "."

    await db.chat_messages.insert_one({
        "sessionId": body.sessionId, "role": "user", "content": body.message,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    })

    async def gen():
        full = ""
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage, TextDelta, StreamDone
            chat = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=body.sessionId,
                system_message=SYSTEM_PROMPT + context_note,
            ).with_model(AI_PROVIDER, AI_MODEL)
            async for ev in chat.stream_message(UserMessage(text=body.message)):
                if isinstance(ev, TextDelta):
                    full += ev.content
                    yield ev.content
                elif isinstance(ev, StreamDone):
                    break
        except Exception as e:
            logger.error(f"AI chat error: {e}")
            fallback = ("I'm having trouble reaching the AI service right now. In the meantime: air quality is "
                        "measured on the AQI scale (0-50 Good to 301+ Hazardous). When AQI is high, limit "
                        "outdoor exertion, keep windows closed during peaks, and improve indoor filtration. "
                        "Please try again shortly.")
            full = fallback
            yield fallback
        try:
            await db.chat_messages.insert_one({
                "sessionId": body.sessionId, "role": "assistant", "content": full,
                "createdAt": datetime.now(timezone.utc).isoformat(),
            })
        except Exception:
            pass

    return StreamingResponse(gen(), media_type="text/plain",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@api.get("/ai/history/{session_id}")
async def ai_history(session_id: str):
    docs = await db.chat_messages.find({"sessionId": session_id}, {"_id": 0}).sort("createdAt", 1).to_list(200)
    return {"messages": docs}


@api.get("/")
async def root():
    return {"message": "OxyZen API", "status": "ok"}


# ---------------------------------------------------------------------------
# App wiring
# ---------------------------------------------------------------------------
app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    try:
        await db.users.create_index("email", unique=True)
        await db.saved_locations.create_index([("userId", 1), ("locationId", 1)])
        await db.aqi_records.create_index([("userId", 1), ("createdAt", -1)])
    except Exception as e:
        logger.warning(f"index creation: {e}")
    # seed admin
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@oxyzen.app")
    admin_password = os.environ.get("ADMIN_PASSWORD", "OxyZen@2026")
    existing = await db.users.find_one({"email": admin_email})
    if existing is None:
        await db.users.insert_one({
            "name": "Admin", "email": admin_email,
            "password_hash": hash_password(admin_password), "role": "admin",
            "alertThreshold": 150, "alertsEnabled": True,
            "created_at": datetime.now(timezone.utc),
        })
        logger.info("seeded admin user")
    elif not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": hash_password(admin_password)}})


@app.on_event("shutdown")
async def shutdown():
    client.close()
