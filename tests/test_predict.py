"""
test_predict.py - Tests for POST /api/predict endpoint.

Uses monkeypatching so no actual .pkl file is required for most tests.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

VALID_PAYLOAD = {
    "temperature": 32.0,
    "humidity": 85.0,
    "rainfall_mm": 5.2,
    "wind_speed_kmh": 18.0,
    "rain_probability": 75.0,
    "cloud_cover": 80.0,
    "visibility_km": 4.5,
    "precipitation_mm": 5.2,
    "uv_index": 3.0,
}


def test_predict_missing_fields():
    """Empty body should return 422 Unprocessable Entity."""
    r = client.post("/api/predict", json={})
    assert r.status_code == 422


def test_predict_invalid_field_type():
    """String value where float expected should return 422."""
    bad = {**VALID_PAYLOAD, "temperature": "hot"}
    r = client.post("/api/predict", json=bad)
    assert r.status_code == 422


def test_predict_model_not_found(monkeypatch):
    """When model file is missing, endpoint should return 503."""
    from app.services import predict_service

    def raise_not_found(**kwargs):
        raise FileNotFoundError("ml/weather_risk_model.pkl not found")

    monkeypatch.setattr(predict_service, "predict_risk", raise_not_found)

    r = client.post("/api/predict", json=VALID_PAYLOAD)
    assert r.status_code == 503
    assert "model" in r.json()["detail"].lower()


def test_predict_valid_request_shape(monkeypatch):
    """With a working model (mocked), response must contain all required fields."""
    from app.services import predict_service

    def fake_predict(**kwargs):
        return {
            "risk_level": 1,
            "risk_label": "Medium",
            "confidence": 0.72,
            "message": "Moderate rainfall risk.",
            "disclaimer": "Demo only.",
        }

    monkeypatch.setattr(predict_service, "predict_risk", fake_predict)

    r = client.post("/api/predict", json=VALID_PAYLOAD)
    assert r.status_code == 200
    d = r.json()
    for field in ["risk_level", "risk_label", "confidence", "message", "disclaimer"]:
        assert field in d, f"Missing field: {field}"
    assert d["risk_level"] == 1
    assert d["risk_label"] == "Medium"
    assert 0.0 <= d["confidence"] <= 1.0


def test_predict_response_has_disclaimer(monkeypatch):
    """Disclaimer must always be present and non-empty."""
    from app.services import predict_service

    def fake_predict(**kwargs):
        return {
            "risk_level": 0,
            "risk_label": "Low",
            "confidence": 0.91,
            "message": "Low risk.",
            "disclaimer": "This prediction uses a Random Forest model trained on synthetic weather data.",
        }

    monkeypatch.setattr(predict_service, "predict_risk", fake_predict)

    r = client.post("/api/predict", json=VALID_PAYLOAD)
    assert r.status_code == 200
    d = r.json()
    assert "disclaimer" in d
    assert len(d["disclaimer"]) > 10


def test_predict_all_risk_levels(monkeypatch):
    """All three risk levels (0, 1, 2) should be accepted and returned correctly."""
    from app.services import predict_service

    for level, label in [(0, "Low"), (1, "Medium"), (2, "High")]:
        def fake_predict(level=level, label=label, **kwargs):
            return {
                "risk_level": level,
                "risk_label": label,
                "confidence": 0.80,
                "message": f"{label} risk.",
                "disclaimer": "Demo only.",
            }

        monkeypatch.setattr(predict_service, "predict_risk", fake_predict)
        r = client.post("/api/predict", json=VALID_PAYLOAD)
        assert r.status_code == 200
        assert r.json()["risk_level"] == level
        assert r.json()["risk_label"] == label
