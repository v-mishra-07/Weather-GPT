import logging

from fastapi import APIRouter, HTTPException
from app.models.schemas import ChatRequest, ChatResponse
from app.services import weather_service, ai_service
import httpx

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(r: ChatRequest):
    """
    Ask WeatherGPT a weather question.

    - language: response language code (en, hi, bn, ta, te, mr, gu, kn, ml, pa)
    - mode: advice mode (general, farmer, traveller, citizen)
    """
    try:
        w = await weather_service.get_current_weather(r.latitude, r.longitude)
        f = await weather_service.get_forecast(r.latitude, r.longitude)
        a = await ai_service.get_weather_answer(r.message, w, f, language=r.language, mode=r.mode)
        return ChatResponse(answer=a, location=w.location)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Timed out.")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Weather service error: {e.response.status_code}")
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Cannot reach weather service.")
    except Exception as e:
        # Catches google.genai.errors.APIError (and any other unexpected error).
        # Logs the full traceback to the Uvicorn terminal for diagnosis.
        logger.exception("Unexpected error in POST /api/chat")
        raise HTTPException(
            status_code=503,
            detail=f"AI service error: {type(e).__name__}: {e}",
        )
