import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import aqi_data

class MockResponse:
    def __init__(self, payload): self.payload = payload
    def raise_for_status(self): return None
    def json(self): return self.payload

def sample_payload():
    return {"status":"ok","data":{"aqi":42,"dominentpol":"pm25","iaqi":{"pm25":{"v":42},"pm10":{"v":30},"o3":{"v":18}},"city":{"name":"Kolhapur","url":"https://aqicn.org/city/kolhapur/","geo":[16.705,74.2433]},"time":{"iso":datetime.now(timezone.utc).isoformat()},"attributions":[{"name":"CPCB India","url":"https://cpcb.nic.in/"}]}}

def test_current_snapshot_uses_waqi(monkeypatch):
    monkeypatch.setenv("WAQI_TOKEN","test-token")
    monkeypatch.setattr(aqi_data.requests,"get",lambda *a,**k: MockResponse(sample_payload()))
    snap=aqi_data.current_snapshot(aqi_data.CITIES[2])
    assert snap["aqi"]==42
    assert snap["pollutants"]["pm25"]==42
    assert snap["source"]["provider"]=="World Air Quality Index (WAQI)"
    assert snap["source"]["origin"]=="CPCB India"

def test_missing_token_uses_model_fallback_or_reports_unavailable(monkeypatch, caplog):
    monkeypatch.delenv("WAQI_TOKEN", raising=False)
    def no_model_data(_loc):
        raise RuntimeError("Open-Meteo test fixture has no current AQI")
    monkeypatch.setattr(aqi_data, "_open_meteo_snapshot", no_model_data)
    snap = aqi_data.current_snapshot(aqi_data.CITIES[2])
    assert snap["aqi"] is None
    assert snap["category"] == "Unavailable"
    assert snap["source"]["provider"] == "Unavailable"
    assert "WAQI_TOKEN is not configured" in caplog.text

def test_history_is_not_fabricated():
    assert aqi_data.history(aqi_data.CITIES[2],"24h")==[]


def test_decimal_string_aqi_is_normalized(monkeypatch):
    payload = {
        "aqi": "23.0",
        "iaqi": {"pm25": {"v": 23}},
        "city": {"name": "Test station"},
        "time": {"iso": "2026-11-27T06:00:00+00:00"},
    }
    monkeypatch.setattr(aqi_data, "_resolve_feed", lambda _loc: (payload, 0, 16.7, 74.2))
    snapshot = aqi_data.current_snapshot(aqi_data.CITIES[2])
    assert snapshot["aqi"] == 23


def test_missing_aggregate_aqi_uses_highest_pollutant_subindex():
    payload = {"iaqi": {"pm25": {"v": 35.2}, "pm10": {"v": 51.7}}}
    assert aqi_data._has_usable_aqi(payload) is True
    assert payload["aqi"] == 52
    assert payload["_aqiDerivedFromPollutantSubindices"] is True
