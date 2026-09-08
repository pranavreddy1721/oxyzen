"""OxyZen backend API tests (pytest)."""
import os
import re
import uuid
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")
API = f"{BASE_URL}/api"

POLLUTANTS = ["pm25", "pm10", "o3", "no2", "so2", "co"]


@pytest.fixture(scope="session")
def creds():
    p = Path("/app/memory/test_credentials.md")
    if not p.exists():
        pytest.skip("missing test_credentials.md")
    t = p.read_text()
    emails = re.findall(r'Email:\s*(\S+)', t)
    pwds = re.findall(r'Password:\s*(\S+)', t)
    return {"admin": (emails[0], pwds[0]), "demo": (emails[1], pwds[1])}


@pytest.fixture(scope="session")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# --- module: root/health ---
class TestHealth:
    def test_root(self, client):
        r = client.get(f"{API}/")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


# --- module: aqi_data / AQI endpoints ---
class TestAQI:
    def test_current(self, client):
        r = client.get(f"{API}/aqi/current", params={"locationId": "delhi"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert isinstance(d["aqi"], int) and 0 <= d["aqi"] <= 500
        assert isinstance(d["category"], str) and d["category"]
        assert set(POLLUTANTS).issubset(d["pollutants"].keys())
        assert set(POLLUTANTS).issubset(d["pollutantMeta"].keys())
        assert isinstance(d["scale"], list) and len(d["scale"]) >= 5
        assert "_id" not in d

    def test_current_deterministic(self, client):
        a = client.get(f"{API}/aqi/current", params={"locationId": "delhi"}).json()
        b = client.get(f"{API}/aqi/current", params={"locationId": "delhi"}).json()
        assert a["aqi"] == b["aqi"]

    def test_current_by_coords(self, client):
        r = client.get(f"{API}/aqi/current", params={"lat": 28.61, "lon": 77.21})
        assert r.status_code == 200
        assert "aqi" in r.json()

    def test_current_no_location_400(self, client):
        r = client.get(f"{API}/aqi/current")
        assert r.status_code == 400

    @pytest.mark.parametrize("rng,minpts", [("24h", 12), ("7d", 5), ("30d", 20)])
    def test_history(self, client, rng, minpts):
        r = client.get(f"{API}/aqi/history", params={"locationId": "delhi", "range": rng})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["range"] == rng
        assert len(d["points"]) >= minpts
        p = d["points"][0]
        assert "label" in p and "aqi" in p
        for k in POLLUTANTS:
            assert k in p

    def test_history_invalid_range_fallback(self, client):
        r = client.get(f"{API}/aqi/history", params={"locationId": "delhi", "range": "bogus"})
        assert r.status_code == 200
        assert r.json()["range"] == "24h"

    def test_forecast(self, client):
        r = client.get(f"{API}/aqi/forecast", params={"locationId": "delhi"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert len(d["forecast"]) >= 2
        f = d["forecast"][0]
        assert "aqi" in f and "trend" in f and "category" in f

    @pytest.mark.parametrize("pol", POLLUTANTS)
    def test_pollutant_detail(self, client, pol):
        r = client.get(f"{API}/aqi/pollutant/{pol}", params={"locationId": "delhi"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["meta"]["reference"] == d["reference"]
        assert isinstance(d["current"], (int, float))
        assert d["severity"] in ("Good", "Moderate", "High", "Very High")
        assert len(d["trend"]) > 0 and "value" in d["trend"][0]

    def test_pollutant_unknown_404(self, client):
        r = client.get(f"{API}/aqi/pollutant/xyz", params={"locationId": "delhi"})
        assert r.status_code == 404


# --- module: location ---
class TestLocation:
    def test_search(self, client):
        r = client.get(f"{API}/location/search", params={"q": "mum"})
        assert r.status_code == 200
        res = r.json()["results"]
        assert len(res) > 0
        assert any("mumbai" in c["name"].lower() for c in res)
        for k in ("id", "name", "country", "lat", "lon"):
            assert k in res[0]

    def test_search_empty(self, client):
        r = client.get(f"{API}/location/search", params={"q": ""})
        assert r.status_code == 200
        assert isinstance(r.json()["results"], list)

    def test_reverse_known(self, client):
        r = client.get(f"{API}/location/reverse", params={"lat": 19.07, "lon": 72.87})
        assert r.status_code == 200
        assert "mumbai" in r.json()["location"]["name"].lower()

    def test_reverse_remote(self, client):
        r = client.get(f"{API}/location/reverse", params={"lat": -40.5, "lon": -120.5})
        assert r.status_code == 200
        assert r.json()["location"]["id"]

    def test_reverse_missing_params_422(self, client):
        r = client.get(f"{API}/location/reverse")
        assert r.status_code == 422


# --- module: health_risk ---
class TestHealthRisk:
    def test_health_risk(self, client):
        r = client.get(f"{API}/health-risk", params={"locationId": "delhi"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["riskLevel"] in ("LOW", "MODERATE", "ELEVATED", "HIGH", "SEVERE")
        assert 0 <= d["riskScore"] <= 100
        assert len(d["mainContributors"]) > 0
        c = d["mainContributors"][0]
        assert "label" in c or "name" in c
        assert isinstance(d["explanation"], str) and len(d["explanation"]) > 10
        assert len(d["healthImpacts"]) > 0
        assert len(d["precautions"]) > 0
        assert d["activityGuidance"]
        assert d["location"]["id"] == "delhi"

    def test_low_vs_high_ordering(self, client):
        d = client.get(f"{API}/health-risk", params={"locationId": "delhi"}).json()
        z = client.get(f"{API}/health-risk", params={"locationId": "zurich"}).json()
        if z.get("riskScore") is not None:
            assert d["riskScore"] >= z["riskScore"]

    @pytest.mark.parametrize("aqi", [20, 90, 180, 320])
    def test_exposure(self, client, aqi):
        r = client.post(f"{API}/exposure", json={"aqi": aqi, "environment": "outdoor",
                                                "activity": "running", "duration": "3-8h"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["level"] and d["text"]
        assert isinstance(d["tips"], list) and len(d["tips"]) > 0

    def test_exposure_validation(self, client):
        r = client.post(f"{API}/exposure", json={"aqi": "abc"})
        assert r.status_code == 422


# --- module: map ---
class TestMap:
    def test_map(self, client):
        r = client.get(f"{API}/map")
        assert r.status_code == 200
        d = r.json()
        assert len(d["locations"]) == 24
        loc = d["locations"][0]
        for k in ("id", "name", "lat", "lon", "aqi", "color", "category"):
            assert k in loc, f"missing {k}"
        assert loc["color"].startswith("#")


# --- module: auth ---
class TestAuth:
    def test_login_admin(self, client, creds):
        email, pwd = creds["admin"]
        r = requests.post(f"{API}/auth/login", json={"email": email, "password": pwd})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["user"]["email"] == email
        assert d["user"]["role"] == "admin"
        assert isinstance(d["token"], str) and len(d["token"]) > 20
        # httpOnly cookies
        cookies = r.cookies
        assert "access_token" in cookies and "refresh_token" in cookies
        raw = r.headers.get("set-cookie", "")
        assert "HttpOnly" in raw

    def test_login_demo(self, client, creds):
        email, pwd = creds["demo"]
        r = requests.post(f"{API}/auth/login", json={"email": email, "password": pwd})
        assert r.status_code == 200, r.text
        assert r.json()["user"]["email"] == email

    def test_login_wrong_password(self, client, creds):
        email, _ = creds["admin"]
        r = requests.post(f"{API}/auth/login", json={"email": email, "password": "WrongPass!1"})
        assert r.status_code == 401

    def test_login_unknown_email(self, client):
        r = requests.post(f"{API}/auth/login", json={"email": "nobody_x@oxyzen.app", "password": "x"})
        assert r.status_code == 401

    def test_bcrypt_hash_format(self):
        import sys
        sys.path.insert(0, "/app/backend")
        from auth import hash_password
        h = hash_password("test123")
        assert h.startswith("$2b$"), f"unexpected hash prefix: {h[:4]}"

    def test_register_and_me_and_logout(self):
        s = requests.Session()
        email = f"TEST_qa_{uuid.uuid4().hex[:8]}@qa-oxyzen.com"
        r = s.post(f"{API}/auth/register", json={"name": "TEST QA", "email": email, "password": "QaPass@2026"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["user"]["email"] == email.lower()
        assert d["user"]["alertThreshold"] == 150
        token = d["token"]
        # me with bearer
        m = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert m.status_code == 200
        assert m.json()["user"]["email"] == email.lower()
        # duplicate register
        dup = requests.post(f"{API}/auth/register", json={"name": "x", "email": email, "password": "QaPass@2026"})
        assert dup.status_code == 400
        # refresh with cookie session
        rf = s.post(f"{API}/auth/refresh")
        assert rf.status_code == 200, rf.text
        assert rf.json()["token"]
        # alerts patch
        pa = requests.patch(f"{API}/auth/alerts", json={"threshold": 90, "enabled": False},
                            headers={"Authorization": f"Bearer {token}"})
        assert pa.status_code == 200, pa.text
        assert pa.json()["user"]["alertThreshold"] == 90
        assert pa.json()["user"]["alertsEnabled"] is False
        # verify persisted
        m2 = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert m2.json()["user"]["alertThreshold"] == 90
        # logout
        lo = s.post(f"{API}/auth/logout")
        assert lo.status_code == 200

    def test_register_weak_password_422(self):
        r = requests.post(f"{API}/auth/register", json={"name": "x", "email": f"TEST_w{uuid.uuid4().hex[:6]}@qa-oxyzen.com", "password": "123"})
        assert r.status_code == 422

    def test_register_bad_email_422(self):
        r = requests.post(f"{API}/auth/register", json={"name": "x", "email": "not-an-email", "password": "QaPass@2026"})
        assert r.status_code == 422

    def test_me_no_token_401(self):
        r = requests.get(f"{API}/auth/me")
        assert r.status_code == 401

    def test_me_malformed_token_401(self):
        r = requests.get(f"{API}/auth/me", headers={"Authorization": "Bearer abc.def.ghi"})
        assert r.status_code == 401, f"expected 401 got {r.status_code}: {r.text[:200]}"

    def test_refresh_token_used_as_access_401(self):
        s = requests.Session()
        email = f"TEST_rt_{uuid.uuid4().hex[:8]}@qa-oxyzen.com"
        s.post(f"{API}/auth/register", json={"name": "t", "email": email, "password": "QaPass@2026"})
        rtok = s.cookies.get("refresh_token")
        r = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {rtok}"})
        assert r.status_code == 401

    def test_brute_force_lockout(self, creds):
        """Playbook: lockout expected after 5 consecutive failures."""
        email = f"TEST_bf_{uuid.uuid4().hex[:8]}@qa-oxyzen.com"
        requests.post(f"{API}/auth/register", json={"name": "bf", "email": email, "password": "QaPass@2026"})
        codes = []
        for _ in range(6):
            codes.append(requests.post(f"{API}/auth/login", json={"email": email, "password": "bad"}).status_code)
        assert 423 in codes or 429 in codes, f"no lockout after 6 failures, codes={codes}"


# --- module: saved locations + dashboard ---
class TestSavedLocations:
    @pytest.fixture(scope="class")
    def auth(self):
        email = f"TEST_sl_{uuid.uuid4().hex[:8]}@qa-oxyzen.com"
        r = requests.post(f"{API}/auth/register", json={"name": "TEST SL", "email": email, "password": "QaPass@2026"})
        assert r.status_code == 200, r.text
        s = requests.Session()
        s.headers.update({"Authorization": f"Bearer {r.json()['token']}"})
        return s

    def test_requires_auth(self):
        assert requests.get(f"{API}/users/locations").status_code == 401
        assert requests.get(f"{API}/users/dashboard").status_code == 401
        assert requests.post(f"{API}/users/locations", json={"locationId": "delhi", "name": "Delhi", "lat": 1, "lon": 1}).status_code == 401

    def test_crud_flow(self, auth):
        payload = {"locationId": "delhi", "name": "Delhi", "country": "India",
                   "lat": 28.61, "lon": 77.21, "label": "TEST_home"}
        c = auth.post(f"{API}/users/locations", json=payload)
        assert c.status_code == 200, c.text
        lid = c.json()["id"]
        assert c.json()["locationId"] == "delhi"
        # duplicate
        assert auth.post(f"{API}/users/locations", json=payload).status_code == 400
        # list
        g = auth.get(f"{API}/users/locations")
        assert g.status_code == 200
        locs = g.json()["locations"]
        assert any(l["id"] == lid and l["label"] == "TEST_home" for l in locs)
        # dashboard reflects it
        d = auth.get(f"{API}/users/dashboard")
        assert d.status_code == 200, d.text
        dd = d.json()
        assert any(l["id"] == lid for l in dd["savedLocations"])
        sl = [l for l in dd["savedLocations"] if l["id"] == lid][0]
        assert isinstance(sl["aqi"], int) and sl["riskLevel"] and sl["color"].startswith("#")
        assert dd["alertThreshold"] == 150
        assert isinstance(dd["recentSearches"], list)
        # delete
        de = auth.delete(f"{API}/users/locations/{lid}")
        assert de.status_code == 200
        g2 = auth.get(f"{API}/users/locations")
        assert all(l["id"] != lid for l in g2.json()["locations"])
        # delete again -> 404
        assert auth.delete(f"{API}/users/locations/{lid}").status_code == 404

    def test_delete_invalid_objectid(self, auth):
        r = auth.delete(f"{API}/users/locations/not-an-objectid")
        assert r.status_code in (400, 404, 422), f"got {r.status_code}: {r.text[:200]}"


# --- module: AI assistant ---
class TestAI:
    def test_chat_stream(self):
        sid = f"TEST_sess_{uuid.uuid4().hex[:8]}"
        r = requests.post(f"{API}/ai/chat", json={
            "message": "In one sentence, what is PM2.5?",
            "sessionId": sid,
            "context": {"name": "Delhi", "aqi": 210, "category": "Very Unhealthy",
                        "dominantPollutant": "pm25", "riskLevel": "HIGH"},
        }, stream=True, timeout=90)
        assert r.status_code == 200, r.text
        body = ""
        for chunk in r.iter_content(chunk_size=None):
            body += chunk.decode("utf-8", "ignore")
        assert len(body) > 20, f"short AI response: {body!r}"
        assert "having trouble reaching the AI service" not in body, "AI fallback returned - LLM call failed"
        # persisted history
        h = requests.get(f"{API}/ai/history/{sid}")
        assert h.status_code == 200
        msgs = h.json()["messages"]
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[1]["role"] == "assistant" and len(msgs[1]["content"]) > 20

    def test_chat_validation(self):
        r = requests.post(f"{API}/ai/chat", json={"message": "hi"})
        assert r.status_code == 422
