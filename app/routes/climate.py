"""
routes/climate.py - Climate/historical weather endpoints

GET /api/climate - returns historical climate summary for a location
"""

from fastapi import APIRouter, HTTPException, Query
from app.models.schemas import ClimateResponse
from app.services import climate_service
import httpx

router = APIRouter()


@router.get("/climate", response_model=ClimateResponse)
async def get_climate(
    latitude: float = Query(..., ge=-90, le=90, description="Latitude of the location"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude of the location"),
    days: int = Query(30, ge=7, le=90, description="Number of historical days to analyse (7-90)"),
):
    """
    Get historical climate insights for a location.

    Returns average temperatures, total rainfall, rainy day count, and a
    plain-language summary based on Open-Meteo archive data.

    Example: GET /api/climate?latitude=28.61&longitude=77.23&days=30
    """
    try:
        return await climate_service.get_climate_summary(latitude, longitude, days)
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Climate service timed out.")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Climate data provider error: {e.response.status_code}")
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Could not reach the climate data service.")
    except Exception:
        raise HTTPException(status_code=500, detail="Unexpected error fetching climate data.")
