"""
predict_service.py - Weather risk prediction using a pre-trained Random Forest model.

The model is loaded once (lazily, on first request) from ml/weather_risk_model.pkl.
numpy and joblib are imported inside functions so a missing package never prevents
the backend from starting -- only POST /api/predict would fail in that case.

NOTE: The model was trained on synthetic data. Predictions are for demo/prototype use only.
"""

import pathlib

# Module-level model cache -- loaded once on first call, never reloaded per request.
_model = None
_model_error: str = ""

# Path: weathergpt/ml/weather_risk_model.pkl
MODEL_PATH = pathlib.Path(__file__).parent.parent.parent / "ml" / "weather_risk_model.pkl"

RISK_LABELS = {0: "Low", 1: "Medium", 2: "High"}

RISK_MESSAGES = {
    0: "Low rainfall risk. Conditions look dry and stable.",
    1: "Moderate rainfall risk. Some chance of rain -- carry an umbrella.",
    2: "High rainfall risk. Rain is likely. Take precautions.",
}

DISCLAIMER = (
    "This prediction uses a Random Forest model trained on synthetic weather data. "
    "It is intended for demo and prototype use only. "
    "Do not use for real safety, agricultural, or emergency decisions."
)


def _load_model():
    """Load and cache the model. Raises FileNotFoundError or RuntimeError on failure."""
    global _model, _model_error

    if _model is not None:
        return _model

    if not MODEL_PATH.exists():
        _model_error = (
            f"Model file not found at '{MODEL_PATH}'. "
            "Copy weather_risk_model.pkl into the ml/ directory."
        )
        raise FileNotFoundError(_model_error)

    try:
        import joblib  # deferred import -- does not run at server startup
        _model = joblib.load(MODEL_PATH)
        _model_error = ""
        return _model
    except Exception as exc:
        _model_error = f"Failed to load model from '{MODEL_PATH}': {exc}"
        raise RuntimeError(_model_error) from exc


def predict_risk(
    temperature: float,
    humidity: float,
    rainfall_mm: float,
    wind_speed_kmh: float,
    rain_probability: float,
    cloud_cover: float,
    visibility_km: float,
    precipitation_mm: float,
    uv_index: float,
) -> dict:
    """
    Run the Random Forest model and return a rainfall/weather risk prediction.

    Features are passed in the exact order the model was trained on:
      [temperature, humidity, rainfall_mm, wind_speed_kmh, rain_probability,
       cloud_cover, visibility_km, precipitation_mm, uv_index]

    Returns dict with: risk_level, risk_label, confidence, message, disclaimer.
    Raises FileNotFoundError if .pkl is missing, RuntimeError if corrupt.
    """
    import numpy as np  # deferred import -- does not run at server startup

    model = _load_model()

    features = np.array([[
        temperature,
        humidity,
        rainfall_mm,
        wind_speed_kmh,
        rain_probability,
        cloud_cover,
        visibility_km,
        precipitation_mm,
        uv_index,
    ]])

    risk_level = int(model.predict(features)[0])
    probabilities = model.predict_proba(features)[0]
    confidence = round(float(probabilities.max()), 4)

    risk_label = RISK_LABELS.get(risk_level, f"Unknown({risk_level})")
    message = RISK_MESSAGES.get(risk_level, "Risk level predicted.")

    return {
        "risk_level": risk_level,
        "risk_label": risk_label,
        "confidence": confidence,
        "message": message,
        "disclaimer": DISCLAIMER,
    }
