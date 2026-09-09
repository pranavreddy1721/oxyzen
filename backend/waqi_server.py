"""Render entrypoint for live WAQI data with strict station-location validation."""
import math
from datetime import datetime, timezone
from fastapi import HTTPException, Request

import server

app = server.app
MAX_STATION_DISTANCE_KM = 25.0


def _remove_route(path: str):
    app.router.routes[:] = [
        r for r in app.router.routes
        if not (getattr(r, "path", None) == path and "GET" in getattr(r, "methods", set()))
    ]


for _path in (
    "/api/aqi/current",
    "/api/aqi/history",
    "/api/aqi/pollutant/{pollutant}",
    "/api/health-risk",
    "/api/aqi/forecast",
):
    _remove_route(_path)


def _loc(**kwargs):
    return server._resolve_location(
        kwargs.get("locationId", ""),
        kwargs.get("lat"),
        kwargs.get("lon"),
        kwargs.get("locationName", ""),
        kwargs.get("locationCountry", ""),
    )


def _distance_km(lat1, lon1, lat2, lon2):
    radius = 6371.0
    p1 = math.radians(float(lat1))
    p2 = math.radians(float(lat2))
    dp = math.radians(float(lat2) - float(lat1))
    dl = math.radians(float(lon2) - float(lon1))
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def _usable_aqi(data):
    raw = (data or {}).get("aqi")
    try:
        int(str(raw).strip())
        return True
    except (TypeError, ValueError):
        return False


def _nearest_live_station(loc):
    """Choose only a WAQI station physically within 25 km of the selected point."""
    lat = float(loc["lat"])
    lon = float(loc["lon"])
    bounds = f"{lat - 0.5},{lon - 0.5},{lat + 0.5},{lon + 0.5}"
    stations = server.aqi_data._waqi_json("/map/bounds/", {"latlng": bounds})
    candidates = []

    for item in stations if isinstance(stations, list) else []:
        uid = item.get("uid")
        try:
            slat = float(item.get("lat"))
            slon = float(item.get("lon"))
            if uid is None:
                continue
            distance = _distance_km(lat, lon, slat, slon)
            if distance <= MAX_STATION_DISTANCE_KM:
                candidates.append((distance, str(uid), slat, slon, item.get("station") or "WAQI station"))
        except (TypeError, ValueError):
            continue

    candidates.sort(key=lambda x: x[0])
    last_error = None
    for distance, uid, slat, slon, station_name in candidates:
        try:
            data = server.aqi_data._waqi_json(f"/feed/@{uid}/")
            if _usable_aqi(data):
                return data, distance, slat, slon, station_name
        except Exception as exc:
            last_error = exc
            server.logger.warning("WAQI nearby station %s failed: %s", uid, exc)

    if candidates and last_error:
        raise RuntimeError("Nearby WAQI stations had no usable live AQI") from last_error
    raise RuntimeError(f"No WAQI monitoring station within {MAX_STATION_DISTANCE_KM:.0f} km of {loc.get('name') or 'this location'}")


def _snapshot(loc):
    data, distance, station_lat, station_lon, map_station_name = _nearest_live_station(loc)
    raw = data.get("aqi")
    aqi = max(0, min(500, int(str(raw).strip())))
    sub = server.aqi_data._subindices(data)
    cat = server.aqi_data.category_for_aqi(aqi)
    provider_updated = ((data.get("time") or {}).get("iso") or (data.get("time") or {}).get("s"))
    updated = provider_updated or datetime.now(timezone.utc).isoformat()

    source = server.aqi_data._source(data)
    source.update({
        "station": source.get("station") or map_station_name,
        "stationLat": station_lat,
        "stationLon": station_lon,
        "distanceKm": round(distance, 1),
        "matchType": "direct" if distance <= 5 else "nearby",
        "dataType": "Direct monitoring station" if distance <= 5 else "Nearby monitoring station",
    })

    return {
        "location": {
            "id": loc["id"],
            "name": loc["name"],
            "country": loc.get("country", ""),
            "lat": float(loc["lat"]),
            "lon": float(loc["lon"]),
        },
        "aqi": aqi,
        "category": cat["label"],
        "categoryKey": cat["key"],
        "color": cat["color"],
        "dominantPollutant": data.get("dominentpol"),
        "pollutants": sub,
        "pollutantSubIndices": sub,
        "updatedAt": updated,
        "providerUpdatedAt": provider_updated,
        "source": source,
    }, data


def _live_or_502(loc):
    try:
        snap, _ = _snapshot(loc)
        return snap
    except Exception as exc:
        server.logger.exception("WAQI request failed for %s", loc.get("name"))
        raise HTTPException(
            status_code=502,
            detail=f"Live WAQI data is temporarily unavailable for {loc.get('name') or 'this location'}.",
        ) from exc


@app.get("/api/aqi/current")
async def aqi_current_waqi(request: Request, locationId: str = "", lat: float | None = None, lon: float | None = None, locationName: str = "", locationCountry: str = ""):
    loc = _loc(locationId=locationId, lat=lat, lon=lon, locationName=locationName, locationCountry=locationCountry)
    snap = _live_or_502(loc)
    snap["scale"] = server.aqi_data.AQI_CATEGORIES
    snap["pollutantMeta"] = server.aqi_data.POLLUTANT_META
    return snap


@app.get("/api/aqi/pollutant/{pollutant}")
async def pollutant_detail_waqi(pollutant: str, locationId: str = "", lat: float | None = None, lon: float | None = None, locationName: str = "", locationCountry: str = ""):
    if pollutant not in server.aqi_data.POLLUTANT_META:
        raise HTTPException(status_code=404, detail="Unknown pollutant")
    loc = _loc(locationId=locationId, lat=lat, lon=lon, locationName=locationName, locationCountry=locationCountry)
    snap = _live_or_502(loc)
    current = snap["pollutants"].get(pollutant)
    if current is None:
        severity = "Unavailable"
    elif current <= 50:
        severity = "Good"
    elif current <= 100:
        severity = "Moderate"
    elif current <= 150:
        severity = "High"
    else:
        severity = "Very High"
    return {
        "meta": server.aqi_data.POLLUTANT_META[pollutant],
        "current": current,
        "reference": 100,
        "severity": severity,
        "trend": [],
        "source": snap.get("source"),
    }


@app.get("/api/health-risk")
async def get_health_risk_waqi(request: Request, locationId: str = "", lat: float | None = None, lon: float | None = None, locationName: str = "", locationCountry: str = ""):
    loc = _loc(locationId=locationId, lat=lat, lon=lon, locationName=locationName, locationCountry=locationCountry)
    snap = _live_or_502(loc)
    result = server.health_risk.assess(snap["aqi"], snap["pollutants"])
    result["location"] = {k: loc[k] for k in ("id", "name", "country")}
    result["source"] = snap.get("source")
    return result


@app.get("/api/aqi/forecast")
async def aqi_forecast_waqi(request: Request, locationId: str = "", lat: float | None = None, lon: float | None = None, locationName: str = "", locationCountry: str = "", days: int = 5):
    loc = _loc(locationId=locationId, lat=lat, lon=lon, locationName=locationName, locationCountry=locationCountry)
    try:
        _, data = _snapshot(loc)
        daily = (data.get("forecast") or {}).get("daily") or {}
        dates = {}
        for pollutant, items in daily.items():
            if pollutant not in server.aqi_data.POLLUTANT_META:
                continue
            for item in items or []:
                day = item.get("day")
                avg = item.get("avg")
                if day is not None and isinstance(avg, (int, float)):
                    dates.setdefault(day, []).append(float(avg))
        rows = []
        for day, values in sorted(dates.items())[:max(1, min(7, int(days)))]:
            aqi = int(round(max(values)))
            cat = server.aqi_data.category_for_aqi(aqi)
            rows.append({
                "t": day,
                "label": day,
                "aqi": aqi,
                "category": cat["label"],
                "categoryKey": cat["key"],
                "color": cat["color"],
                "dominantPollutant": None,
                "trend": "stable",
                "derived": True,
                "source": {"provider": "World Air Quality Index (WAQI)", "providerUrl": "https://waqi.info/"},
            })
        return {"forecast": rows}
    except Exception as exc:
        server.logger.exception("WAQI forecast failed for %s", loc.get("name"))
        return {"forecast": []}
