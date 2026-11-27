"""Unit tests for source-aware pollutant enrichment and risk scoring."""
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import aqi_data
import health_risk


def test_aqi_only_mode_does_not_turn_missing_pollutants_into_zero_risk():
    result = health_risk.assess(107, {})
    assert result["scoreMode"] == "aqi_only"
    assert result["riskScore"] == 43
    assert result["riskLevel"] == "ELEVATED"
    assert result["dataCompleteness"] == {"available": 0, "total": 6, "percentage": 0, "stationMeasurements": 0, "modelledEstimates": 0, "unclassified": 0}
    assert result["mainContributors"][0]["name"] == "AQI"
    assert "not treated as zero" in result["explanation"]


def test_weighted_mode_requires_two_pollutants_and_a_particulate():
    insufficient = health_risk.assess(107, {"o3": 120})
    assert insufficient["scoreMode"] == "aqi_only"

    enough = health_risk.assess(107, {"pm25": 107, "pm10": 107})
    assert enough["scoreMode"] == "pollutant_weighted"
    assert enough["dataCompleteness"]["available"] == 2
    assert 0 <= enough["riskScore"] <= 100


def test_missing_pollutant_values_are_not_counted_as_zero():
    result = health_risk.assess(107, {"pm25": 107, "pm10": None, "o3": "unknown"})
    assert result["scoreMode"] == "aqi_only"
    assert result["dataCompleteness"]["available"] == 1


def test_open_meteo_subindices_are_timestamp_aligned_and_source_independent():
    payload = {
        "hourly": {
            "time": ["2026-11-27T10:00", "2026-11-27T11:00"],
            "us_aqi_pm2_5": [88, 91],
            "us_aqi_pm10": [45, 48],
            "us_aqi_ozone": [None, 12],
            "us_aqi_nitrogen_dioxide": [None, None],
            "us_aqi_sulphur_dioxide": [None, None],
            "us_aqi_carbon_monoxide": [None, None],
        }
    }
    target = datetime(2026, 11, 27, 10, 20, tzinfo=timezone.utc)
    indices, stamp = aqi_data._open_meteo_pollutant_indices(payload, target)
    assert indices == {"pm25": 88.0, "pm10": 45.0}
    assert stamp == "2026-11-27T10:00:00+00:00"


def test_open_meteo_indices_rejected_when_too_far_from_target_time():
    payload = {
        "hourly": {
            "time": ["2026-11-27T06:00"],
            "us_aqi_pm2_5": [88],
        }
    }
    target = datetime(2026, 11, 27, 10, 0, tzinfo=timezone.utc)
    indices, stamp = aqi_data._open_meteo_pollutant_indices(payload, target)
    assert indices == {}
    assert stamp is None


def test_pollutant_provenance_is_returned_for_explanation():
    sources = {
        "pm25": "WAQI monitoring station sub-index",
        "pm10": "Open-Meteo CAMS model estimate",
    }
    result = health_risk.assess(107, {"pm25": 107, "pm10": 107}, sources, {"provider": "WAQI"})
    assert result["pollutantSources"] == sources
    assert result["aqiSource"]["provider"] == "WAQI"



def test_data_completeness_distinguishes_station_and_modelled_sources():
    pollutants = {
        "pm25": 107, "pm10": 35, "o3": 78,
        "no2": 2, "so2": 3, "co": 2,
    }
    model_sources = {key: "Open-Meteo CAMS model estimate" for key in pollutants}
    model_result = health_risk.assess(107, pollutants, model_sources)
    assert model_result["dataCompleteness"]["available"] == 6
    assert model_result["dataCompleteness"]["stationMeasurements"] == 0
    assert model_result["dataCompleteness"]["modelledEstimates"] == 6

    mixed_sources = dict(model_sources)
    mixed_sources["pm25"] = "WAQI monitoring station sub-index"
    mixed_result = health_risk.assess(107, pollutants, mixed_sources)
    assert mixed_result["dataCompleteness"]["stationMeasurements"] == 1
    assert mixed_result["dataCompleteness"]["modelledEstimates"] == 5


def test_unknown_source_is_not_mislabelled_as_station_or_model():
    result = health_risk.assess(107, {"pm25": 107, "pm10": 35}, {})
    assert result["dataCompleteness"]["stationMeasurements"] == 0
    assert result["dataCompleteness"]["modelledEstimates"] == 0
    assert result["dataCompleteness"]["unclassified"] == 2


def test_cpcb_mirror_without_fresh_station_data_returns_unavailable(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"data": [], "meta": {"source": {"attribution": "CPCB monitoring stations"}}}

    monkeypatch.delenv("DATA_GOV_IN_API_KEY", raising=False)
    monkeypatch.setattr(aqi_data.requests, "get", lambda *args, **kwargs: FakeResponse())
    aqi_data._CPCB_CACHE.clear()
    result = aqi_data.cpcb_station_data(
        {"id": "kolhapur", "name": "Kolhapur", "country": "India"}
    )
    assert result["available"] is False
    assert result["stations"] == []
    assert "No fresh CPCB station readings" in result["reason"]


def test_cpcb_mirror_response_is_normalized_to_primary_india_aqi(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            pass
        def json(self):
            return {"data": [
                {"station": "Shivaji University, Kolhapur - MPCB", "city": "Kolhapur", "state": "Maharashtra",
                 "latitude": 16.6870449, "longitude": 74.2505872, "updated": datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M"),
                 "aqi": 80, "category": "Satisfactory", "main_pollutant": "PM10",
                 "pollutants": {"PM10": {"min": 53, "max": 134, "avg": 80},
                                "PM2.5": {"min": 23, "max": 115, "avg": 71},
                                "NO2": {"min": 15, "max": 100, "avg": 42}}},
                {"station": "Sinchan Bhavan, Kolhapur - MPCB", "city": "Kolhapur", "state": "Maharashtra",
                 "latitude": 16.7143745, "longitude": 74.2426398, "updated": "2026-11-27 16:00",
                 "aqi": 73, "category": "Satisfactory", "main_pollutant": "PM2.5",
                 "pollutants": {"PM2.5": {"min": 62, "max": 88, "avg": 73}}}
            ], "meta": {"source": {"attribution": "CPCB monitoring stations"}}}
    monkeypatch.setattr(aqi_data.requests, "get", lambda *args, **kwargs: FakeResponse())
    aqi_data._CPCB_CACHE.clear()
    loc = {"id": "kolhapur", "name": "Kolhapur", "country": "India", "lat": 16.705, "lon": 74.2433}
    data = aqi_data.cpcb_station_data(loc)
    snapshot = aqi_data._cpcb_snapshot(loc, data)
    assert data["available"] is True
    assert len(data["stations"]) == 2
    assert snapshot["aqiScale"] == "india_cpcb"
    assert snapshot["aqi"] in (73, 80)
    assert snapshot["pollutantDataSources"]["pm25"].startswith("CPCB")
    assert snapshot["category"] == "Satisfactory"


def test_india_cpcb_aqi_uses_national_scale_for_awareness_score():
    result = health_risk.assess(80, {"pm25": 71, "pm10": 80},
        {"pm25": "CPCB ground monitoring station sub-index", "pm10": "CPCB ground monitoring station sub-index"},
        {"provider": "CPCB"}, "india_cpcb")
    assert result["aqiScale"] == "india_cpcb"
    assert result["dataCompleteness"]["stationMeasurements"] == 2
