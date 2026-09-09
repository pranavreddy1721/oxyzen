FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Normalize WAQI AQI values at the backend boundary. WAQI normally documents
# AQI as an integer, but the live Sangli-associated feed can return a numeric
# string such as "23.0". The old int("23.0") path rejected it and later
# current_snapshot() crashed with ValueError. Also derive AQI from pollutant
# sub-indices only when WAQI omits the aggregate AQI entirely.
RUN python - <<'PY'
from pathlib import Path
p = Path("aqi_data.py")
s = p.read_text()
old = '''def _has_usable_aqi(data):
 try:return int(str((data or {}).get("aqi")).strip())>=0
 except (TypeError,ValueError):return False'''
new = '''def _has_usable_aqi(data):
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
 return False'''
if old not in s:
 raise SystemExit("WAQI AQI helper pattern not found")
s=s.replace(old,new,1)
old_snapshot='''def current_snapshot(loc):
 data,distance,slat,slon=_resolve_feed(loc);aqi=max(0,min(500,int(str(data["aqi"]).strip())));sub=_subindices(data);cat=category_for_aqi(aqi);updated=((data.get("time") or {}).get("iso") or (data.get("time") or {}).get("s"));source=_source(data);source.update({"stationLat":slat,"stationLon":slon,"distanceKm":round(distance,1),"matchType":"direct" if distance<=5 else "nearby","dataType":"Direct monitoring station" if distance<=5 else "Nearby/associated monitoring station"});return {"location":{"id":loc["id"],"name":loc["name"],"country":loc.get("country",""),"lat":float(loc["lat"]),"lon":float(loc["lon"])},"aqi":aqi,"category":cat["label"],"categoryKey":cat["key"],"color":cat["color"],"dominantPollutant":data.get("dominentpol"),"pollutants":sub,"pollutantSubIndices":sub,"updatedAt":updated or datetime.now(timezone.utc).isoformat(),"providerUpdatedAt":updated,"source":source}'''
new_snapshot='''def current_snapshot(loc):
 data,distance,slat,slon=_resolve_feed(loc);aqi=max(0,min(500,int(round(float(data["aqi"])))));sub=_subindices(data);cat=category_for_aqi(aqi);updated=((data.get("time") or {}).get("iso") or (data.get("time") or {}).get("s"));source=_source(data);source.update({"stationLat":slat,"stationLon":slon,"distanceKm":round(distance,1),"matchType":"direct" if distance<=5 else "nearby","dataType":"Direct monitoring station" if distance<=5 else "Nearby/associated monitoring station"});return {"location":{"id":loc["id"],"name":loc["name"],"country":loc.get("country",""),"lat":float(loc["lat"]),"lon":float(loc["lon"])},"aqi":aqi,"category":cat["label"],"categoryKey":cat["key"],"color":cat["color"],"dominantPollutant":data.get("dominentpol"),"pollutants":sub,"pollutantSubIndices":sub,"updatedAt":updated or datetime.now(timezone.utc).isoformat(),"providerUpdatedAt":updated,"source":source}'''
if old_snapshot not in s:
 raise SystemExit("current_snapshot pattern not found")
s=s.replace(old_snapshot,new_snapshot,1)
p.write_text(s)
PY

EXPOSE 8000
CMD ["uvicorn", "waqi_server:app", "--host", "0.0.0.0", "--port", "8000"]
