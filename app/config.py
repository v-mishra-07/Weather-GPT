from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    model_config = ConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    # Weather API (Phase 2) — Open-Meteo is free and needs no key
    weather_api_key: str = ''
    weather_api_base_url: str = 'https://api.open-meteo.com/v1'

    # AI/LLM API — Google Gemini
    gemini_api_key: str = ''

    # Secondary weather provider (WeatherAPI.com) — used as fallback when Open-Meteo is rate-limited
    weatherapi_key: str = ''

    # App settings
    app_name: str = 'WeatherGPT'
    debug: bool = False

    # MySQL database
    database_url: str = ''

# Single shared instance - import this everywhere
settings = Settings()
