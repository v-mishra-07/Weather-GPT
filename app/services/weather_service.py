import time
import httpx
from app.config import settings
from app.models.schemas import WeatherResponse, ForecastResponse, ForecastDay

WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODE_URL = "https://nominatim.openstreetmap.org/reverse"
WEATHERAPI_CURRENT_URL = "https://api.weatherapi.com/v1/current.json"
WEATHERAPI_FORECAST_URL = "https://api.weatherapi.com/v1/forecast.json"

WMO_CODES = {
    0: "Clear Sky", 1: "Mainly Clear", 2: "Partly Cloudy", 3: "Overcast",
    45: "Foggy", 48: "Icy Fog",
    51: "Light Drizzle", 53: "Moderate Drizzle", 55: "Dense Drizzle",
    61: "Slight Rain", 63: "Moderate Rain", 65: "Heavy Rain",
    71: "Slight Snowfall", 73: "Moderate Snowfall", 75: "Heavy Snowfall",
    80: "Slight Rain Showers", 81: "Moderate Rain Showers", 82: "Violent Rain Showers",
    95: "Thunderstorm", 96: "Thunderstorm with Hail", 99: "Thunderstorm with Heavy Hail",
}

# ── In-memory TTL cache ───────────────────────────────────────────────────────
CACHE_TTL = 300  # 5 minutes

_weather_cache: dict = {}
_forecast_cache: dict = {}


def _round_coord(v: float) -> float:
    return round(v, 2)


def _cache_get(store: dict, key):
    entry = store.get(key)
    if entry is None:
        return None
    ts, value = entry
    if time.time() - ts > CACHE_TTL:
        del store[key]
        return None
    return value


def _cache_set(store: dict, key, value):
    store[key] = (time.time(), value)


# ── WeatherAPI.com condition text → normalised condition string ───────────────

def _normalise_weatherapi_condition(text: str) -> str:
    """Map WeatherAPI condition text to a WeatherGPT-style condition string."""
    t = text.lower()
    if "thunder" in t:
        return "Thunderstorm"
    if "blizzard" in t or "heavy snow" in t:
        return "Heavy Snowfall"
    if "snow" in t or "sleet" in t:
        return "Slight Snowfall"
    if "freezing" in t or "ice" in t:
        return "Icy Fog"
    if "heavy rain" in t or "torrential" in t:
        return "Heavy Rain"
    if "moderate rain" in t:
        return "Moderate Rain"
    if "patchy rain" in t or "light rain" in t or "drizzle" in t:
        return "Light Drizzle"
    if "shower" in t:
        return "Slight Rain Showers"
    if "fog" in t or "mist" in t or "freezing fog" in t:
        return "Foggy"
    if "overcast" in t:
        return "Overcast"
    if "cloudy" in t:
        return "Partly Cloudy"
    if "clear" in t or "sunny" in t:
        return "Clear Sky"
    if "partly cloudy" in t:
        return "Partly Cloudy"
    return text.title()


# ── WeatherAPI.com — current weather ─────────────────────────────────────────

async def _fetch_weatherapi_current(client: httpx.AsyncClient, latitude: float, longitude: float) -> WeatherResponse:
    """Fetch current weather from WeatherAPI.com and normalise to WeatherResponse."""
    r = await client.get(
        WEATHERAPI_CURRENT_URL,
        params={"key": settings.weatherapi_key, "q": f"{latitude},{longitude}", "aqi": "no"},
        timeout=10.0,
    )
    r.raise_for_status()
    d = r.json()

    loc_data = d.get("location", {})
    cur = d.get("current", {})
    loc_name = loc_data.get("name") or loc_data.get("region") or "Unknown Location"
    condition_text = cur.get("condition", {}).get("text", "Unknown")

    return WeatherResponse(
        location=loc_name,
        latitude=latitude,
        longitude=longitude,
        temperature=round(float(cur.get("temp_c", 0)), 1),
        feels_like=round(float(cur.get("feelslike_c", 0)), 1),
        humidity=int(cur.get("humidity", 0)),
        wind_speed=round(float(cur.get("wind_kph", 0)), 1),
        rain_probability=int(cur.get("precip_mm", 0) > 0) * 80,  # WeatherAPI current has no probability; use precip presence
        condition=_normalise_weatherapi_condition(condition_text),
        is_day=int(cur.get("is_day", 1)),
    )


# ── WeatherAPI.com — forecast ─────────────────────────────────────────────────

async def _fetch_weatherapi_forecast(client: httpx.AsyncClient, latitude: float, longitude: float, days: int) -> ForecastResponse:
    """Fetch forecast from WeatherAPI.com and normalise to ForecastResponse."""
    actual_days = min(days, 14)  # WeatherAPI free tier: up to 14 days
    r = await client.get(
        WEATHERAPI_FORECAST_URL,
        params={"key": settings.weatherapi_key, "q": f"{latitude},{longitude}", "days": actual_days, "aqi": "no"},
        timeout=10.0,
    )
    r.raise_for_status()
    d = r.json()

    loc_data = d.get("location", {})
    loc_name = loc_data.get("name") or loc_data.get("region") or "Unknown Location"
    forecast_days = d.get("forecast", {}).get("forecastday", [])

    return ForecastResponse(
        location=loc_name,
        latitude=latitude,
        longitude=longitude,
        days=[
            ForecastDay(
                date=fd["date"],
                max_temp=round(float(fd["day"].get("maxtemp_c", 0)), 1),
                min_temp=round(float(fd["day"].get("mintemp_c", 0)), 1),
                precipitation_mm=round(float(fd["day"].get("totalprecip_mm", 0)), 1),
                rain_probability=int(fd["day"].get("daily_chance_of_rain", 0)),
                wind_speed=round(float(fd["day"].get("maxwind_kph", 0)), 1),
                condition=_normalise_weatherapi_condition(
                    fd["day"].get("condition", {}).get("text", "Unknown")
                ),
            )
            for fd in forecast_days
        ],
    )


# ── Primary: Open-Meteo — current weather ────────────────────────────────────

async def _fetch_openmeteo_current(client: httpx.AsyncClient, latitude: float, longitude: float) -> WeatherResponse:
    """Fetch current weather from Open-Meteo."""
    params = {
        "latitude": latitude, "longitude": longitude,
        "current": [
            "temperature_2m", "apparent_temperature",
            "relative_humidity_2m", "wind_speed_10m",
            "precipitation_probability", "weather_code",
            "is_day",
        ],
        "daily": ["sunrise", "sunset"],
        "wind_speed_unit": "kmh",
        "timezone": "auto",
    }
    r = await client.get(WEATHER_URL, params=params, timeout=10.0)
    r.raise_for_status()
    data = r.json()
    loc = await _reverse_geocode(client, latitude, longitude)

    c = data.get("current", {})
    daily = data.get("daily", {})
    sunrise_list = daily.get("sunrise") or []
    sunset_list  = daily.get("sunset")  or []
    sunrise_val  = sunrise_list[0] if sunrise_list else None
    sunset_val   = sunset_list[0]  if sunset_list  else None

    return WeatherResponse(
        location=loc, latitude=latitude, longitude=longitude,
        temperature=round(float(c.get("temperature_2m", 0)), 1),
        feels_like=round(float(c.get("apparent_temperature", 0)), 1),
        humidity=int(c.get("relative_humidity_2m", 0)),
        wind_speed=round(float(c.get("wind_speed_10m", 0)), 1),
        rain_probability=int(c.get("precipitation_probability", 0)),
        condition=WMO_CODES.get(int(c.get("weather_code", 0)), "Unknown"),
        is_day=int(c.get("is_day", 1)),
        sunrise=sunrise_val,
        sunset=sunset_val,
    )


# ── Primary: Open-Meteo — forecast ───────────────────────────────────────────

async def _fetch_openmeteo_forecast(client: httpx.AsyncClient, latitude: float, longitude: float, days: int) -> ForecastResponse:
    """Fetch forecast from Open-Meteo."""
    params = {
        "latitude": latitude, "longitude": longitude,
        "daily": [
            "weather_code", "temperature_2m_max", "temperature_2m_min",
            "precipitation_sum", "precipitation_probability_max", "wind_speed_10m_max",
        ],
        "wind_speed_unit": "kmh",
        "timezone": "auto",
        "forecast_days": days,
    }
    r = await client.get(WEATHER_URL, params=params, timeout=10.0)
    r.raise_for_status()
    data = r.json()
    loc = await _reverse_geocode(client, latitude, longitude)

    d = data.get("daily", {})
    return ForecastResponse(
        location=loc, latitude=latitude, longitude=longitude,
        days=[
            ForecastDay(
                date=d["time"][i],
                max_temp=round(float(d["temperature_2m_max"][i] or 0), 1),
                min_temp=round(float(d["temperature_2m_min"][i] or 0), 1),
                precipitation_mm=round(float(d["precipitation_sum"][i] or 0), 1),
                rain_probability=int(d["precipitation_probability_max"][i] or 0),
                wind_speed=round(float(d["wind_speed_10m_max"][i] or 0), 1),
                condition=WMO_CODES.get(int(d["weather_code"][i] or 0), "Unknown"),
            )
            for i in range(len(d["time"]))
        ],
    )


# ── Public API: get_current_weather ──────────────────────────────────────────

async def get_current_weather(latitude: float, longitude: float) -> WeatherResponse:
    """
    Fetch current weather.

    Priority order:
    1. Open-Meteo (primary, free)
    2. WeatherAPI.com (fallback, requires WEATHERAPI_KEY in .env)
    3. In-memory TTL cache (stale-but-real data from a previous successful call)

    Raises httpx.HTTPStatusError / httpx.RequestError only when all sources fail.
    """
    key = (_round_coord(latitude), _round_coord(longitude))

    async with httpx.AsyncClient() as client:
        # ── 1. Try Open-Meteo ──────────────────────────────────────────────
        try:
            result = await _fetch_openmeteo_current(client, latitude, longitude)
            _cache_set(_weather_cache, key, result)
            return result
        except (httpx.HTTPStatusError, httpx.RequestError, httpx.TimeoutException):
            pass  # fall through to next provider

        # ── 2. Try WeatherAPI.com fallback ─────────────────────────────────
        if settings.weatherapi_key:
            try:
                result = await _fetch_weatherapi_current(client, latitude, longitude)
                _cache_set(_weather_cache, key, result)
                return result
            except (httpx.HTTPStatusError, httpx.RequestError, httpx.TimeoutException):
                pass  # fall through to cache

        # ── 3. Stale cache (last known real data) ──────────────────────────
        cached = _cache_get(_weather_cache, key)
        if cached is not None:
            return cached

    # All sources exhausted — re-raise so the route layer returns 502/503
    raise httpx.RequestError("All weather providers failed and no cached data available.")


# ── Public API: get_forecast ──────────────────────────────────────────────────

async def get_forecast(latitude: float, longitude: float, days: int = 7) -> ForecastResponse:
    """
    Fetch weather forecast.

    Same fallback priority as get_current_weather:
    1. Open-Meteo
    2. WeatherAPI.com (if key configured)
    3. In-memory cache
    """
    key = (_round_coord(latitude), _round_coord(longitude), days)

    async with httpx.AsyncClient() as client:
        # ── 1. Try Open-Meteo ──────────────────────────────────────────────
        try:
            result = await _fetch_openmeteo_forecast(client, latitude, longitude, days)
            _cache_set(_forecast_cache, key, result)
            return result
        except (httpx.HTTPStatusError, httpx.RequestError, httpx.TimeoutException):
            pass

        # ── 2. Try WeatherAPI.com fallback ─────────────────────────────────
        if settings.weatherapi_key:
            try:
                result = await _fetch_weatherapi_forecast(client, latitude, longitude, days)
                _cache_set(_forecast_cache, key, result)
                return result
            except (httpx.HTTPStatusError, httpx.RequestError, httpx.TimeoutException):
                pass

        # ── 3. Stale cache ─────────────────────────────────────────────────
        cached = _cache_get(_forecast_cache, key)
        if cached is not None:
            return cached

    raise httpx.RequestError("All forecast providers failed and no cached data available.")


# ── Reverse geocode ───────────────────────────────────────────────────────────

async def _reverse_geocode(client: httpx.AsyncClient, latitude: float, longitude: float) -> str:
    try:
        r = await client.get(
            GEOCODE_URL,
            params={"lat": latitude, "lon": longitude, "format": "json"},
            headers={"User-Agent": "WeatherGPT/1.0 (SIH26068)"},
            timeout=5.0,
        )
        r.raise_for_status()
        addr = r.json().get("address", {})
        return (
            addr.get("city") or addr.get("town") or addr.get("village")
            or addr.get("county") or addr.get("state") or "Unknown Location"
        )
    except Exception:
        return "Unknown Location"
