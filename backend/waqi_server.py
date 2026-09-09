"""Render entrypoint that replaces AQI routes with live WAQI handlers."""
import math
from fastapi import HTTPException, Request

import server

app = server.app
MAX_STATION_DISTANCE_KM = 25.0


def _remove_route(path: str):
    app.router.routes[:] = [
        r for r in app.router.routes
        if not (getattr(r, "path", None) == path and "GET" in getattr(r, "methods", set()))
    ]


for _path in ("/api/aqi/current", "/api/aqi/history", "/api/aqi/pollutant/{pollutant}", "/api/health-risk"):
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
    p1 = math.radians(float(lat1)); p2 = math.radians(float(lat2))
    dp = math.radians(float(lat2) - float(lat1)); dl = math.radians(float(lon2) - float(lon1))
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def _station_coordinates(station_name, lat, lon):
    """Resolve the selected WAQI station to coordinates using the same WAQI
    map API, so a distant station cannot silently masquerade as a city result."""
    if not station_name:
        return None
    try:
        bounds = f"{float(lat) - 0.5},{float(lon) - 0.5},{float(lat) + 0.5},{float(lon) + 0.5}"
        stations = server.aqi_data._waqi_json("/map/bounds/", {"latlng": bounds})
        target = station_name.strip().lower()
        candidates = []
        for item in stations if isinstance(stations, list) else []:
            name = str(item.get("station") or "").strip()
            if name.lower() == target or target in name.lower() or name.lower() in target:
                try:
                    candidates.append((_distance_km(lat, lon, item["lat"], item["lon"]), float(item["lat"]), float(item["lon"])))
                except (KeyError, TypeError, ValueError):
                    continue
        return min(candidates, key=lambda x: x[0]) if candidates else None
    except Exception as exc:
        server.logger.warning("Could not validate WAQI station distance: %s", exc)
        return None


def _annotate_source(snap, loc):
    source = dict(snap.get("source") or {})
    station = source.get("station") or "WAQI station"
    match = _station_coordinates(station, loc["lat"], loc["lon"])
    if match:
        distance, station_lat, station_lon = match
        source["distanceKm"] = round(distance, 1)
        source["stationLat"] = station_lat
        source["stationLon"] = station_lon
        if distance > MAX_STATION_DISTANCE_KM:
            raise RuntimeError(f"WAQI station is {distance:.1f} km from {loc.get('name')}; no sufficiently close live station")
        source["matchType"] = "direct" if distance <= 5 else "nearby"
        source["dataType"] = "Direct monitoring station" if distance <= 5 else "Nearby monitoring station"
    else:
        source["matchType"] = "station"
        source["dataType"] = "Live monitoring-station data"
    snap["source"] = source
    return snap


def _live_or_502(loc):
    try:
        return _annotate_source(server.aqi_data.current_snapshot(loc), loc)
    except Exception as exc:
        server.logger.exception("WAQI request failed for %s", loc.get("name"))
        raise HTTPException(status_code=502, detail=f"Live WAQI data is temporarily unavailable for {loc.get('name') or 'this location'}.") from exc


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
    meta = server.aqi_data.POLLUTANT_META[pollutant]
    current = snap["pollutants"].get(pollutant)
    if current is None: severity = "Unavailable"
    elif current <= 50: severity = "Good"
    elif current <= 100: severity = "Moderate"
    elif current <= 150: severity = "High"
    else: severity = "Very High"
    return {"meta": meta, "current": current, "reference": 100, "severity": severity, "trend": [], "source": snap.get("source")}


@app.get("/api/health-risk")
async def get_health_risk_waqi(request: Request, locationId: str = "", lat: float | None = None, lon: float | None = None, locationName: str = "", locationCountry: str = ""):
    loc = _loc(locationId=locationId, lat=lat, lon=lon, locationName=locationName, locationCountry=locationCountry)
    snap = _live_or_502(loc)
    result = server.health_risk.assess(snap["aqi"], snap["pollutants"])
    result["location"] = {k: loc[k] for k in ("id", "name", "country")}
    result["source"] = snap.get("source")
    return result
