"""Render entrypoint that replaces AQI routes with live WAQI handlers."""
from fastapi import HTTPException, Request

import server

app = server.app


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


def _live_or_502(loc):
    try:
        return server.aqi_data.current_snapshot(loc)
    except Exception as exc:
        server.logger.exception("WAQI request failed for %s", loc.get("name"))
        raise HTTPException(
            status_code=502,
            detail=f"Live WAQI data is temporarily unavailable for {loc.get('name') or 'this location'}.",
        ) from exc


@app.get("/api/aqi/current")
async def aqi_current_waqi(
    request: Request,
    locationId: str = "",
    lat: float | None = None,
    lon: float | None = None,
    locationName: str = "",
    locationCountry: str = "",
):
    loc = _loc(
        locationId=locationId,
        lat=lat,
        lon=lon,
        locationName=locationName,
        locationCountry=locationCountry,
    )
    snap = _live_or_502(loc)
    snap["scale"] = server.aqi_data.AQI_CATEGORIES
    snap["pollutantMeta"] = server.aqi_data.POLLUTANT_META
    return snap


@app.get("/api/aqi/history")
async def aqi_history_waqi(
    locationId: str = "",
    lat: float | None = None,
    lon: float | None = None,
    range: str = "24h",
    locationName: str = "",
    locationCountry: str = "",
):
    loc = _loc(
        locationId=locationId,
        lat=lat,
        lon=lon,
        locationName=locationName,
        locationCountry=locationCountry,
    )
    if range not in ("24h", "7d", "30d"):
        range = "24h"
    return {
        "range": range,
        "available": False,
        "points": [],
        "message": "Historical AQI data is unavailable from the live WAQI API.",
        "location": {k: loc[k] for k in ("id", "name", "country")},
    }


@app.get("/api/aqi/pollutant/{pollutant}")
async def pollutant_detail_waqi(
    pollutant: str,
    locationId: str = "",
    lat: float | None = None,
    lon: float | None = None,
    locationName: str = "",
    locationCountry: str = "",
):
    if pollutant not in server.aqi_data.POLLUTANT_META:
        raise HTTPException(status_code=404, detail="Unknown pollutant")
    loc = _loc(
        locationId=locationId,
        lat=lat,
        lon=lon,
        locationName=locationName,
        locationCountry=locationCountry,
    )
    snap = _live_or_502(loc)
    meta = server.aqi_data.POLLUTANT_META[pollutant]
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
        "meta": meta,
        "current": current,
        "reference": 100,
        "severity": severity,
        "trend": [],
        "source": snap.get("source"),
    }


@app.get("/api/health-risk")
async def get_health_risk_waqi(
    request: Request,
    locationId: str = "",
    lat: float | None = None,
    lon: float | None = None,
    locationName: str = "",
    locationCountry: str = "",
):
    loc = _loc(
        locationId=locationId,
        lat=lat,
        lon=lon,
        locationName=locationName,
        locationCountry=locationCountry,
    )
    snap = _live_or_502(loc)
    result = server.health_risk.assess(snap["aqi"], snap["pollutants"])
    result["location"] = {k: loc[k] for k in ("id", "name", "country")}
    result["source"] = snap.get("source")
    return result
