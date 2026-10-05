"""
predict.py - POST /api/predict endpoint

Accepts 9 weather features, returns a rainfall risk prediction
from the pre-trained Random Forest model, and saves the prediction
to MySQL.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.schemas import PredictRequest, PredictResponse
from app.models.prediction import Prediction
from app.services import predict_service

router = APIRouter()


@router.post("/predict", response_model=PredictResponse)
async def predict(
    r: PredictRequest,
    db: Session = Depends(get_db),
):
    """
    Predict rainfall/weather risk using a pre-trained Random Forest model.

    Supply 9 weather features. Returns risk_level, risk_label, confidence,
    message, and disclaimer.

    The prediction is also saved to the MySQL predictions table.

    NOTE: Model was trained on synthetic data - for demo use only.
    """
    try:
        result = predict_service.predict_risk(
            temperature=r.temperature,
            humidity=r.humidity,
            rainfall_mm=r.rainfall_mm,
            wind_speed_kmh=r.wind_speed_kmh,
            rain_probability=r.rain_probability,
            cloud_cover=r.cloud_cover,
            visibility_km=r.visibility_km,
            precipitation_mm=r.precipitation_mm,
            uv_index=r.uv_index,
        )

        prediction = Prediction(
            temperature=r.temperature,
            humidity=r.humidity,
            rainfall_mm=r.rainfall_mm,
            wind_speed_kmh=r.wind_speed_kmh,
            rain_probability=r.rain_probability,
            cloud_cover=r.cloud_cover,
            visibility_km=r.visibility_km,
            precipitation_mm=r.precipitation_mm,
            uv_index=r.uv_index,
            risk_level=result["risk_level"],
            risk_label=result["risk_label"],
            confidence=result["confidence"],
            message=result["message"],
        )

        db.add(prediction)
        db.commit()

        return PredictResponse(**result)

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=503,
            detail=f"ML model not available: {e}. Place weather_risk_model.pkl in the ml/ directory.",
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=503,
            detail=f"ML model error: {e}",
        )
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unexpected error during prediction.",
        )