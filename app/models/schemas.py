from pydantic import BaseModel, Field
from typing import Optional, List


# -----------------------------------------------------------------------
# Health
# -----------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    service: str


# -----------------------------------------------------------------------
# Weather (Phase 2)
# -----------------------------------------------------------------------

class WeatherResponse(BaseModel):
    location: str
    latitude: float
    longitude: float
    temperature: float = Field(description="Temperature in Celsius")
    feels_like: float = Field(description="Feels-like temperature in Celsius")
    humidity: int = Field(description="Relative humidity percentage")
    wind_speed: float = Field(description="Wind speed in km/h")
    rain_probability: int = Field(description="Precipitation probability percentage")
    condition: str = Field(description="Short weather condition description")
    is_day: int = Field(default=1, description="1 = daytime, 0 = night (from Open-Meteo/WeatherAPI)")
    sunrise: str | None = Field(default=None, description="Today's sunrise time as ISO datetime string, e.g. 2026-10-05T06:12")
    sunset: str | None = Field(default=None, description="Today's sunset time as ISO datetime string, e.g. 2026-10-05T17:58")


# -----------------------------------------------------------------------
# Forecast (Phase 3)
# -----------------------------------------------------------------------

class ForecastDay(BaseModel):
    date: str = Field(description="Date in YYYY-MM-DD format")
    max_temp: float = Field(description="Maximum temperature in Celsius")
    min_temp: float = Field(description="Minimum temperature in Celsius")
    rain_probability: int = Field(description="Precipitation probability percentage")
    precipitation_mm: float = Field(description="Total precipitation in mm")
    wind_speed: float = Field(description="Max wind speed in km/h")
    condition: str = Field(description="Weather condition description")


class ForecastResponse(BaseModel):
    location: str
    latitude: float
    longitude: float
    days: List[ForecastDay]


# -----------------------------------------------------------------------
# Chat (Phase 4)
# -----------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500, description="User's weather question")
    latitude: float = Field(ge=-90, le=90, description="Location latitude")
    longitude: float = Field(ge=-180, le=180, description="Location longitude")
    language: str = Field(
        default="en",
        description="Response language code. Examples: en, hi, bn, ta, te, mr, gu, kn, ml, pa"
    )
    mode: str = Field(
        default="general",
        description="Advice mode: general, farmer, traveller, citizen"
    )


class ChatResponse(BaseModel):
    answer: str
    location: Optional[str] = None


# -----------------------------------------------------------------------
# Alerts (Phase 5)
# -----------------------------------------------------------------------

class AlertResponse(BaseModel):
    has_alert: bool
    severity: Optional[str] = Field(None, description="low | medium | high")
    type: Optional[str] = Field(None, description="Alert type, e.g. heavy_rain")
    message: Optional[str] = None


# -----------------------------------------------------------------------
# Climate (Phase 7c)
# -----------------------------------------------------------------------

class ClimateResponse(BaseModel):
    location: str
    latitude: float
    longitude: float
    days: int = Field(description="Number of historical days analysed")
    avg_max_temp: float = Field(description="Average daily maximum temperature in Celsius")
    avg_min_temp: float = Field(description="Average daily minimum temperature in Celsius")
    total_rainfall_mm: float = Field(description="Total precipitation over the period in mm")
    rainy_days: int = Field(description="Number of days with rainfall > 1mm")
    summary: str = Field(description="Plain-language climate summary for the period")


# -----------------------------------------------------------------------
# Predict (ML — Random Forest risk prediction)
# -----------------------------------------------------------------------

class PredictRequest(BaseModel):
    temperature: float = Field(description="Current temperature in Celsius")
    humidity: float = Field(description="Relative humidity percentage (0–100)")
    rainfall_mm: float = Field(description="Current or recent rainfall in mm")
    wind_speed_kmh: float = Field(description="Wind speed in km/h")
    rain_probability: float = Field(description="Precipitation probability percentage (0–100)")
    cloud_cover: float = Field(description="Cloud cover percentage (0–100)")
    visibility_km: float = Field(description="Visibility in km")
    precipitation_mm: float = Field(description="Total precipitation in mm")
    uv_index: float = Field(description="UV index value")


class PredictResponse(BaseModel):
    risk_level: int = Field(description="Predicted risk level: 0=Low, 1=Medium, 2=High")
    risk_label: str = Field(description="Human-readable risk label: Low, Medium, or High")
    confidence: float = Field(description="Model confidence score (0.0–1.0)")
    message: str = Field(description="Plain-language risk summary")
    disclaimer: str = Field(description="Important note about model limitations")
