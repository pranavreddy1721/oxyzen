"""OxyZen AQI data engine: deterministic simulated air-quality data.

The data is generated deterministically from a location key + date so results are
stable within a day but vary realistically by location and time. This module is
isolated so a real provider (e.g. OpenWeather) can replace it without touching routes.
"""
import hashlib
import math
import logging
import time
from datetime import datetime, timezone, timedelta

import requests

# ---------------------------------------------------------------------------
# Static reference data
# ---------------------------------------------------------------------------

# Curated location catalogue. base = baseline pollution factor (0.1 clean .. 1.0 severe)
CITIES = [
    {"id": "delhi",        "name": "Delhi",          "country": "India",          "lat": 28.6139, "lon": 77.2090, "base": 0.92},
    {"id": "mumbai",       "name": "Mumbai",         "country": "India",          "lat": 19.0760, "lon": 72.8777, "base": 0.62},
    {"id": "kolhapur",     "name": "Kolhapur",       "country": "India",          "lat": 16.7050, "lon": 74.2433, "base": 0.40},
    {"id": "pune",         "name": "Pune",           "country": "India",          "lat": 18.5204, "lon": 73.8567, "base": 0.48},
    {"id": "bengaluru",    "name": "Bengaluru",      "country": "India",          "lat": 12.9716, "lon": 77.5946, "base": 0.44},
    {"id": "kolkata",      "name": "Kolkata",        "country": "India",          "lat": 22.5726, "lon": 88.3639, "base": 0.70},
    {"id": "beijing",      "name": "Beijing",        "country": "China",          "lat": 39.9042, "lon": 116.4074, "base": 0.80},
    {"id": "shanghai",     "name": "Shanghai",       "country": "China",          "lat": 31.2304, "lon": 121.4737, "base": 0.58},
    {"id": "lahore",       "name": "Lahore",         "country": "Pakistan",       "lat": 31.5204, "lon": 74.3587, "base": 0.90},
    {"id": "dhaka",        "name": "Dhaka",          "country": "Bangladesh",     "lat": 23.8103, "lon": 90.4125, "base": 0.85},
    {"id": "london",       "name": "London",         "country": "United Kingdom", "lat": 51.5074, "lon": -0.1278, "base": 0.30},
    {"id": "paris",        "name": "Paris",          "country": "France",         "lat": 48.8566, "lon": 2.3522, "base": 0.34},
    {"id": "newyork",      "name": "New York",       "country": "United States",  "lat": 40.7128, "lon": -74.0060, "base": 0.28},
    {"id": "losangeles",   "name": "Los Angeles",    "country": "United States",  "lat": 34.0522, "lon": -118.2437, "base": 0.42},
    {"id": "tokyo",        "name": "Tokyo",          "country": "Japan",          "lat": 35.6762, "lon": 139.6503, "base": 0.33},
    {"id": "seoul",        "name": "Seoul",          "country": "South Korea",    "lat": 37.5665, "lon": 126.9780, "base": 0.50},
    {"id": "sydney",       "name": "Sydney",         "country": "Australia",      "lat": -33.8688, "lon": 151.2093, "base": 0.18},
    {"id": "zurich",       "name": "Zurich",         "country": "Switzerland",    "lat": 47.3769, "lon": 8.5417, "base": 0.14},
    {"id": "cairo",        "name": "Cairo",          "country": "Egypt",          "lat": 30.0444, "lon": 31.2357, "base": 0.78},
    {"id": "saopaulo",     "name": "São Paulo",      "country": "Brazil",         "lat": -23.5505, "lon": -46.6333, "base": 0.46},
    {"id": "mexicocity",   "name": "Mexico City",    "country": "Mexico",         "lat": 19.4326, "lon": -99.1332, "base": 0.55},
    {"id": "dubai",        "name": "Dubai",          "country": "UAE",            "lat": 25.2048, "lon": 55.2708, "base": 0.52},
    {"id": "singapore",    "name": "Singapore",      "country": "Singapore",      "lat": 1.3521, "lon": 103.8198, "base": 0.36},
    {"id": "reykjavik",    "name": "Reykjavik",      "country": "Iceland",        "lat": 64.1466, "lon": -21.9426, "base": 0.08},
]

POLLUTANT_META = {
    "pm25": {
        "key": "pm25", "name": "PM2.5", "unit": "µg/m³",
        "reference": 15,  # WHO 24h guideline
        "full_name": "Fine Particulate Matter",
        "short": "Fine particles that can penetrate deep into the respiratory system and bloodstream.",
        "what": "PM2.5 refers to airborne particles 2.5 micrometers or smaller — about 30x thinner than a human hair. Because of their tiny size they bypass the body's natural defenses.",
        "sources": ["Vehicle exhaust", "Industrial combustion", "Wildfires & biomass burning", "Construction dust"],
        "effects": ["Deep respiratory penetration", "Aggravated asthma", "Reduced lung function", "Cardiovascular stress with prolonged exposure"],
        "precautions": ["Limit prolonged outdoor exertion when elevated", "Use good indoor filtration", "Keep windows closed during peaks"],
    },
    "pm10": {
        "key": "pm10", "name": "PM10", "unit": "µg/m³",
        "reference": 45,
        "full_name": "Coarse Particulate Matter",
        "short": "Coarse inhalable particles from dust, pollen and combustion.",
        "what": "PM10 are inhalable particles 10 micrometers or smaller. They settle in the upper airways and can irritate the nose, throat and lungs.",
        "sources": ["Road & construction dust", "Agricultural activity", "Pollen and mold", "Industrial processes"],
        "effects": ["Airway irritation", "Coughing and throat discomfort", "Aggravated respiratory conditions"],
        "precautions": ["Reduce outdoor time in dusty conditions", "Wear a well-fitted mask outdoors when high"],
    },
    "o3": {
        "key": "o3", "name": "O₃", "unit": "µg/m³",
        "reference": 100,
        "full_name": "Ground-level Ozone",
        "short": "A reactive gas formed by sunlight acting on pollutants; peaks on hot afternoons.",
        "what": "Ground-level ozone is not emitted directly but forms when sunlight reacts with nitrogen oxides and volatile organic compounds. It is a key component of smog.",
        "sources": ["Vehicle & industrial emissions in sunlight", "Chemical solvents", "Hot, stagnant weather"],
        "effects": ["Airway inflammation", "Chest tightness", "Reduced lung function during exercise"],
        "precautions": ["Avoid intense outdoor exercise on hot afternoons", "Schedule activity for early morning"],
    },
    "no2": {
        "key": "no2", "name": "NO₂", "unit": "µg/m³",
        "reference": 25,
        "full_name": "Nitrogen Dioxide",
        "short": "A traffic-related gas that irritates airways and contributes to smog.",
        "what": "Nitrogen dioxide is a reddish-brown gas produced mainly by combustion in vehicles and power plants. It is a marker of traffic-related pollution.",
        "sources": ["Vehicle engines", "Power generation", "Gas stoves & heaters"],
        "effects": ["Airway irritation", "Increased respiratory infections", "Asthma aggravation"],
        "precautions": ["Avoid busy roadsides during rush hour", "Ventilate when using gas appliances"],
    },
    "so2": {
        "key": "so2", "name": "SO₂", "unit": "µg/m³",
        "reference": 40,
        "full_name": "Sulfur Dioxide",
        "short": "A sharp-smelling gas from fossil-fuel burning that irritates the respiratory tract.",
        "what": "Sulfur dioxide is produced when fuels containing sulfur are burned. It can react to form fine particles and contributes to acid rain.",
        "sources": ["Coal & oil combustion", "Metal smelting", "Industrial facilities"],
        "effects": ["Throat and airway irritation", "Breathing difficulty", "Aggravated asthma"],
        "precautions": ["Limit exposure near industrial areas when elevated"],
    },
    "co": {
        "key": "co", "name": "CO", "unit": "mg/m³",
        "reference": 4,
        "full_name": "Carbon Monoxide",
        "short": "A colorless, odorless gas from incomplete combustion that reduces oxygen delivery.",
        "what": "Carbon monoxide binds to hemoglobin more readily than oxygen, reducing the blood's oxygen-carrying capacity. Outdoor levels are usually low but rise near heavy traffic.",
        "sources": ["Vehicle exhaust", "Incomplete combustion", "Industrial processes"],
        "effects": ["Reduced oxygen delivery", "Headache & fatigue at higher levels", "Cardiovascular strain"],
        "precautions": ["Avoid congested traffic in poorly ventilated areas", "Never run engines in closed spaces"],
    },
}

# US EPA AQI breakpoints for PM2.5 (µg/m³, 24h)
PM25_BREAKPOINTS = [
    (0.0, 12.0, 0, 50),
    (12.1, 35.4, 51, 100),
    (35.5, 55.4, 101, 150),
    (55.5, 150.4, 151, 200),
    (150.5, 250.4, 201, 300),
    (250.5, 350.4, 301, 400),
    (350.5, 500.4, 401, 500),
]

AQI_CATEGORIES = [
    {"min": 0,   "max": 50,  "label": "Good",                            "key": "good",         "color": "#10B981"},
    {"min": 51,  "max": 100, "label": "Moderate",                        "key": "moderate",     "color": "#F59E0B"},
    {"min": 101, "max": 150, "label": "Unhealthy for Sensitive Groups",  "key": "sensitive",    "color": "#F97316"},
    {"min": 151, "max": 200, "label": "Unhealthy",                       "key": "unhealthy",    "color": "#EF4444"},
    {"min": 201, "max": 300, "label": "Very Unhealthy",                  "key": "veryUnhealthy","color": "#9333EA"},
    {"min": 301, "max": 500, "label": "Hazardous",                       "key": "hazardous",    "color": "#9F1239"},
]


# ---------------------------------------------------------------------------
# Deterministic pseudo-random helpers
# ---------------------------------------------------------------------------

def _hash_float(*parts) -> float:
    """Return a stable float in [0,1) from arbitrary parts."""
    s = "|".join(str(p) for p in parts)
    h = hashlib.sha256(s.encode()).hexdigest()
    return int(h[:12], 16) / float(16 ** 12)


def category_for_aqi(aqi: int) -> dict:
    for c in AQI_CATEGORIES:
        if c["min"] <= aqi <= c["max"]:
            return c
    return AQI_CATEGORIES[-1]


def aqi_from_pm25(pm25: float) -> int:
    for c_lo, c_hi, i_lo, i_hi in PM25_BREAKPOINTS:
        if c_lo <= pm25 <= c_hi:
            aqi = (i_hi - i_lo) / (c_hi - c_lo) * (pm25 - c_lo) + i_lo
            return int(round(aqi))
    return 500


def _severity_at(base: float, seed) -> float:
    """Combine baseline pollution with a stable per-seed variation -> 0..1.2."""
    variation = (_hash_float(seed, "v") - 0.5) * 0.4  # +/-0.2
    return max(0.04, min(1.25, base + variation))


def _pollutants_from_severity(sev: float, seed) -> dict:
    """Derive the six pollutant concentrations from a severity factor."""
    def jitter(name, spread):
        return 1.0 + (_hash_float(seed, name) - 0.5) * spread

    pm25 = round(4 + sev * 190 * jitter("pm25", 0.25), 1)
    pm10 = round(pm25 * (1.4 + _hash_float(seed, "pmr") * 0.6), 1)
    o3 = round(15 + (1.15 - sev) * 90 * jitter("o3", 0.5) + sev * 40, 1)  # ozone partly inverse
    no2 = round(6 + sev * 70 * jitter("no2", 0.4), 1)
    so2 = round(3 + sev * 55 * jitter("so2", 0.5), 1)
    co = round(0.3 + sev * 6.5 * jitter("co", 0.4), 2)
    return {"pm25": pm25, "pm10": pm10, "o3": o3, "no2": no2, "so2": so2, "co": co}


def _diurnal_factor(hour: int) -> float:
    """Traffic-style daily curve: peaks morning (8) and evening (19)."""
    return 1.0 + 0.28 * (math.exp(-((hour - 8) ** 2) / 8) + math.exp(-((hour - 19) ** 2) / 8))


# ---------------------------------------------------------------------------
# Location helpers
# ---------------------------------------------------------------------------

logger = logging.getLogger("oxyzen.aqi_data")
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
_GEOCODE_CACHE = {}
_GEOCODE_CACHE_TTL = 600  # 10 minutes
_EXTERNAL_LOCATIONS = {}


def _location_id_from_geocoder(item: dict) -> str:
    return f"geo_{item.get('id')}"


def _external_location(item: dict) -> dict:
    loc = {
        "id": _location_id_from_geocoder(item),
        "name": item.get("name") or "Unknown location",
        "country": item.get("country") or "",
        "admin1": item.get("admin1") or "",
        "lat": float(item["latitude"]),
        "lon": float(item["longitude"]),
        # Deterministic baseline keeps OxyZen's existing simulated AQI engine stable.
        "base": 0.25 + _hash_float(round(float(item["latitude"]), 1), round(float(item["longitude"]), 1)) * 0.6,
    }
    _EXTERNAL_LOCATIONS[loc["id"]] = loc
    return loc


def _search_open_meteo(q: str, limit: int) -> list:
    """Search the global Open-Meteo geocoding catalogue.

    Open-Meteo supports global place-name search and returns WGS84 coordinates,
    country and administrative-area information without requiring an API key for
    normal non-commercial use. Results are cached briefly to avoid repeated calls
    while the user types.
    """
    normalized = q.strip().lower()
    if len(normalized) < 2:
        return []

    now = time.monotonic()
    cached = _GEOCODE_CACHE.get(normalized)
    if cached and now - cached[0] < _GEOCODE_CACHE_TTL:
        return cached[1][:limit]

    try:
        response = requests.get(
            GEOCODING_URL,
            params={"name": q.strip(), "count": min(max(limit, 1), 20), "language": "en", "format": "json"},
            timeout=4,
        )
        response.raise_for_status()
        payload = response.json()
        results = [_external_location(item) for item in (payload.get("results") or [])]
        _GEOCODE_CACHE[normalized] = (now, results)
        return results[:limit]
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        logger.warning("Global location search failed for %r: %s", q, exc)
        return []


def _same_location(a: dict, b: dict) -> bool:
    return (
        a.get("name", "").strip().lower() == b.get("name", "").strip().lower()
        and a.get("country", "").strip().lower() == b.get("country", "").strip().lower()
    ) or (
        abs(float(a.get("lat", 0)) - float(b.get("lat", 0))) < 0.01
        and abs(float(a.get("lon", 0)) - float(b.get("lon", 0))) < 0.01
    )


def search_locations(q: str, limit: int = 8):
    q = (q or "").strip()
    limit = min(max(int(limit or 8), 1), 20)
    if not q:
        return CITIES[:limit]

    # Keep the original curated catalogue fast, then enrich it with global results.
    local = []
    needle = q.lower()
    for c in CITIES:
        hay = f"{c['name']} {c['country']}".lower()
        if needle in hay:
            score = 0 if hay.startswith(needle) or c["name"].lower().startswith(needle) else 1
            local.append((score, c))
    local.sort(key=lambda x: x[0])

    merged = [c for _, c in local]
    for external in _search_open_meteo(q, limit):
        if not any(_same_location(external, existing) for existing in merged):
            merged.append(external)
        if len(merged) >= limit:
            break
    return merged[:limit]


def find_by_id(loc_id: str):
    for c in CITIES:
        if c["id"] == loc_id:
            return c
    return _EXTERNAL_LOCATIONS.get(loc_id)


def nearest_location(lat: float, lon: float):
    best, best_d = None, 1e18
    for c in CITIES:
        d = (c["lat"] - lat) ** 2 + (c["lon"] - lon) ** 2
        if d < best_d:
            best, best_d = c, d
    return best


def make_custom_location(lat: float, lon: float, name: str = None, country: str = ""):
    """Build a location dict for arbitrary coordinates (used for geolocation)."""
    base = 0.25 + _hash_float(round(lat, 1), round(lon, 1)) * 0.6
    return {
        "id": f"coord_{round(lat,3)}_{round(lon,3)}",
        "name": name or f"{round(lat,3)}, {round(lon,3)}",
        "country": country or "",
        "lat": lat, "lon": lon, "base": base,
    }


# ---------------------------------------------------------------------------
# Public data builders
# ---------------------------------------------------------------------------

def current_snapshot(loc: dict) -> dict:
    now = datetime.now(timezone.utc)
    day_seed = f"{loc['id']}-{now.strftime('%Y-%m-%d')}"
    sev = _severity_at(loc["base"], day_seed)
    hour_factor = _diurnal_factor(now.hour)
    hour_seed = f"{day_seed}-{now.hour}"
    sev_h = min(1.3, sev * hour_factor * 0.55 + sev * 0.45)
    pollutants = _pollutants_from_severity(sev_h, hour_seed)
    aqi = aqi_from_pm25(pollutants["pm25"])
    # ozone-driven bump for sunny low-particulate places
    aqi = max(aqi, int(pollutants["o3"] / 2.0))
    aqi = min(aqi, 500)
    cat = category_for_aqi(aqi)
    dominant = _dominant_pollutant(pollutants)
    return {
        "location": {k: loc[k] for k in ("id", "name", "country", "lat", "lon")},
        "aqi": aqi,
        "category": cat["label"],
        "categoryKey": cat["key"],
        "color": cat["color"],
        "dominantPollutant": dominant,
        "pollutants": pollutants,
        "updatedAt": now.isoformat(),
    }


def _dominant_pollutant(pollutants: dict) -> str:
    ratios = {k: pollutants[k] / POLLUTANT_META[k]["reference"] for k in pollutants}
    return max(ratios, key=ratios.get)


def history(loc: dict, kind: str = "24h"):
    """kind: '24h' -> hourly points; '7d'/'30d' -> daily points."""
    now = datetime.now(timezone.utc)
    points = []
    if kind == "24h":
        for i in range(23, -1, -1):
            t = now - timedelta(hours=i)
            day_seed = f"{loc['id']}-{t.strftime('%Y-%m-%d')}"
            sev = _severity_at(loc["base"], day_seed)
            sev_h = min(1.3, sev * _diurnal_factor(t.hour) * 0.55 + sev * 0.45)
            p = _pollutants_from_severity(sev_h, f"{day_seed}-{t.hour}")
            aqi = min(500, max(aqi_from_pm25(p["pm25"]), int(p["o3"] / 2.0)))
            points.append({"t": t.isoformat(), "label": t.strftime("%H:%M"), "aqi": aqi, **p})
    else:
        days = 7 if kind == "7d" else 30
        for i in range(days - 1, -1, -1):
            t = now - timedelta(days=i)
            day_seed = f"{loc['id']}-{t.strftime('%Y-%m-%d')}"
            sev = _severity_at(loc["base"], day_seed)
            # daily average uses midday-ish factor
            p = _pollutants_from_severity(min(1.3, sev), f"{day_seed}-avg")
            aqi = min(500, max(aqi_from_pm25(p["pm25"]), int(p["o3"] / 2.0)))
            points.append({"t": t.isoformat(), "label": t.strftime("%b %d"), "aqi": aqi, **p})
    return points


def forecast(loc: dict, days: int = 5):
    now = datetime.now(timezone.utc)
    out = []
    for i in range(days):
        t = now + timedelta(days=i)
        day_seed = f"{loc['id']}-fc-{t.strftime('%Y-%m-%d')}"
        sev = _severity_at(loc["base"], day_seed)
        p = _pollutants_from_severity(min(1.3, sev), f"{day_seed}-avg")
        aqi = min(500, max(aqi_from_pm25(p["pm25"]), int(p["o3"] / 2.0)))
        cat = category_for_aqi(aqi)
        label = "Today" if i == 0 else ("Tomorrow" if i == 1 else t.strftime("%a, %b %d"))
        out.append({
            "t": t.isoformat(), "label": label, "aqi": aqi,
            "category": cat["label"], "categoryKey": cat["key"], "color": cat["color"],
            "dominantPollutant": _dominant_pollutant(p),
        })
    # trend + guidance
    for i in range(len(out)):
        if i == 0:
            out[i]["trend"] = "stable"
        else:
            d = out[i]["aqi"] - out[i - 1]["aqi"]
            out[i]["trend"] = "worsening" if d > 8 else ("improving" if d < -8 else "stable")
    return out


def map_overview():
    """Snapshot for all catalogue cities, for the pollution map & globe."""
    out = []
    for c in CITIES:
        snap = current_snapshot(c)
        out.append({
            "id": c["id"], "name": c["name"], "country": c["country"],
            "lat": c["lat"], "lon": c["lon"],
            "aqi": snap["aqi"], "category": snap["category"], "categoryKey": snap["categoryKey"],
            "color": snap["color"], "dominantPollutant": snap["dominantPollutant"],
            "pm25": snap["pollutants"]["pm25"],
        })
    return out
