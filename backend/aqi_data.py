"""OxyZen live AQI data adapter.

Current AQI and map data are obtained from the World Air Quality Index (WAQI)
API. WAQI pollutant values are AQI sub-indices, not raw concentrations.
Historical API data is intentionally not fabricated or archived.
"""
import logging
import time
from datetime import datetime, timezone

import requests

logger = logging.getLogger("oxyzen.aqi_data")
WAQI_BASE = "https://api.waqi.info"
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
_EXTERNAL_LOCATIONS = {}
_GEOCODE_CACHE = {}
_GEOCODE_CACHE_TTL = 600

CITIES = [
    {"id":"delhi","name":"Delhi","country":"India","lat":28.6139,"lon":77.2090},
    {"id":"mumbai","name":"Mumbai","country":"India","lat":19.0760,"lon":72.8777},
    {"id":"kolhapur","name":"Kolhapur","country":"India","lat":16.7050,"lon":74.2433},
    {"id":"pune","name":"Pune","country":"India","lat":18.5204,"lon":73.8567},
    {"id":"bengaluru","name":"Bengaluru","country":"India","lat":12.9716,"lon":77.5946},
    {"id":"kolkata","name":"Kolkata","country":"India","lat":22.5726,"lon":88.3639},
    {"id":"beijing","name":"Beijing","country":"China","lat":39.9042,"lon":116.4074},
    {"id":"shanghai","name":"Shanghai","country":"China","lat":31.2304,"lon":121.4737},
    {"id":"lahore","name":"Lahore","country":"Pakistan","lat":31.5204,"lon":74.3587},
    {"id":"dhaka","name":"Dhaka","country":"Bangladesh","lat":23.8103,"lon":90.4125},
    {"id":"london","name":"London","country":"United Kingdom","lat":51.5074,"lon":-0.1278},
    {"id":"paris","name":"Paris","country":"France","lat":48.8566,"lon":2.3522},
    {"id":"newyork","name":"New York","country":"United States","lat":40.7128,"lon":-74.0060},
    {"id":"losangeles","name":"Los Angeles","country":"United States","lat":34.0522,"lon":-118.2437},
    {"id":"tokyo","name":"Tokyo","country":"Japan","lat":35.6762,"lon":139.6503},
    {"id":"seoul","name":"Seoul","country":"South Korea","lat":37.5665,"lon":126.9780},
    {"id":"sydney","name":"Sydney","country":"Australia","lat":-33.8688,"lon":151.2093},
    {"id":"zurich","name":"Zurich","country":"Switzerland","lat":47.3769,"lon":8.5417},
    {"id":"cairo","name":"Cairo","country":"Egypt","lat":30.0444,"lon":31.2357},
    {"id":"saopaulo","name":"São Paulo","country":"Brazil","lat":-23.5505,"lon":-46.6333},
    {"id":"mexicocity","name":"Mexico City","country":"Mexico","lat":19.4326,"lon":-99.1332},
    {"id":"dubai","name":"Dubai","country":"UAE","lat":25.2048,"lon":55.2708},
    {"id":"singapore","name":"Singapore","country":"Singapore","lat":1.3521,"lon":103.8198},
    {"id":"reykjavik","name":"Reykjavik","country":"Iceland","lat":64.1466,"lon":-21.9426},
]

POLLUTANT_META = {
    "pm25":{"key":"pm25","name":"PM2.5","unit":"AQI sub-index","reference":100,"full_name":"Fine Particulate Matter","short":"WAQI pollutant AQI sub-index for fine particulate matter.","what":"This value is a WAQI pollutant AQI sub-index, not a concentration measurement.","sources":[],"effects":[],"precautions":[]},
    "pm10":{"key":"pm10","name":"PM10","unit":"AQI sub-index","reference":100,"full_name":"Coarse Particulate Matter","short":"WAQI pollutant AQI sub-index for PM10.","what":"This value is a WAQI pollutant AQI sub-index, not a concentration measurement.","sources":[],"effects":[],"precautions":[]},
    "o3":{"key":"o3","name":"O₃","unit":"AQI sub-index","reference":100,"full_name":"Ground-level Ozone","short":"WAQI pollutant AQI sub-index for ozone.","what":"This value is a WAQI pollutant AQI sub-index, not a concentration measurement.","sources":[],"effects":[],"precautions":[]},
    "no2":{"key":"no2","name":"NO₂","unit":"AQI sub-index","reference":100,"full_name":"Nitrogen Dioxide","short":"WAQI pollutant AQI sub-index for nitrogen dioxide.","what":"This value is a WAQI pollutant AQI sub-index, not a concentration measurement.","sources":[],"effects":[],"precautions":[]},
    "so2":{"key":"so2","name":"SO₂","unit":"AQI sub-index","reference":100,"full_name":"Sulfur Dioxide","short":"WAQI pollutant AQI sub-index for sulfur dioxide.","what":"This value is a WAQI pollutant AQI sub-index, not a concentration measurement.","sources":[],"effects":[],"precautions":[]},
    "co":{"key":"co","name":"CO","unit":"AQI sub-index","reference":100,"full_name":"Carbon Monoxide","short":"WAQI pollutant AQI sub-index for carbon monoxide.","what":"This value is a WAQI pollutant AQI sub-index, not a concentration measurement.","sources":[],"effects":[],"precautions":[]},
}

AQI_CATEGORIES = [
    {"min":0,"max":50,"label":"Good","key":"good","color":"#10B981"},
    {"min":51,"max":100,"label":"Moderate","key":"moderate","color":"#F59E0B"},
    {"min":101,"max":150,"label":"Unhealthy for Sensitive Groups","key":"sensitive","color":"#F97316"},
    {"min":151,"max":200,"label":"Unhealthy","key":"unhealthy","color":"#EF4444"},
    {"min":201,"max":300,"label":"Very Unhealthy","key":"veryUnhealthy","color":"#9333EA"},
    {"min":301,"max":500,"label":"Hazardous","key":"hazardous","color":"#9F1239"},
]


def category_for_aqi(aqi):
    aqi = max(0, min(500, int(aqi)))
    for c in AQI_CATEGORIES:
        if c["min"] <= aqi <= c["max"]:
            return c
    return AQI_CATEGORIES[-1]


def _external_location(item):
    loc = {"id":f"geo_{item.get('id')}","name":item.get("name") or "Unknown location","country":item.get("country") or "","admin1":item.get("admin1") or "","lat":float(item["latitude"]),"lon":float(item["longitude"])}
    _EXTERNAL_LOCATIONS[loc["id"]] = loc
    return loc


def _search_open_meteo(q, limit):
    q = (q or "").strip()
    if len(q) < 2:
        return []
    key = q.lower()
    now = time.monotonic()
    cached = _GEOCODE_CACHE.get(key)
    if cached and now - cached[0] < _GEOCODE_CACHE_TTL:
        return cached[1][:limit]
    try:
        r = requests.get(GEOCODING_URL, params={"name":q,"count":min(limit,20),"language":"en","format":"json"}, timeout=4)
        r.raise_for_status()
        results = [_external_location(x) for x in (r.json().get("results") or [])]
        _GEOCODE_CACHE[key] = (now, results)
        return results[:limit]
    except Exception as exc:
        logger.warning("location search failed: %s", exc)
        return []


def _same_location(a,b):
    return (a.get("name","").lower(),a.get("country","").lower()) == (b.get("name","").lower(),b.get("country","").lower()) or (abs(a["lat"]-b["lat"])<0.01 and abs(a["lon"]-b["lon"])<0.01)


def search_locations(q="", limit=8):
    q=(q or "").strip(); limit=min(max(int(limit or 8),1),20)
    if not q: return CITIES[:limit]
    needle=q.lower(); out=[c for c in CITIES if needle in f"{c['name']} {c['country']}".lower()]
    for x in _search_open_meteo(q,limit):
        if not any(_same_location(x,y) for y in out): out.append(x)
        if len(out)>=limit: break
    return out[:limit]


def find_by_id(loc_id):
    return next((c for c in CITIES if c["id"]==loc_id),None) or _EXTERNAL_LOCATIONS.get(loc_id)


def nearest_location(lat,lon):
    return min(CITIES,key=lambda c:(c["lat"]-lat)**2+(c["lon"]-lon)**2)


def make_custom_location(lat,lon,name=None,country=""):
    return {"id":f"coord_{round(lat,3)}_{round(lon,3)}","name":name or f"{round(lat,3)}, {round(lon,3)}","country":country or "","lat":lat,"lon":lon}


def _waqi_json(path, params=None):
    token = __import__("os").environ.get("WAQI_TOKEN", "").strip()
    if not token:
        raise RuntimeError("WAQI_TOKEN is not configured on the backend")
    p=dict(params or {}); p["token"]=token
    r=requests.get(f"{WAQI_BASE}{path}",params=p,timeout=8)
    r.raise_for_status()
    payload=r.json()
    if payload.get("status") != "ok":
        raise RuntimeError(str(payload.get("data") or "WAQI request failed"))
    return payload.get("data") or {}


def _waqi_feed(loc):
    return _waqi_json(f"/feed/geo:{loc['lat']};{loc['lon']}/")


def _subindices(data):
    iaqi=data.get("iaqi") or {}
    aliases={"pm25":"pm25","pm10":"pm10","o3":"o3","no2":"no2","so2":"so2","co":"co"}
    out={}
    for key,waqi_key in aliases.items():
        value=(iaqi.get(waqi_key) or {}).get("v")
        if isinstance(value,(int,float)):
            out[key]=round(float(value),1)
    return out


def _source(data):
    city=data.get("city") or {}
    attributions=data.get("attributions") or []
    origin=attributions[0] if attributions else {}
    return {"provider":"World Air Quality Index (WAQI)","providerUrl":"https://waqi.info/","station":city.get("name") or "WAQI station","stationUrl":city.get("url") or "","origin":origin.get("name") or "","originUrl":origin.get("url") or ""}


def current_snapshot(loc):
    data=_waqi_feed(loc)
    raw_aqi=data.get("aqi")
    if raw_aqi is None or not str(raw_aqi).lstrip("-").isdigit():
        raise RuntimeError("WAQI returned no usable AQI for this location")
    aqi=max(0,min(500,int(raw_aqi)))
    sub=_subindices(data)
    # Keep the legacy pollutants object non-sensitive/empty so the backend does not archive WAQI data.
    # Real provider values are exposed separately as pollutantSubIndices.
    cat=category_for_aqi(aqi)
    city=data.get("city") or {}
    geo=city.get("geo") or [loc["lat"],loc["lon"]]
    return {"location":{"id":loc["id"],"name":city.get("name") or loc["name"],"country":loc.get("country", ""),"lat":float(geo[0]),"lon":float(geo[1])},"aqi":aqi,"category":cat["label"],"categoryKey":cat["key"],"color":cat["color"],"dominantPollutant":data.get("dominentpol") or None,"pollutants":{},"pollutantSubIndices":sub,"updatedAt":datetime.now(timezone.utc).isoformat(),"providerUpdatedAt":((data.get("time") or {}).get("iso") or (data.get("time") or {}).get("s")),"source":_source(data)}


def history(loc,kind="24h"):
    return []


def forecast(loc,days=5):
    # WAQI exposes pollutant forecasts, but the existing UI expects a compact daily AQI series.
    # We do not fabricate a series when the provider does not return forecast data.
    try:
        data=_waqi_feed(loc)
        fc=data.get("forecast") or {}
        daily=fc.get("daily") or {}
        days=max(1,min(7,int(days)))
        rows=[]
        for i in range(days):
            candidates=[]
            for pollutant in ("pm25","pm10","o3","no2","so2","co"):
                for item in (daily.get(pollutant) or []):
                    if len(rows) >= days: break
                    if item.get("avg") is not None: candidates.append(float(item["avg"]))
            if not candidates: break
            aqi=int(round(max(candidates)))
            cat=category_for_aqi(aqi)
            rows.append({"t":None,"label":"Forecast day %d"%(i+1),"aqi":aqi,"category":cat["label"],"categoryKey":cat["key"],"color":cat["color"],"trend":"stable","derived":True})
        return rows
    except Exception:
        return []


def map_overview():
    try:
        data=_waqi_json("/map/bounds/",{"latlng":"-90,-180,90,180"})
    except Exception as exc:
        logger.warning("WAQI map request failed: %s",exc)
        return []
    out=[]
    for item in data if isinstance(data,list) else []:
        aqi=item.get("aqi")
        if aqi in (None,"-"): continue
        try: aqi=int(aqi)
        except (TypeError,ValueError): continue
        cat=category_for_aqi(aqi)
        out.append({"id":str(item.get("uid") or item.get("station") or len(out)),"name":item.get("station") or "WAQI station","country":"","lat":item.get("lat"),"lon":item.get("lon"),"aqi":aqi,"category":cat["label"],"categoryKey":cat["key"],"color":cat["color"],"dominantPollutant":None,"source":{"provider":"World Air Quality Index (WAQI)","providerUrl":"https://waqi.info/"}})
    return out
