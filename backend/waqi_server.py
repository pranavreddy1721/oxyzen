"""Render entrypoint for live WAQI AQI routes."""
import math
from datetime import datetime, timezone
from fastapi import HTTPException, Request
import server

app = server.app
MAX_STATION_DISTANCE_KM = 75.0


def _remove_route(path):
    app.router.routes[:] = [
        r for r in app.router.routes
        if not (getattr(r, "path", None) == path and "GET" in getattr(r, "methods", set()))
    ]

for path in ("/api/aqi/current", "/api/aqi/history", "/api/aqi/pollutant/{pollutant}", "/api/health-risk", "/api/aqi/forecast"):
    _remove_route(path)


def _loc(**kwargs):
    return server._resolve_location(
        kwargs.get("locationId", ""), kwargs.get("lat"), kwargs.get("lon"),
        kwargs.get("locationName", ""), kwargs.get("locationCountry", "")
    )


def _distance_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(float(lat1)), math.radians(float(lat2))
    dp = math.radians(float(lat2) - float(lat1))
    dl = math.radians(float(lon2) - float(lon1))
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _usable(data):
    try:
        int(str((data or {}).get("aqi")).strip())
        return True
    except (TypeError, ValueError):
        return False


def _geo_coordinates(data):
    """WAQI city.geo is [latitude, longitude]."""
    geo = ((data or {}).get("city") or {}).get("geo") or []
    if len(geo) < 2:
        return None
    try:
        return float(geo[0]), float(geo[1])
    except (TypeError, ValueError):
        return None


def _try_geo(loc):
    lat, lon = float(loc["lat"]), float(loc["lon"])
    try:
        data = server.aqi_data._waqi_json(f"/feed/geo:{lat};{lon}/")
        if not _usable(data):
            return None
        coords = _geo_coordinates(data)
        if not coords:
            # Some WAQI responses do not expose station coordinates. The geo
            # endpoint itself is still a location-constrained response, so use
            # the selected point only as a last-resort source coordinate.
            return data, 0.0, lat, lon
        slat, slon = coords
        distance = _distance_km(lat, lon, slat, slon)
        if distance > MAX_STATION_DISTANCE_KM:
            server.logger.warning(
                "Rejected WAQI geo station %s: %.1f km from %s",
                ((data.get("city") or {}).get("name")), distance, loc.get("name")
            )
            return None
        return data, distance, slat, slon
    except Exception as exc:
        server.logger.warning("WAQI geo lookup failed for %s: %s", loc.get("name"), exc)
        return None


def _try_map(loc):
    lat, lon = float(loc["lat"]), float(loc["lon"])
    bounds = f"{lat - 0.5},{lon - 0.5},{lat + 0.5},{lon + 0.5}"
    try:
        stations = server.aqi_data._waqi_json("/map/bounds/", {"latlng": bounds})
    except Exception as exc:
        server.logger.warning("WAQI map lookup failed for %s: %s", loc.get("name"), exc)
        return None

    candidates = []
    for item in stations if isinstance(stations, list) else []:
        uid = item.get("uid")
        try:
            slat, slon = float(item["lat"]), float(item["lon"])
            if uid is None:
                continue
            distance = _distance_km(lat, lon, slat, slon)
            if distance <= MAX_STATION_DISTANCE_KM:
                candidates.append((distance, str(uid), slat, slon))
        except (KeyError, TypeError, ValueError):
            continue

    candidates.sort(key=lambda x: x[0])
    for distance, uid, slat, slon in candidates:
        try:
            data = server.aqi_data._waqi_json(f"/feed/@{uid}/")
            if _usable(data):
                coords = _geo_coordinates(data)
                if coords:
                    slat2, slon2 = coords
                    distance2 = _distance_km(lat, lon, slat2, slon2)
                    if distance2 > MAX_STATION_DISTANCE_KM:
                        continue
                    return data, distance2, slat2, slon2
                return data, distance, slat, slon
        except Exception as exc:
            server.logger.warning("WAQI station %s failed: %s", uid, exc)
    return None


def _snapshot(loc):
    result = _try_geo(loc) or _try_map(loc)
    if not result:
        raise RuntimeError(f"No usable WAQI station within {MAX_STATION_DISTANCE_KM:.0f} km")

    data, distance, slat, slon = result
    aqi = max(0, min(500, int(str(data["aqi"]).strip())))
    sub = server.aqi_data._subindices(data)
    cat = server.aqi_data.category_for_aqi(aqi)
    provider_updated = ((data.get("time") or {}).get("iso") or (data.get("time") or {}).get("s"))
    source = server.aqi_data._source(data)
    source.update({
        "stationLat": slat,
        "stationLon": slon,
        "distanceKm": round(distance, 1),
        "matchType": "direct" if distance <= 5 else "nearby",
        "dataType": "Direct monitoring station" if distance <= 5 else "Nearby monitoring station",
    })
    snap = {
        "location": {
            "id": loc["id"], "name": loc["name"], "country": loc.get("country", ""),
            "lat": float(loc["lat"]), "lon": float(loc["lon"])
        },
        "aqi": aqi,
        "category": cat["label"],
        "categoryKey": cat["key"],
        "color": cat["color"],
        "dominantPollutant": data.get("dominentpol"),
        "pollutants": sub,
        "pollutantSubIndices": sub,
        "updatedAt": provider_updated or datetime.now(timezone.utc).isoformat(),
        "providerUpdatedAt": provider_updated,
        "source": source,
    }
    return snap, data


def _live(loc):
    try:
        return _snapshot(loc)[0]
    except Exception as exc:
        server.logger.exception("WAQI live data failed for %s", loc.get("name"))
        raise HTTPException(
            status_code=502,
            detail=f"Live WAQI data is temporarily unavailable for {loc.get('name') or 'this location'}."
        ) from exc


@app.get("/api/aqi/current")
async def current(request: Request, locationId: str = "", lat: float | None = None, lon: float | None = None, locationName: str = "", locationCountry: str = ""):
    loc = _loc(locationId=locationId, lat=lat, lon=lon, locationName=locationName, locationCountry=locationCountry)
    snap = _live(loc)
    snap["scale"] = server.aqi_data.AQI_CATEGORIES
    snap["pollutantMeta"] = server.aqi_data.POLLUTANT_META
    return snap


@app.get("/api/aqi/pollutant/{pollutant}")
async def pollutant(pollutant: str, locationId: str = "", lat: float | None = None, lon: float | None = None, locationName: str = "", locationCountry: str = ""):
    if pollutant not in server.aqi_data.POLLUTANT_META:
        raise HTTPException(status_code=404, detail="Unknown pollutant")
    loc = _loc(locationId=locationId, lat=lat, lon=lon, locationName=locationName, locationCountry=locationCountry)
    snap = _live(loc)
    current_value = snap["pollutants"].get(pollutant)
    severity = "Unavailable" if current_value is None else "Good" if current_value <= 50 else "Moderate" if current_value <= 100 else "High" if current_value <= 150 else "Very High"
    return {"meta": server.aqi_data.POLLUTANT_META[pollutant], "current": current_value, "reference": 100, "severity": severity, "trend": [], "source": snap["source"]}


@app.get("/api/health-risk")
async def health_risk(request: Request, locationId: str = "", lat: float | None = None, lon: float | None = None, locationName: str = "", locationCountry: str = ""):
    loc = _loc(locationId=locationId, lat=lat, lon=lon, locationName=locationName, locationCountry=locationCountry)
    snap = _live(loc)
    result = server.health_risk.assess(snap["aqi"], snap["pollutants"])
    result["location"] = {k: loc[k] for k in ("id", "name", "country")}
    result["source"] = snap["source"]
    return result


@app.get("/api/aqi/forecast")
async def forecast(request: Request, locationId: str = "", lat: float | None = None, lon: float | None = None, locationName: str = "", locationCountry: str = "", days: int = 5):
    loc = _loc(locationId=locationId, lat=lat, lon=lon, locationName=locationName, locationCountry=locationCountry)
    try:
        _, data = _snapshot(loc)
        daily = (data.get("forecast") or {}).get("daily") or {}
        dates = {}
        for pollutant_name, items in daily.items():
            if pollutant_name not in server.aqi_data.POLLUTANT_META:
                continue
            for item in items or []:
                day, avg = item.get("day"), item.get("avg")
                if day is not None and isinstance(avg, (int, float)):
                    dates.setdefault(day, []).append(float(avg))
        rows = []
        for day, values in sorted(dates.items())[:max(1, min(7, int(days)))]:
            aqi = int(round(max(values)))
            cat = server.aqi_data.category_for_aqi(aqi)
            rows.append({"t": day, "label": day, "aqi": aqi, "category": cat["label"], "categoryKey": cat["key"], "color": cat["color"], "dominantPollutant": None, "trend": "stable", "derived": True, "source": {"provider": "World Air Quality Index (WAQI)", "providerUrl": "https://waqi.info/"}})
        return {"forecast": rows}
    except Exception as exc:
        server.logger.exception("WAQI forecast failed for %s", loc.get("name"))
        return {"forecast": []}
