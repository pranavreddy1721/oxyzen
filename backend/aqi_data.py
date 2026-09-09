"""OxyZen live AQI data adapter using WAQI."""
import logging, os, time, math
from datetime import datetime, timezone
import requests
logger=logging.getLogger("oxyzen.aqi_data")
WAQI_BASE="https://api.waqi.info"; GEOCODING_URL="https://geocoding-api.open-meteo.com/v1/search"
_EXTERNAL_LOCATIONS={}; _GEOCODE_CACHE={}; _GEOCODE_CACHE_TTL=600; MAX_STATION_DISTANCE_KM=100.0
WAQI_STATIONS={"kolhapur":["A567994","A567991"],"sangli":["A568009"]}
CITIES=[{"id":"delhi","name":"Delhi","country":"India","lat":28.6139,"lon":77.2090},{"id":"mumbai","name":"Mumbai","country":"India","lat":19.076,"lon":72.8777},{"id":"sangli","name":"Sangli","country":"India","lat":16.8524,"lon":74.5815},{"id":"kolhapur","name":"Kolhapur","country":"India","lat":16.705,"lon":74.2433},{"id":"pune","name":"Pune","country":"India","lat":18.5204,"lon":73.8567},{"id":"bengaluru","name":"Bengaluru","country":"India","lat":12.9716,"lon":77.5946},{"id":"kolkata","name":"Kolkata","country":"India","lat":22.5726,"lon":88.3639},{"id":"beijing","name":"Beijing","country":"China","lat":39.9042,"lon":116.4074},{"id":"shanghai","name":"Shanghai","country":"China","lat":31.2304,"lon":121.4737},{"id":"lahore","name":"Lahore","country":"Pakistan","lat":31.5204,"lon":74.3587},{"id":"dhaka","name":"Dhaka","country":"Bangladesh","lat":23.8103,"lon":90.4125},{"id":"london","name":"London","country":"United Kingdom","lat":51.5074,"lon":-0.1278},{"id":"paris","name":"Paris","country":"France","lat":48.8566,"lon":2.3522},{"id":"newyork","name":"New York","country":"United States","lat":40.7128,"lon":-74.006},{"id":"losangeles","name":"Los Angeles","country":"United States","lat":34.0522,"lon":-118.2437},{"id":"tokyo","name":"Tokyo","country":"Japan","lat":35.6762,"lon":139.6503},{"id":"seoul","name":"Seoul","country":"South Korea","lat":37.5665,"lon":126.978},{"id":"sydney","name":"Sydney","country":"Australia","lat":-33.8688,"lon":151.2093},{"id":"zurich","name":"Zurich","country":"Switzerland","lat":47.3769,"lon":8.5417},{"id":"cairo","name":"Cairo","country":"Egypt","lat":30.0444,"lon":31.2357},{"id":"saopaulo","name":"São Paulo","country":"Brazil","lat":-23.5505,"lon":-46.6333},{"id":"mexicocity","name":"Mexico City","country":"Mexico","lat":19.4326,"lon":-99.1332},{"id":"dubai","name":"Dubai","country":"UAE","lat":25.2048,"lon":55.2708},{"id":"singapore","name":"Singapore","country":"Singapore","lat":1.3521,"lon":103.8198},{"id":"reykjavik","name":"Reykjavik","country":"Iceland","lat":64.1466,"lon":-21.9426}]
POLLUTANT_META={k:{"key":k,"name":n,"unit":"AQI sub-index","reference":100,"full_name":f,"short":f"WAQI pollutant AQI sub-index for {f.lower()}.","what":"This value is a WAQI pollutant AQI sub-index, not a concentration measurement.","sources":[],"effects":[],"precautions":[]} for k,n,f in [("pm25","PM2.5","fine particulate matter"),("pm10","PM10","coarse particulate matter"),("o3","O₃","ground-level ozone"),("no2","NO₂","nitrogen dioxide"),("so2","SO₂","sulfur dioxide"),("co","CO","carbon monoxide") ]}
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
 try:return int(str((data or {}).get("aqi")).strip())>=0
 except (TypeError,ValueError):return False
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
 for sid in _known_station_ids(loc):
  result=_fetch_feed(loc,f"/feed/@{sid}/",enforce_distance=False)
  if result:return result
 name=(loc.get("name") or "").strip()
 if name:
  result=_fetch_feed(loc,f"/feed/{name}/")
  if result:return result
 result=_fetch_feed(loc,f"/feed/geo:{float(loc['lat'])};{float(loc['lon'])}/")
 if result:return result
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
  if result:return result
 raise RuntimeError(f"No usable WAQI station within {MAX_STATION_DISTANCE_KM:.0f} km of {name or 'selected location'}")
def _subindices(data):
 iaqi=data.get("iaqi") or {};out={}
 for k in POLLUTANT_META:
  v=(iaqi.get(k) or {}).get("v")
  if isinstance(v,(int,float)):out[k]=round(float(v),1)
 return out
def _source(data):
 city=data.get("city") or {};attrs=data.get("attributions") or [];origin=attrs[0] if attrs else {}
 return {"provider":"World Air Quality Index (WAQI)","providerUrl":"https://waqi.info/","station":city.get("name") or "WAQI station","stationUrl":city.get("url") or "","origin":origin.get("name") or "","originUrl":origin.get("url") or ""}
def current_snapshot(loc):
 data,distance,slat,slon=_resolve_feed(loc);aqi=max(0,min(500,int(str(data["aqi"]).strip())));sub=_subindices(data);cat=category_for_aqi(aqi);updated=((data.get("time") or {}).get("iso") or (data.get("time") or {}).get("s"));source=_source(data);source.update({"stationLat":slat,"stationLon":slon,"distanceKm":round(distance,1),"matchType":"direct" if distance<=5 else "nearby","dataType":"Direct monitoring station" if distance<=5 else "Nearby/associated monitoring station"});return {"location":{"id":loc["id"],"name":loc["name"],"country":loc.get("country",""),"lat":float(loc["lat"]),"lon":float(loc["lon"])},"aqi":aqi,"category":cat["label"],"categoryKey":cat["key"],"color":cat["color"],"dominantPollutant":data.get("dominentpol"),"pollutants":sub,"pollutantSubIndices":sub,"updatedAt":updated or datetime.now(timezone.utc).isoformat(),"providerUpdatedAt":updated,"source":source}
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
