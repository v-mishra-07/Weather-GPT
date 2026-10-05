"""
tests/test_alerts.py - Tests for the alerts endpoint and alert service
"""

from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import WeatherResponse
from app.services.alert_service import check_alerts

client = TestClient(app)


# --- Unit tests for alert_service logic (no HTTP calls needed) ---

def _make_weather(**kwargs) -> WeatherResponse:
    """Helper: build a WeatherResponse with sensible defaults, override with kwargs."""
    defaults = dict(
        location="TestCity", latitude=28.61, longitude=77.23,
        temperature=28.0, feels_like=30.0, humidity=60,
        wind_speed=15.0, rain_probability=10, condition="Partly Cloudy",
    )
    defaults.update(kwargs)
    return WeatherResponse(**defaults)


def test_no_alert_normal_conditions():
    w = _make_weather(rain_probability=10, wind_speed=15, temperature=28)
    result = check_alerts(w)
    assert result.has_alert is False
    assert result.severity is None


def test_heavy_rain_alert():
    w = _make_weather(rain_probability=85)
    result = check_alerts(w)
    assert result.has_alert is True
    assert result.severity == "high"
    assert result.type == "heavy_rain"


def test_moderate_rain_alert():
    w = _make_weather(rain_probability=60)
    result = check_alerts(w)
    assert result.has_alert is True
    assert result.severity == "medium"
    assert result.type == "rain"


def test_strong_wind_high():
    w = _make_weather(wind_speed=65)
    result = check_alerts(w)
    assert result.has_alert is True
    assert result.severity == "high"
    assert result.type == "strong_wind"


def test_extreme_heat_alert():
    w = _make_weather(temperature=44)
    result = check_alerts(w)
    assert result.has_alert is True
    assert result.severity == "high"
    assert result.type == "extreme_heat"


def test_cold_wave_alert():
    w = _make_weather(temperature=3)
    result = check_alerts(w)
    assert result.has_alert is True
    assert result.severity == "medium"
    assert result.type == "cold_wave"


# --- API endpoint tests ---

def test_alerts_missing_params():
    r = client.get("/api/alerts")
    assert r.status_code == 422


def test_alerts_invalid_latitude():
    r = client.get("/api/alerts?latitude=999&longitude=77.23")
    assert r.status_code == 422


def test_alerts_valid_request():
    """
    Valid request should return one of:
    - 200: success (Open-Meteo reachable and within rate limit)
    - 502: upstream weather API unreachable or rate-limited (HTTP 429)
    - 504: upstream weather API timed out
    On a machine with internet access and within Open-Meteo free-tier limits, returns 200.
    """
    r = client.get("/api/alerts?latitude=28.61&longitude=77.23")
    assert r.status_code in (200, 502, 504)
    if r.status_code == 200:
        d = r.json()
        assert "has_alert" in d
        assert "severity" in d
        assert "type" in d
        assert "message" in d
