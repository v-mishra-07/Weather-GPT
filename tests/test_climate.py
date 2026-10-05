"""
tests/test_climate.py - Tests for the climate/historical endpoint and service
"""

from fastapi.testclient import TestClient
from app.main import app
from app.services.climate_service import _build_summary

client = TestClient(app)


# --- Unit tests for _build_summary ---

def test_summary_hot_conditions():
    s = _build_summary(42, 28, 50, 5, 30, "Delhi")
    assert "Delhi" in s
    assert "hot" in s.lower() or "42" in s


def test_summary_dry_period():
    s = _build_summary(30, 20, 0, 0, 30, "Jaipur")
    assert "dry" in s.lower() or "no significant" in s.lower()


def test_summary_heavy_rainfall():
    s = _build_summary(28, 22, 300, 20, 30, "Mumbai")
    assert "rain" in s.lower()
    assert "20" in s


def test_summary_mild_conditions():
    s = _build_summary(22, 12, 10, 2, 30, "Shimla")
    assert "Shimla" in s


def test_summary_returns_string():
    s = _build_summary(30, 20, 50, 10, 30, "TestCity")
    assert isinstance(s, str)
    assert len(s) > 0


# --- API endpoint tests ---

def test_climate_missing_params():
    r = client.get("/api/climate")
    assert r.status_code == 422


def test_climate_invalid_latitude():
    r = client.get("/api/climate?latitude=999&longitude=77.23")
    assert r.status_code == 422


def test_climate_invalid_longitude():
    r = client.get("/api/climate?latitude=28.61&longitude=999")
    assert r.status_code == 422


def test_climate_days_too_low():
    r = client.get("/api/climate?latitude=28.61&longitude=77.23&days=3")
    assert r.status_code == 422


def test_climate_days_too_high():
    r = client.get("/api/climate?latitude=28.61&longitude=77.23&days=100")
    assert r.status_code == 422


def test_climate_valid_request():
    r = client.get("/api/climate?latitude=28.61&longitude=77.23&days=30")
    assert r.status_code == 200
    d = r.json()
    assert "location" in d
    assert "avg_max_temp" in d
    assert "avg_min_temp" in d
    assert "total_rainfall_mm" in d
    assert "rainy_days" in d
    assert "summary" in d
    assert d["days"] == 30


def test_climate_default_days():
    r = client.get("/api/climate?latitude=28.61&longitude=77.23")
    assert r.status_code == 200
    assert r.json()["days"] == 30


def test_climate_custom_days():
    r = client.get("/api/climate?latitude=28.61&longitude=77.23&days=7")
    assert r.status_code == 200
    assert r.json()["days"] == 7
