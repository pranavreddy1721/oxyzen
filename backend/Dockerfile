FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Sangli's dedicated WAQI station can omit the aggregate AQI while still
# returning pollutant AQI sub-indices. Derive the overall AQI from the
# highest available WAQI pollutant sub-index instead of returning HTTP 500.
RUN python - <<'PY'
from pathlib import Path
p = Path('aqi_data.py')
s = p.read_text()
old = '''def _has_usable_aqi(data):
 try:return int(str((data or {}).get("aqi")).strip())>=0
 except (TypeError,ValueError):return False'''
new = '''def _has_usable_aqi(data):
 try:
  return int(str((data or {}).get("aqi")).strip())>=0
 except (TypeError,ValueError):
  iaqi=(data or {}).get("iaqi") or {}
  values=[]
  for item in iaqi.values():
   try:
    value=float((item or {}).get("v"))
    if value>=0: values.append(value)
   except (TypeError,ValueError):
    pass
  if values:
   data["aqi"]=max(values)
   data["_aqiDerivedFromPollutantSubindices"]=True
   return True
  return False'''
if old not in s:
 raise SystemExit('WAQI AQI helper pattern not found')
s=s.replace(old,new,1)
s=s.replace('"sangli":["A568009"]','"sangli":["A568009","A567994","A567991"]',1)
p.write_text(s)
PY

EXPOSE 8000
CMD ["uvicorn", "waqi_server:app", "--host", "0.0.0.0", "--port", "8000"]
