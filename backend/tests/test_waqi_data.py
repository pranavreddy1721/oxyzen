import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import aqi_data

class MockResponse:
    def __init__(self, payload): self.payload = payload
    def raise_for_status(self): return None
    def json(self): return self.payload

def sample_payload():
    return {"status":"ok","data":{"aqi":42,"dominentpol":"pm25","iaqi":{"pm25":{"v":42},"pm10":{"v":30},"o3":{"v":18}},"city":{"name":"Kolhapur","url":"https://aqicn.org/city/kolhapur/","geo":[16.705,74.2433]},"time":{"iso":"2026-09-08T12:00:00+00:00"},"attributions":[{"name":"CPCB India","url":"https://cpcb.nic.in/"}]}}

def test_current_snapshot_uses_waqi(monkeypatch):
    monkeypatch.setenv("WAQI_TOKEN","test-token")
    monkeypatch.setattr(aqi_data.requests,"get",lambda *a,**k: MockResponse(sample_payload()))
    snap=aqi_data.current_snapshot(aqi_data.CITIES[2])
    assert snap["aqi"]==42
    assert snap["pollutants"]["pm25"]==42
    assert snap["source"]["provider"]=="World Air Quality Index (WAQI)"
    assert snap["source"]["origin"]=="CPCB India"

def test_missing_token_fails_without_simulation(monkeypatch):
    monkeypatch.delenv("WAQI_TOKEN",raising=False)
    try: aqi_data.current_snapshot(aqi_data.CITIES[2]); assert False
    except RuntimeError as exc: assert "WAQI_TOKEN" in str(exc)

def test_history_is_not_fabricated():
    assert aqi_data.history(aqi_data.CITIES[2],"24h")==[]
