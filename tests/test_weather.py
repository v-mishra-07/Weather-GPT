import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_still_works():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_weather_invalid_latitude():
    r = client.get("/api/weather?latitude=999&longitude=77.23")
    assert r.status_code == 422


def test_weather_invalid_longitude():
    r = client.get("/api/weather?latitude=28.61&longitude=999")
    assert r.status_code == 422


def test_weather_missing_params():
    r = client.get("/api/weather")
    assert r.status_code == 422


def test_weather_valid_request():
    """
    Valid request should return one of:
    - 200: success (Open-Meteo reachable and within rate limit)
    - 502: upstream weather API unreachable or rate-limited (HTTP 429)
    - 504: upstream weather API timed out
    On a machine with internet access and within Open-Meteo free-tier limits, returns 200.
    """
    r = client.get("/api/weather?latitude=28.61&longitude=77.23")
    assert r.status_code in (200, 502, 503, 504)
    if r.status_code == 200:
        d = r.json()
        for k in ["temperature", "humidity", "wind_speed", "rain_probability", "condition", "location"]:
            assert k in d
        assert d["latitude"] == 28.61
        assert d["longitude"] == 77.23


# ── Cache helper unit tests ────────────────────────────────────────────────────

def test_cache_helpers_set_and_get():
    """_cache_set and _cache_get should store and retrieve values."""
    from app.services.weather_service import _cache_get, _cache_set
    store = {}
    _cache_set(store, "mykey", "myvalue")
    assert _cache_get(store, "mykey") == "myvalue"


def test_cache_helpers_expiry():
    """_cache_get should return None for an expired entry."""
    import time
    from app.services.weather_service import _cache_get, _cache_set
    store = {}
    _cache_set(store, "k", "v")
    # Manually backdate the timestamp so it looks expired
    store["k"] = (time.time() - 9999, "v")
    assert _cache_get(store, "k") is None


def test_cache_fallback_on_upstream_error():
    """When upstream fails with 429, stale cached data is returned instead of raising."""
    from app.services.weather_service import _weather_cache, _cache_set, _round_coord
    import asyncio
    import httpx
    from unittest.mock import MagicMock, AsyncMock, patch
    from app.models.schemas import WeatherResponse

    # Seed the cache with fake data for coords (1.0, 2.0)
    fake = WeatherResponse(
        location="CacheCity", latitude=1.0, longitude=2.0,
        temperature=25.0, feels_like=26.0, humidity=50,
        wind_speed=10.0, rain_probability=5, condition="Clear Sky",
    )
    key = (_round_coord(1.0), _round_coord(2.0))
    _cache_set(_weather_cache, key, fake)

    # Build a mock response that raises HTTPStatusError when raise_for_status() is called
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "429 Too Many Requests", request=MagicMock(), response=mock_response
    )

    async def _fake_get(*args, **kwargs):
        return mock_response

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = _fake_get

    with patch("app.services.weather_service.httpx.AsyncClient", return_value=mock_client):
        from app.services.weather_service import get_current_weather
        result = asyncio.run(get_current_weather(1.0, 2.0))

    assert result.location == "CacheCity"
    assert result.temperature == 25.0


# ── WeatherAPI fallback tests ──────────────────────────────────────────────────

def test_openmeteo_429_triggers_weatherapi_fallback(monkeypatch):
    """When Open-Meteo returns 429, WeatherAPI fallback is attempted."""
    import asyncio, httpx
    from unittest.mock import AsyncMock, MagicMock, patch
    from app.services import weather_service
    from app.config import settings

    # Patch settings so weatherapi_key appears configured
    monkeypatch.setattr(settings, "weatherapi_key", "test_key_not_real")

    # Track which providers were called
    calls = []

    async def fake_openmeteo(*args, **kwargs):
        calls.append("openmeteo")
        raise httpx.HTTPStatusError("429", request=MagicMock(), response=MagicMock(status_code=429))

    async def fake_weatherapi(*args, **kwargs):
        calls.append("weatherapi")
        from app.models.schemas import WeatherResponse
        return WeatherResponse(
            location="FallbackCity", latitude=28.61, longitude=77.23,
            temperature=31.0, feels_like=33.0, humidity=65,
            wind_speed=12.0, rain_probability=20, condition="Partly Cloudy",
        )

    monkeypatch.setattr(weather_service, "_fetch_openmeteo_current", fake_openmeteo)
    monkeypatch.setattr(weather_service, "_fetch_weatherapi_current", fake_weatherapi)

    result = asyncio.run(weather_service.get_current_weather(28.61, 77.23))
    assert "openmeteo" in calls
    assert "weatherapi" in calls
    assert result.location == "FallbackCity"
    assert result.temperature == 31.0


def test_openmeteo_success_does_not_call_weatherapi(monkeypatch):
    """When Open-Meteo succeeds, WeatherAPI is never called."""
    import asyncio
    from app.services import weather_service
    from app.models.schemas import WeatherResponse

    calls = []

    async def fake_openmeteo(*args, **kwargs):
        calls.append("openmeteo")
        return WeatherResponse(
            location="PrimaryCity", latitude=1.0, longitude=2.0,
            temperature=25.0, feels_like=26.0, humidity=50,
            wind_speed=10.0, rain_probability=5, condition="Clear Sky",
        )

    async def fake_weatherapi(*args, **kwargs):
        calls.append("weatherapi")
        raise AssertionError("Should not be called")

    monkeypatch.setattr(weather_service, "_fetch_openmeteo_current", fake_openmeteo)
    monkeypatch.setattr(weather_service, "_fetch_weatherapi_current", fake_weatherapi)

    result = asyncio.run(weather_service.get_current_weather(1.0, 2.0))
    assert calls == ["openmeteo"]
    assert result.location == "PrimaryCity"


def test_both_providers_fail_raises(monkeypatch):
    """When both providers fail and cache is empty, an exception is raised."""
    import asyncio, httpx
    from unittest.mock import MagicMock
    from app.services import weather_service
    from app.config import settings

    monkeypatch.setattr(settings, "weatherapi_key", "test_key_not_real")

    async def fail(*args, **kwargs):
        raise httpx.RequestError("connection error")

    monkeypatch.setattr(weather_service, "_fetch_openmeteo_current", fail)
    monkeypatch.setattr(weather_service, "_fetch_weatherapi_current", fail)

    # Clear cache for these coords
    key = (weather_service._round_coord(55.0), weather_service._round_coord(66.0))
    weather_service._weather_cache.pop(key, None)

    with pytest.raises(httpx.RequestError):
        asyncio.run(weather_service.get_current_weather(55.0, 66.0))


def test_both_providers_fail_uses_cache(monkeypatch):
    """When both providers fail but cache has data, cached data is returned."""
    import asyncio, httpx, time
    from app.services import weather_service
    from app.models.schemas import WeatherResponse
    from app.config import settings

    monkeypatch.setattr(settings, "weatherapi_key", "test_key_not_real")

    # Seed cache
    fake = WeatherResponse(
        location="CachedCity", latitude=77.0, longitude=88.0,
        temperature=22.0, feels_like=23.0, humidity=60,
        wind_speed=8.0, rain_probability=10, condition="Mainly Clear",
    )
    key = (weather_service._round_coord(77.0), weather_service._round_coord(88.0))
    weather_service._cache_set(weather_service._weather_cache, key, fake)

    async def fail(*args, **kwargs):
        raise httpx.RequestError("connection error")

    monkeypatch.setattr(weather_service, "_fetch_openmeteo_current", fail)
    monkeypatch.setattr(weather_service, "_fetch_weatherapi_current", fail)

    result = asyncio.run(weather_service.get_current_weather(77.0, 88.0))
    assert result.location == "CachedCity"
    assert result.temperature == 22.0


def test_weatherapi_condition_normalisation():
    """_normalise_weatherapi_condition should map known strings correctly."""
    from app.services.weather_service import _normalise_weatherapi_condition
    assert _normalise_weatherapi_condition("Patchy rain possible") == "Light Drizzle"
    assert _normalise_weatherapi_condition("Thundery outbreaks possible") == "Thunderstorm"
    assert _normalise_weatherapi_condition("Sunny") == "Clear Sky"
    assert _normalise_weatherapi_condition("Overcast") == "Overcast"
    assert _normalise_weatherapi_condition("Heavy rain") == "Heavy Rain"


def test_response_shape_preserved(monkeypatch):
    """Whether Open-Meteo or WeatherAPI serves the data, all required fields must be present."""
    import asyncio
    from app.services import weather_service
    from app.models.schemas import WeatherResponse

    async def fake_openmeteo(*args, **kwargs):
        return WeatherResponse(
            location="ShapeCity", latitude=10.0, longitude=20.0,
            temperature=30.0, feels_like=32.0, humidity=70,
            wind_speed=15.0, rain_probability=80, condition="Thunderstorm",
        )

    monkeypatch.setattr(weather_service, "_fetch_openmeteo_current", fake_openmeteo)

    result = asyncio.run(weather_service.get_current_weather(10.0, 20.0))
    for field in ["location", "latitude", "longitude", "temperature", "feels_like",
                  "humidity", "wind_speed", "rain_probability", "condition"]:
        assert hasattr(result, field), f"Missing field: {field}"


# ── HTTPS URL tests ────────────────────────────────────────────────────────────

def test_weatherapi_urls_use_https():
    """Both WeatherAPI URL constants must use HTTPS to protect the API key in transit."""
    from app.services.weather_service import WEATHERAPI_CURRENT_URL, WEATHERAPI_FORECAST_URL
    assert WEATHERAPI_CURRENT_URL.startswith("https://"), (
        f"WEATHERAPI_CURRENT_URL must use https://, got: {WEATHERAPI_CURRENT_URL}"
    )
    assert WEATHERAPI_FORECAST_URL.startswith("https://"), (
        f"WEATHERAPI_FORECAST_URL must use https://, got: {WEATHERAPI_FORECAST_URL}"
    )


# ── Forecast fallback tests ────────────────────────────────────────────────────

def test_openmeteo_429_triggers_weatherapi_forecast_fallback(monkeypatch):
    """When Open-Meteo forecast returns 429, WeatherAPI forecast fallback is attempted."""
    import asyncio, httpx
    from unittest.mock import MagicMock
    from app.services import weather_service
    from app.config import settings
    from app.models.schemas import ForecastResponse, ForecastDay

    # Patch settings so weatherapi_key appears configured
    monkeypatch.setattr(settings, "weatherapi_key", "test_key_not_real")

    calls = []

    async def fake_openmeteo_forecast(*args, **kwargs):
        calls.append("openmeteo")
        raise httpx.HTTPStatusError(
            "429 Too Many Requests",
            request=MagicMock(),
            response=MagicMock(status_code=429),
        )

    async def fake_weatherapi_forecast(*args, **kwargs):
        calls.append("weatherapi")
        return ForecastResponse(
            location="FallbackForecastCity",
            latitude=28.61,
            longitude=77.23,
            days=[
                ForecastDay(
                    date="2026-09-29",
                    max_temp=36.0,
                    min_temp=24.0,
                    precipitation_mm=2.5,
                    rain_probability=60,
                    wind_speed=18.0,
                    condition="Moderate Rain",
                )
            ],
        )

    monkeypatch.setattr(weather_service, "_fetch_openmeteo_forecast", fake_openmeteo_forecast)
    monkeypatch.setattr(weather_service, "_fetch_weatherapi_forecast", fake_weatherapi_forecast)

    result = asyncio.run(weather_service.get_forecast(28.61, 77.23, days=7))
    assert "openmeteo" in calls
    assert "weatherapi" in calls
    assert result.location == "FallbackForecastCity"
    assert len(result.days) == 1
    assert result.days[0].condition == "Moderate Rain"
    assert result.days[0].rain_probability == 60


def test_openmeteo_forecast_success_does_not_call_weatherapi(monkeypatch):
    """When Open-Meteo forecast succeeds, WeatherAPI forecast is never called."""
    import asyncio
    from app.services import weather_service
    from app.models.schemas import ForecastResponse, ForecastDay

    calls = []

    async def fake_openmeteo_forecast(*args, **kwargs):
        calls.append("openmeteo")
        return ForecastResponse(
            location="PrimaryForecastCity",
            latitude=1.0,
            longitude=2.0,
            days=[
                ForecastDay(
                    date="2026-09-29",
                    max_temp=28.0,
                    min_temp=18.0,
                    precipitation_mm=0.0,
                    rain_probability=5,
                    wind_speed=10.0,
                    condition="Clear Sky",
                )
            ],
        )

    async def fake_weatherapi_forecast(*args, **kwargs):
        calls.append("weatherapi")
        raise AssertionError("Should not be called when Open-Meteo succeeds")

    monkeypatch.setattr(weather_service, "_fetch_openmeteo_forecast", fake_openmeteo_forecast)
    monkeypatch.setattr(weather_service, "_fetch_weatherapi_forecast", fake_weatherapi_forecast)

    result = asyncio.run(weather_service.get_forecast(1.0, 2.0, days=7))
    assert calls == ["openmeteo"]
    assert result.location == "PrimaryForecastCity"


def test_both_forecast_providers_fail_raises(monkeypatch):
    """When both forecast providers fail and cache is empty, an exception is raised."""
    import asyncio, httpx
    from app.services import weather_service
    from app.config import settings

    monkeypatch.setattr(settings, "weatherapi_key", "test_key_not_real")

    async def fail(*args, **kwargs):
        raise httpx.RequestError("connection error")

    monkeypatch.setattr(weather_service, "_fetch_openmeteo_forecast", fail)
    monkeypatch.setattr(weather_service, "_fetch_weatherapi_forecast", fail)

    # Clear cache for these coords+days
    key = (weather_service._round_coord(33.0), weather_service._round_coord(44.0), 7)
    weather_service._forecast_cache.pop(key, None)

    with pytest.raises(httpx.RequestError):
        asyncio.run(weather_service.get_forecast(33.0, 44.0, days=7))


def test_both_forecast_providers_fail_uses_cache(monkeypatch):
    """When both forecast providers fail but cache has data, cached data is returned."""
    import asyncio, httpx
    from app.services import weather_service
    from app.models.schemas import ForecastResponse, ForecastDay
    from app.config import settings

    monkeypatch.setattr(settings, "weatherapi_key", "test_key_not_real")

    fake = ForecastResponse(
        location="CachedForecastCity",
        latitude=50.0,
        longitude=60.0,
        days=[
            ForecastDay(
                date="2026-09-29",
                max_temp=22.0,
                min_temp=14.0,
                precipitation_mm=0.0,
                rain_probability=10,
                wind_speed=8.0,
                condition="Mainly Clear",
            )
        ],
    )
    key = (weather_service._round_coord(50.0), weather_service._round_coord(60.0), 7)
    weather_service._cache_set(weather_service._forecast_cache, key, fake)

    async def fail(*args, **kwargs):
        raise httpx.RequestError("connection error")

    monkeypatch.setattr(weather_service, "_fetch_openmeteo_forecast", fail)
    monkeypatch.setattr(weather_service, "_fetch_weatherapi_forecast", fail)

    result = asyncio.run(weather_service.get_forecast(50.0, 60.0, days=7))
    assert result.location == "CachedForecastCity"
    assert result.days[0].condition == "Mainly Clear"
