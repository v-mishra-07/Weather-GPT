from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import httpx

from app.database import get_db
from app.models.schemas import WeatherResponse, ForecastResponse
from app.services import weather_service
from app.services.database_service import get_or_create_location, save_weather_record

router = APIRouter()


@router.get("/weather", response_model=WeatherResponse)
async def get_weather(
    latitude: float = Query(...),
    longitude: float = Query(...),
    db: Session = Depends(get_db),
):
    try:
        weather = await weather_service.get_current_weather(latitude, longitude)

        location = get_or_create_location(
            db=db,
            name=weather.location,
            latitude=weather.latitude,
            longitude=weather.longitude,
        )

        save_weather_record(
            db=db,
            location=location,
            temperature=weather.temperature,
            feels_like=weather.feels_like,
            humidity=weather.humidity,
            wind_speed=weather.wind_speed,
            rain_probability=weather.rain_probability,
            condition=weather.condition,
            is_day=weather.is_day,
        )

        return weather

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Weather service timed out.",
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Weather provider error: {e.response.status_code}",
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=503,
            detail="Weather service is unavailable.",
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unexpected error while fetching weather.",
        )


@router.get("/forecast", response_model=ForecastResponse)
async def get_forecast(
    latitude: float = Query(...),
    longitude: float = Query(...),
    days: int = Query(7, ge=1, le=14),
):
    try:
        return await weather_service.get_forecast(latitude, longitude, days)

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Weather service timed out.",
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Weather provider error: {e.response.status_code}",
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=503,
            detail="Weather service is unavailable.",
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unexpected error while fetching forecast.",
        )