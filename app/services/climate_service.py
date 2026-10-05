"""
climate_service.py - Historical climate data service

Uses Open-Meteo's free archive API to fetch historical weather data.
No API key required.
"""

import httpx
from datetime import date, timedelta
from app.models.schemas import ClimateResponse
from app.services.weather_service import _reverse_geocode

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


async def get_climate_summary(latitude: float, longitude: float, days: int = 30) -> ClimateResponse:
    """
    Fetch historical weather data for the past N days and return a climate summary.
    Uses Open-Meteo archive API — free, no API key required.
    """
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=days - 1)

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
        ],
        "timezone": "auto",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(ARCHIVE_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
        location_name = await _reverse_geocode(client, latitude, longitude)

    daily = data.get("daily", {})
    max_temps = [t for t in daily.get("temperature_2m_max", []) if t is not None]
    min_temps = [t for t in daily.get("temperature_2m_min", []) if t is not None]
    precip = [p for p in daily.get("precipitation_sum", []) if p is not None]

    avg_max = round(sum(max_temps) / len(max_temps), 1) if max_temps else 0.0
    avg_min = round(sum(min_temps) / len(min_temps), 1) if min_temps else 0.0
    total_rain = round(sum(precip), 1)
    rainy_days = sum(1 for p in precip if p > 1.0)

    summary = _build_summary(avg_max, avg_min, total_rain, rainy_days, days, location_name)

    return ClimateResponse(
        location=location_name,
        latitude=latitude,
        longitude=longitude,
        days=days,
        avg_max_temp=avg_max,
        avg_min_temp=avg_min,
        total_rainfall_mm=total_rain,
        rainy_days=rainy_days,
        summary=summary,
    )


def _build_summary(avg_max: float, avg_min: float, total_rain: float, rainy_days: int, days: int, location: str) -> str:
    """Build a plain-language summary of the climate data."""
    parts = []

    if avg_max >= 40:
        parts.append(f"Very hot conditions in {location} with average highs of {avg_max}°C.")
    elif avg_max >= 35:
        parts.append(f"Hot conditions in {location} with average highs of {avg_max}°C.")
    elif avg_max >= 25:
        parts.append(f"Warm conditions in {location} with average highs of {avg_max}°C.")
    else:
        parts.append(f"Mild to cool conditions in {location} with average highs of {avg_max}°C.")

    rain_fraction = rainy_days / days if days > 0 else 0
    if rain_fraction >= 0.5:
        parts.append(f"Heavy rainfall period — {rainy_days} out of {days} days had rain, totalling {total_rain} mm.")
    elif rain_fraction >= 0.25:
        parts.append(f"Moderate rainfall — {rainy_days} rainy days with {total_rain} mm total.")
    elif rainy_days > 0:
        parts.append(f"Mostly dry with only {rainy_days} rainy day(s) and {total_rain} mm total rainfall.")
    else:
        parts.append(f"Dry period — no significant rainfall recorded.")

    return " ".join(parts)
