"""
routes/alerts.py - Alert endpoints

GET /api/alerts - returns weather alert for a location based on current conditions
"""

from fastapi import APIRouter, HTTPException, Query
from app.models.schemas import AlertResponse
from app.services import weather_service, alert_service
import httpx

router = APIRouter()


@router.get("/alerts", response_model=AlertResponse)
async def get_alerts(
    latitude: float = Query(..., ge=-90, le=90, description="Latitude of the location"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude of the location"),
):
    """
    Get weather alerts for a location.

    Returns the most severe active alert based on current weather conditions.
    Uses simple rule-based detection - no machine learning required.

    Example: GET /api/alerts?latitude=28.61&longitude=77.23
    """
    try:
        weather = await weather_service.get_current_weather(latitude, longitude)
        return alert_service.check_alerts(weather)
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Weather service timed out.")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Weather provider error: {e.response.status_code}")
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Could not reach the weather service.")
    except Exception:
        raise HTTPException(status_code=500, detail="Unexpected error checking alerts.")
