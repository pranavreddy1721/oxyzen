"""OxyZen live AQI data adapter using WAQI."""
import logging, os, time, math
from datetime import datetime, timezone
import requests
logger=logging.getLogger("oxyzen.aqi_data")
WAQI_BASE="https://api.waqi.info"; GEOCODING_URL="https://geocoding-api.open-meteo.com/v1/search"
_EXTERNAL_LOCATIONS={}; _GEOCODE_CACHE={}; _GEOCODE_CACHE_TTL=600; _OPEN_METEO_CACHE={}; MAX_STATION_DISTANCE_KM=100.0
WAQI_STATIONS={"kolhapur":["A567994","A567991"],"sangli":["A568009"]}
CITIES=[{"id":"delhi","name":"Delhi","country":"India","lat":28.6139,"lon":77.2090},{"id":"mumbai","name":"Mumbai","country":"India","lat":19.076,"lon":72.8777},{"id":"sangli","name":"Sangli","country":"India","lat":16.8524,"lon":74.5815},{"id":"kolhapur","name":"Kolhapur","country":"India","lat":16.705,"lon":74.2433},{"id":"pune","name":"Pune","country":"India","lat":18.5204,"lon":73.8567},{"id":"bengaluru","name":"Bengaluru","country":"India","lat":12.9716,"lon":77.5946},{"id":"kolkata","name":"Kolkata","country":"India","lat":22.5726,"lon":88.3639},{"id":"beijing","name":"Beijing","country":"China","lat":39.9042,"lon":116.4074},{"id":"shanghai","name":"Shanghai","country":"China","lat":31.2304,"lon":121.4737},{"id":"lahore","name":"Lahore","country":"Pakistan","lat":31.5204,"lon":74.3587},{"id":"dhaka","name":"Dhaka","country":"Bangladesh","lat":23.8103,"lon":90.4125},{"id":"london","name":"London","country":"United Kingdom","lat":51.5074,"lon":-0.1278},{"id":"paris","name":"Paris","country":"France","lat":48.8566,"lon":2.3522},{"id":"newyork","name":"New York","country":"United States","lat":40.7128,"lon":-74.006},{"id":"losangeles","name":"Los Angeles","country":"United States","lat":34.0522,"lon":-118.2437},{"id":"tokyo","name":"Tokyo","country":"Japan","lat":35.6762,"lon":139.6503},{"id":"seoul","name":"Seoul","country":"South Korea","lat":37.5665,"lon":126.978},{"id":"sydney","name":"Sydney","country":"Australia","lat":-33.8688,"lon":151.2093},{"id":"zurich","name":"Zurich","country":"Switzerland","lat":47.3769,"lon":8.5417},{"id":"cairo","name":"Cairo","country":"Egypt","lat":30.0444,"lon":31.2357},{"id":"saopaulo","name":"São Paulo","country":"Brazil","lat":-23.5505,"lon":-46.6333},{"id":"mexicocity","name":"Mexico City","country":"Mexico","lat":19.4326,"lon":-99.1332},{"id":"dubai","name":"Dubai","country":"UAE","lat":25.2048,"lon":55.2708},{"id":"singapore","name":"Singapore","country":"Singapore","lat":1.3521,"lon":103.8198},{"id":"reykjavik","name":"Reykjavik","country":"Iceland","lat":64.1466,"lon":-21.9426}]
POLLUTANT_META={k:{"key":k,"name":n,"unit":"AQI sub-index","reference":500,"full_name":f,"short":f"WAQI pollutant AQI sub-index for {f.lower()}.","what":"This value is a WAQI pollutant AQI sub-index, not a concentration measurement.","sources":[],"effects":[],"precautions":[]} for k,n,f in [("pm25","PM2.5","fine particulate matter"),("pm10","PM10","coarse particulate matter"),("o3","O₃","ground-level ozone"),("no2","NO₂","nitrogen dioxide"),("so2","SO₂","sulfur dioxide"),("co","CO","carbon monoxide") ]}
AQI_CATEGORIES=[{"min":0,"max":50,"label":"Good","key":"good","color":"#10B981"},{"min":51,"max":100,"label":"Moderate","key":"moderate","color":"#F59E0B"},{"min":101,"max":150,"label":"Unhealthy for Sensitive Groups","key":"sensitive","color":"#F97316"},{"min":151,"max":200,"label":"Unhealthy","key":"unhealthy","color":"#EF4444"},{"min":201,"max":300,"label":"Very Unhealthy","key":"veryUnhealthy","color":"#9333EA"},{"min":301,"max":500,"label":"Hazardous","key":"hazardous","color":"#9F1239"}]
def category_for_aqi(aqi):
 aqi=max(0,min(500,int(aqi))); return next((c for c in AQI_CATEGORIES if c["min"]<=aqi<=c["max"]),AQI_CATEGORIES[-1])
def _external_location(x):
 loc={"id":f"geo_{x.get('id')}","name":x.get("name") or "Unknown location","country":x.get("country") or "","admin1":x.get("admin1") or "","lat":float(x["latitude"]),"lon":float(x["longitude"])}; _EXTERNAL_LOCATIONS[loc["id"]]=loc; return loc
def _search_open_meteo(q,limit):
 q=(q or "").strip()
 if len(q)<2:return []
 key=q.lower(); now=time.monotonic(); cached=_GEOCODE_CACHE.get(key)
 if cached and now-cached[0]<_GEOCODE_CACHE_TTL:return cached[1][:limit]
 try:
  r=requests.get(GEOCODING_URL,params={"name":q,"count":min(limit,20),"language":"en","format":"json"},timeout=4); r.raise_for_status(); out=[_external_location(x) for x in (r.json().get("results") or [])]; _GEOCODE_CACHE[key]=(now,out); return out[:limit]
 except Exception as exc: logger.warning("location search failed: %s",exc); return []
def _same_location(a,b): return (a.get("name","").lower(),a.get("country","").lower())==(b.get("name","").lower(),b.get("country","").lower()) or (abs(a["lat"]-b["lat"])<.01 and abs(a["lon"]-b["lon"])<.01)
def search_locations(q="",limit=8):
 q=(q or "").strip(); limit=min(max(int(limit or 8),1),20)
 if not q:return CITIES[:limit]
 out=[c for c in CITIES if q.lower() in f"{c['name']} {c['country']}".lower()]
 for x in _search_open_meteo(q,limit):
  if not any(_same_location(x,y) for y in out):out.append(x)
  if len(out)>=limit:break
 return out[:limit]
def find_by_id(loc_id): return next((c for c in CITIES if c["id"]==loc_id),None) or _EXTERNAL_LOCATIONS.get(loc_id)
def nearest_location(lat,lon): return min(CITIES,key=lambda c:(c["lat"]-lat)**2+(c["lon"]-lon)**2)
def make_custom_location(lat,lon,name=None,country=""): return {"id":f"coord_{round(lat,3)}_{round(lon,3)}","name":name or f"{round(lat,3)}, {round(lon,3)}","country":country,"lat":lat,"lon":lon}
def _waqi_json(path,params=None):
 token=os.environ.get("WAQI_TOKEN","").strip()
 if not token:raise RuntimeError("WAQI_TOKEN is not configured on the backend")
 p=dict(params or {}); p["token"]=token; r=requests.get(f"{WAQI_BASE}{path}",params=p,timeout=10); r.raise_for_status(); payload=r.json()
 if payload.get("status")!="ok":raise RuntimeError(str(payload.get("data") or "WAQI request failed"))
 return payload.get("data") or {}
def _has_usable_aqi(data):
 raw=(data or {}).get("aqi")
 try:
  value=float(str(raw).strip())
  if value>=0:
   data["aqi"]=int(round(value))
   return True
 except (TypeError,ValueError):
  pass
 iaqi=(data or {}).get("iaqi") or {}
 values=[]
 for item in iaqi.values():
  try:
   value=float((item or {}).get("v"))
   if value>=0: values.append(value)
  except (TypeError,ValueError):
   pass
 if values:
  data["aqi"]=int(round(max(values)))
  data["_aqiDerivedFromPollutantSubindices"]=True
  return True
 return False
def _distance_km(lat1,lon1,lat2,lon2):
 r=6371.0;p1=math.radians(float(lat1));p2=math.radians(float(lat2));dp=math.radians(float(lat2)-float(lat1));dl=math.radians(float(lon2)-float(lon1));a=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2;return 2*r*math.asin(math.sqrt(a))
def _feed_coordinates(data):
 geo=((data or {}).get("city") or {}).get("geo") or []
 if len(geo)<2:return None
 try:return float(geo[0]),float(geo[1])
 except (TypeError,ValueError):return None
def _fetch_feed(loc,path,fallback_coords=None,enforce_distance=True):
 try:data=_waqi_json(path)
 except Exception as exc: logger.warning("WAQI feed %s failed for %s: %s",path,loc.get("name"),exc); return None
 if not _has_usable_aqi(data): logger.warning("WAQI feed %s has no current AQI for %s",path,loc.get("name")); return None
 coords=_feed_coordinates(data) or fallback_coords
 if not coords and not enforce_distance: coords=(float(loc["lat"]),float(loc["lon"]))
 if not coords: logger.warning("WAQI feed %s has no coordinates for %s",path,loc.get("name")); return None
 actual=_feed_coordinates(data) or fallback_coords
 distance=_distance_km(loc["lat"],loc["lon"],actual[0],actual[1]) if actual else 0.0
 if enforce_distance and distance>MAX_STATION_DISTANCE_KM: logger.warning("Rejected WAQI station %s: %.1f km from %s",(data.get("city") or {}).get("name") or path,distance,loc.get("name")); return None
 return data,distance,coords[0],coords[1]
def _known_station_ids(loc):
 key=str(loc.get("id") or "").lower();name=str(loc.get("name") or "").lower()
 for candidate in (key,name):
  if "kolhapur" in candidate:return WAQI_STATIONS["kolhapur"]
  if "sangli" in candidate:return WAQI_STATIONS["sangli"]
 return []
def _resolve_feed(loc):
 name=(loc.get("name") or "").strip()
 now=datetime.now(timezone.utc)
 def fresh(result, station_label):
  if not result:return False
  updated_raw=_provider_time(result[0])
  if updated_raw is None:
   logger.warning("Skipping WAQI station %s: timestamp missing or invalid",station_label)
   return False
  try:
   updated=datetime.fromisoformat(updated_raw.replace("Z","+00:00"))
  except (TypeError,ValueError):
   logger.warning("Skipping WAQI station %s: normalized timestamp is invalid: %r",station_label,updated_raw)
   return False
  age=(now-updated).total_seconds()
  if age < -300 or age > 7200:
   logger.warning("Skipping stale/future WAQI station %s: updated=%s age_seconds=%.0f",station_label,updated.isoformat(),age)
   return False
  return True
 for sid in _known_station_ids(loc):
  result=_fetch_feed(loc,f"/feed/{sid}/",enforce_distance=False)
  if fresh(result,sid):return result
 if name:
  result=_fetch_feed(loc,f"/feed/{name}/")
  if fresh(result,name):return result
 result=_fetch_feed(loc,f"/feed/geo:{float(loc['lat'])};{float(loc['lon'])}/")
 if fresh(result,"geographic lookup"):return result
 lat,lon=float(loc["lat"]),float(loc["lon"]); bounds=f"{lat-1.0},{lon-1.0},{lat+1.0},{lon+1.0}"
 try:stations=_waqi_json("/map/bounds/",{"latlng":bounds})
 except Exception as exc: logger.warning("WAQI map lookup failed for %s: %s",name,exc); stations=[]
 candidates=[]
 for item in stations if isinstance(stations,list) else []:
  try:
   uid=item.get("uid");slat=float(item["lat"]);slon=float(item["lon"])
   if uid is not None:
    d=_distance_km(lat,lon,slat,slon)
    if d<=MAX_STATION_DISTANCE_KM:candidates.append((d,str(uid),slat,slon))
  except (KeyError,TypeError,ValueError):continue
 for _,uid,slat,slon in sorted(candidates,key=lambda x:x[0]):
  result=_fetch_feed(loc,f"/feed/@{uid}/",fallback_coords=(slat,slon))
  if fresh(result,uid):return result
 raise RuntimeError(f"No fresh WAQI station within {MAX_STATION_DISTANCE_KM:.0f} km of {name or 'selected location'}")
def _subindices(data):
 iaqi=data.get("iaqi") or {};out={}
 for k in POLLUTANT_META:
  v=(iaqi.get(k) or {}).get("v")
  if isinstance(v,(int,float)):out[k]=round(float(v),1)
 return out
def _source(data):
 city=data.get("city") or {};attrs=data.get("attributions") or [];origin=attrs[0] if attrs else {}
 return {"provider":"World Air Quality Index (WAQI)","providerUrl":"https://waqi.info/","station":city.get("name") or "WAQI station","stationUrl":city.get("url") or "","origin":origin.get("name") or "","originUrl":origin.get("url") or ""}
def _provider_time(data):
    stamp = data.get("time") or {}
    raw_iso = stamp.get("iso")
    raw_epoch = stamp.get("s")
    tz_hint = stamp.get("tz")
    if raw_iso:
        try:
            parsed = datetime.fromisoformat(str(raw_iso).replace("Z", "+00:00"))
            if parsed.tzinfo is None and tz_hint:
                try:
                    from zoneinfo import ZoneInfo
                    parsed = parsed.replace(tzinfo=ZoneInfo(str(tz_hint)))
                except Exception:
                    import re
                    match = re.fullmatch(r"([+-])(\\d{2}):?(\\d{2})", str(tz_hint).strip())
                    if match:
                        minutes = (int(match.group(2)) * 60 + int(match.group(3))) * (1 if match.group(1) == "+" else -1)
                        from datetime import timedelta
                        parsed = parsed.replace(tzinfo=timezone(timedelta(minutes=minutes)))
            if parsed.tzinfo is not None:
                return parsed.astimezone(timezone.utc).isoformat()
            logger.warning("WAQI timestamp has no timezone; rejecting ambiguous local timestamp: %s", raw_iso)
        except (TypeError, ValueError, OverflowError):
            logger.warning("Could not parse WAQI ISO timestamp: %s", raw_iso)
    if raw_epoch is not None:
        try:
            return datetime.fromtimestamp(float(raw_epoch), tz=timezone.utc).isoformat()
        except (TypeError, ValueError, OverflowError, OSError):
            logger.warning("Could not parse WAQI epoch timestamp: %s", raw_epoch)
    return None

OPEN_METEO_AQI_FIELDS={
 "pm25":"us_aqi_pm2_5","pm10":"us_aqi_pm10","o3":"us_aqi_ozone",
 "no2":"us_aqi_nitrogen_dioxide","so2":"us_aqi_sulphur_dioxide",
 "co":"us_aqi_carbon_monoxide",
}

def _open_meteo_payload(loc):
    key=(round(float(loc["lat"]),3),round(float(loc["lon"]),3))
    cached=_OPEN_METEO_CACHE.get(key)
    now=time.monotonic()
    if cached and now-cached[0]<600:
        return cached[1]
    url="https://air-quality-api.open-meteo.com/v1/air-quality"
    response=requests.get(url,params={
        "latitude":float(loc["lat"]),
        "longitude":float(loc["lon"]),
        "current":"us_aqi,pm2_5,pm10,ozone,nitrogen_dioxide,sulphur_dioxide,carbon_monoxide",
        "hourly":",".join(OPEN_METEO_AQI_FIELDS.values()),
        "past_hours":2,
        "forecast_hours":1,
        "timezone":"UTC",
    },timeout=10)
    response.raise_for_status()
    payload=response.json()
    _OPEN_METEO_CACHE[key]=(now,payload)
    return payload

def _open_meteo_pollutant_indices(payload,target_time):
    """Return CAMS modelled US-AQI sub-indices nearest the requested timestamp."""
    hourly=payload.get("hourly") or {}
    times=hourly.get("time") or []
    if not times:
        return {},None
    try:
        target=datetime.fromisoformat(str(target_time).replace("Z","+00:00"))
        if target.tzinfo is None: target=target.replace(tzinfo=timezone.utc)
        target=target.astimezone(timezone.utc)
    except (TypeError,ValueError):
        return {},None
    nearest=None
    for index,raw in enumerate(times):
        try:
            stamp=datetime.fromisoformat(str(raw).replace("Z","+00:00"))
            if stamp.tzinfo is None: stamp=stamp.replace(tzinfo=timezone.utc)
            delta=abs((stamp.astimezone(timezone.utc)-target).total_seconds())
            if nearest is None or delta<nearest[0]: nearest=(delta,index,stamp)
        except (TypeError,ValueError):
            continue
    if nearest is None or nearest[0]>5400:
        logger.warning("Open-Meteo pollutant index time is not aligned with AQI timestamp")
        return {},None
    _,index,stamp=nearest
    result={}
    for pollutant,field in OPEN_METEO_AQI_FIELDS.items():
        values=hourly.get(field) or []
        if index>=len(values): continue
        try:
            value=float(values[index])
            if math.isfinite(value) and value>=0:
                result[pollutant]=round(value,1)
        except (TypeError,ValueError):
            continue
    return result,stamp.astimezone(timezone.utc).isoformat()

def _open_meteo_snapshot(loc):
    payload=_open_meteo_payload(loc)
    current=payload.get("current") or {}
    raw_aqi=current.get("us_aqi")
    stamp=current.get("time")
    if raw_aqi is None or not stamp:
        raise RuntimeError("Open-Meteo did not return a current US AQI reading")
    updated=datetime.fromisoformat(str(stamp).replace("Z","+00:00"))
    if updated.tzinfo is None:
        updated=updated.replace(tzinfo=timezone.utc)
    now=datetime.now(timezone.utc)
    age=(now-updated.astimezone(timezone.utc)).total_seconds()
    if age < -900 or age > 10800:
        raise RuntimeError(f"Open-Meteo current AQI timestamp is outside freshness window (age_seconds={age:.0f})")
    aqi=max(0,min(500,int(round(float(raw_aqi)))))
    cat=category_for_aqi(aqi)
    pollutants,index_time=_open_meteo_pollutant_indices(payload,updated)
    pollutant_sources={k:"Open-Meteo CAMS model estimate" for k in pollutants}
    source={
        "provider":"Open-Meteo CAMS Air Quality",
        "providerUrl":"https://open-meteo.com/en/docs/air-quality-api",
        "station":"CAMS model grid cell",
        "stationLat":payload.get("latitude"),
        "stationLon":payload.get("longitude"),
        "distanceKm":round(_distance_km(float(loc["lat"]),float(loc["lon"]),float(payload.get("latitude",loc["lat"])),float(payload.get("longitude",loc["lon"]))),1),
        "matchType":"model",
        "dataType":"Modelled current US AQI and pollutant sub-indices (not a ground monitoring station)",
        "pollutantIndexTime":index_time,
    }
    logger.info("Using fresh Open-Meteo fallback for %s: AQI=%s pollutant_indices=%s",loc.get("name"),aqi,sorted(pollutants))
    return {
        "location":{"id":loc["id"],"name":loc["name"],"country":loc.get("country",""),"lat":float(loc["lat"]),"lon":float(loc["lon"])},
        "aqi":aqi,"category":cat["label"],"categoryKey":cat["key"],"color":cat["color"],
        "dominantPollutant":None,"pollutants":pollutants,"pollutantSubIndices":pollutants,
        "pollutantDataSources":pollutant_sources,"updatedAt":updated.isoformat(),
        "providerUpdatedAt":updated.isoformat(),"source":source,
    }

# CPCB-origin Indian station data through a third-party API mirror.
_CPCB_CACHE = {}
_CPCB_CACHE_TTL = 300
_CPCB_STATE = {"delhi": "Delhi", "mumbai": "Maharashtra", "pune": "Maharashtra", "sangli": "Maharashtra", "kolhapur": "Maharashtra", "bengaluru": "Karnataka", "kolkata": "West Bengal"}
_CPCB_COLORS = {"good": "#10B981", "satisfactory": "#84CC16", "moderate": "#F59E0B", "poor": "#F97316", "very poor": "#EF4444", "severe": "#7F1D1D"}
_CPCB_BANDS = [(0, 50, "Good", "good"), (51, 100, "Satisfactory", "satisfactory"), (101, 200, "Moderate", "moderate"), (201, 300, "Poor", "poor"), (301, 400, "Very Poor", "very poor"), (401, 500, "Severe", "severe")]
_CPCB_POLLUTANTS = {"PM2.5": "pm25", "PM10": "pm10", "OZONE": "o3", "NO2": "no2", "SO2": "so2", "CO": "co"}

def _safe_float(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None

def _cpcb_category(aqi):
    value = max(0, min(500, int(round(float(aqi)))))
    return next(({"min": lo, "max": hi, "label": label, "key": key, "color": _CPCB_COLORS[key]} for lo, hi, label, key in _CPCB_BANDS if lo <= value <= hi), {"label": "Severe", "key": "severe", "color": _CPCB_COLORS["severe"]})

def cpcb_station_data(loc):
    """Fetch CPCB-origin station AQI and pollutant sub-indices via the documented mirror."""
    city = str(loc.get("name") or "").strip()
    if not city or loc.get("country") != "India":
        return {"available": False, "reason": "CPCB mirror supports Indian cities only", "stations": []}
    cache_key = city.lower()
    now = time.monotonic()
    cached = _CPCB_CACHE.get(cache_key)
    if cached and now - cached[0] < _CPCB_CACHE_TTL:
        return cached[1]
    try:
        response = requests.get("https://api.dharun.dev/v1/air-quality", params={"city": city}, timeout=12)
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("data") or []
        stations = []
        for row in rows:
            pollutants = {}
            indices = {}
            for label, key in _CPCB_POLLUTANTS.items():
                values = row.get("pollutants", {}).get(label) or {}
                avg = _safe_float(values.get("avg"))
                if avg is None or avg < 0:
                    continue
                indices[key] = avg
                pollutants[label] = {"average": avg, "minimum": _safe_float(values.get("min")), "maximum": _safe_float(values.get("max")), "unit": "CPCB AQI sub-index"}
            aqi = _safe_float(row.get("aqi"))
            if aqi is None or not 0 <= aqi <= 500:
                continue
            updated = str(row.get("updated") or "").strip()
            try:
                stamp = datetime.strptime(updated, "%Y-%m-%d %H:%M").replace(tzinfo=__import__("zoneinfo").ZoneInfo("Asia/Kolkata"))
                age = (datetime.now(timezone.utc) - stamp.astimezone(timezone.utc)).total_seconds()
                if age < -900 or age > 10800:
                    logger.warning("Skipping stale/future CPCB mirror station %s: age_seconds=%.0f", row.get("station"), age)
                    continue
                updated_iso = stamp.isoformat()
            except (TypeError, ValueError, OverflowError):
                logger.warning("Skipping CPCB mirror station with invalid timestamp: %r", updated)
                continue
            stations.append({
                "station": row.get("station") or "CPCB monitoring station",
                "city": row.get("city") or city, "state": row.get("state") or _CPCB_STATE.get(cache_key, ""),
                "latitude": _safe_float(row.get("latitude")), "longitude": _safe_float(row.get("longitude")),
                "lastUpdate": updated, "updatedAt": updated_iso, "aqi": int(round(aqi)),
                "category": row.get("category") or _cpcb_category(aqi)["label"],
                "dominantPollutant": str(row.get("main_pollutant") or "").lower(),
                "pollutants": pollutants, "pollutantSubIndices": indices,
            })
        result = {
            "available": bool(stations), "provider": "CPCB via third-party API mirror",
            "providerUrl": "https://api.dharun.dev/docs/air-quality",
            "datasetUrl": "https://www.data.gov.in/resource/real-time-air-quality-index-various-locations",
            "dataType": "CPCB station AQI and pollutant sub-indices, relayed by a third-party API mirror",
            "city": city, "state": _CPCB_STATE.get(cache_key, ""),
            "stations": stations, "recordCount": len(stations),
            "updatedAt": max((s["lastUpdate"] for s in stations), default=None),
            "attribution": (payload.get("meta") or {}).get("source", {}).get("attribution", ""),
            "retrievedAt": (payload.get("meta") or {}).get("source", {}).get("retrieved"),
        }
        if not stations:
            result["reason"] = "No fresh CPCB station readings were returned for this city"
        _CPCB_CACHE[cache_key] = (now, result)
        return result
    except Exception as exc:
        logger.warning("CPCB mirror request failed for %s: %s", city, exc)
        return {"available": False, "provider": "CPCB via third-party API mirror", "stations": [],
                "reason": "CPCB station feed is temporarily unavailable"}

def _cpcb_snapshot(loc, station_data):
    stations = station_data.get("stations") or []
    if not stations:
        return None
    def distance(station):
        lat, lon = station.get("latitude"), station.get("longitude")
        return _distance_km(float(loc["lat"]), float(loc["lon"]), lat, lon) if lat is not None and lon is not None else float("inf")
    station = min(stations, key=distance)
    aqi = station["aqi"]
    cat = _cpcb_category(aqi)
    pollutants = dict(station.get("pollutantSubIndices") or {})
    sources = {key: "CPCB ground monitoring station sub-index (via third-party mirror)" for key in pollutants}
    dist = distance(station)
    source = {
        "provider": "CPCB via third-party API mirror",
        "providerUrl": "https://api.dharun.dev/docs/air-quality",
        "origin": "Central Pollution Control Board (CPCB) / MPCB",
        "originUrl": "https://app.cpcbccr.com/AQIIndia/",
        "station": station["station"], "stationLat": station.get("latitude"), "stationLon": station.get("longitude"),
        "distanceKm": round(dist, 1) if math.isfinite(dist) else None,
        "matchType": "direct" if dist <= 5 else "nearby",
        "dataType": "CPCB National AQI and station pollutant sub-indices via third-party mirror",
        "scale": "India CPCB National AQI",
    }
    return {
        "location": {"id": loc["id"], "name": loc["name"], "country": loc.get("country", ""), "lat": float(loc["lat"]), "lon": float(loc["lon"])},
        "aqi": aqi, "category": cat["label"], "categoryKey": cat["key"], "color": cat["color"],
        "dominantPollutant": station.get("dominantPollutant"), "pollutants": pollutants,
        "pollutantSubIndices": pollutants, "pollutantDataSources": sources,
        "updatedAt": station.get("updatedAt"), "providerUpdatedAt": station.get("updatedAt"),
        "aqiScale": "india_cpcb", "source": source,
    }

def _attach_cpcb_data(snapshot, loc):
    if loc.get("country") == "India":
        snapshot["officialStationData"] = cpcb_station_data(loc)
    return snapshot

def current_snapshot(loc):
    if loc.get("country") == "India":
        cpcb = cpcb_station_data(loc)
        primary = _cpcb_snapshot(loc, cpcb) if cpcb.get("available") else None
        if primary:
            primary["officialStationData"] = cpcb
            return primary
    try:
        data,distance,slat,slon=_resolve_feed(loc)
    except Exception as exc:
        logger.warning("No fresh WAQI station for %s; trying Open-Meteo current AQI and pollutant fallback: %s",loc.get("name"),exc)
        try:
            return _attach_cpcb_data(_open_meteo_snapshot(loc), loc)
        except Exception as fallback_exc:
            logger.error("No usable WAQI or Open-Meteo data for %s: %s",loc.get("name"),fallback_exc)
            return _attach_cpcb_data({
                "location":{"id":loc["id"],"name":loc["name"],"country":loc.get("country",""),"lat":float(loc["lat"]),"lon":float(loc["lon"])},
                "aqi":None,"category":"Unavailable","categoryKey":"unavailable","color":"#64748B",
                "dominantPollutant":None,"pollutants":{},"pollutantSubIndices":{},
                "pollutantDataSources":{},"updatedAt":None,"providerUpdatedAt":None,
                "source":{"provider":"Unavailable","station":"No current data source","dataType":"No fresh AQI or pollutant data available"},
            }, loc)

    aqi=max(0,min(500,int(round(float(data["aqi"])))))
    pollutants=_subindices(data)
    pollutant_sources={k:"WAQI monitoring station sub-index" for k in pollutants}
    updated=_provider_time(data)
    # Keep WAQI readings authoritative; use CAMS only to fill absent pollutant indices.
    model_time=None
    if len(pollutants)<len(POLLUTANT_META):
        try:
            model_payload=_open_meteo_payload(loc)
            modelled,model_time=_open_meteo_pollutant_indices(model_payload,updated)
            for pollutant,value in modelled.items():
                if pollutant not in pollutants:
                    pollutants[pollutant]=value
                    pollutant_sources[pollutant]="Open-Meteo CAMS model estimate"
        except Exception as exc:
            logger.warning("Open-Meteo pollutant enrichment unavailable for %s: %s",loc.get("name"),exc)
    cat=category_for_aqi(aqi)
    source=_source(data)
    source.update({
        "stationLat":slat,"stationLon":slon,
        "distanceKm":round(distance,1),
        "matchType":"direct" if distance<=5 else "nearby",
        "dataType":"WAQI ground monitoring station",
        "pollutantModelTime":model_time,
    })
    return _attach_cpcb_data({
        "location":{"id":loc["id"],"name":loc["name"],"country":loc.get("country",""),"lat":float(loc["lat"]),"lon":float(loc["lon"])},
        "aqi":aqi,"category":cat["label"],"categoryKey":cat["key"],"color":cat["color"],
        "dominantPollutant":data.get("dominentpol"),
        "pollutants":pollutants,"pollutantSubIndices":pollutants,
        "pollutantDataSources":pollutant_sources,
        "updatedAt":updated,"providerUpdatedAt":updated,"source":source,
    }, loc)
def history(loc,kind="24h"): return []
def forecast(loc,days=5):
 try:
  data=_resolve_feed(loc)[0];daily=(data.get("forecast") or {}).get("daily") or {};dates={}
  for pollutant,items in daily.items():
   if pollutant not in POLLUTANT_META:continue
   for item in items or []:
    day,avg=item.get("day"),item.get("avg")
    if day is not None and isinstance(avg,(int,float)):dates.setdefault(day,[]).append(float(avg))
  rows=[]
  for day,vals in sorted(dates.items())[:max(1,min(7,int(days)))]:
   aqi=int(round(max(vals)));cat=category_for_aqi(aqi);rows.append({"t":day,"label":day,"aqi":aqi,"category":cat["label"],"categoryKey":cat["key"],"color":cat["color"],"dominantPollutant":None,"trend":"stable","derived":True,"source":{"provider":"World Air Quality Index (WAQI)","providerUrl":"https://waqi.info/"}})
  return rows
 except Exception as exc: logger.warning("WAQI forecast failed: %s",exc); return []
def map_overview():
 try:data=_waqi_json("/map/bounds/",{"latlng":"-90,-180,90,180"})
 except Exception as exc:logger.warning("WAQI map request failed: %s",exc);return []
 out=[]
 for x in data if isinstance(data,list) else []:
  try:aqi=int(x.get("aqi"))
  except (TypeError,ValueError):continue
  cat=category_for_aqi(aqi);out.append({"id":str(x.get("uid") or len(out)),"name":x.get("station") or "WAQI station","country":"","lat":x.get("lat"),"lon":x.get("lon"),"aqi":aqi,"category":cat["label"],"categoryKey":cat["key"],"color":cat["color"],"dominantPollutant":None,"source":{"provider":"World Air Quality Index (WAQI)","providerUrl":"https://waqi.info/"}})
 return out
