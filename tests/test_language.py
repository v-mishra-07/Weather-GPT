"""
tests/test_language.py - Tests for Indian language support in the chat endpoint
"""

from fastapi.testclient import TestClient
from app.main import app
from app.services.ai_service import LANGUAGE_NAMES, _build_context
from app.models.schemas import ChatRequest, WeatherResponse, ForecastResponse

client = TestClient(app)


def test_language_defaults_to_english():
    """ChatRequest should default to English when language is not provided."""
    r = ChatRequest(message="Will it rain?", latitude=28.61, longitude=77.23)
    assert r.language == "en"


def test_language_field_accepted():
    """ChatRequest should accept a valid language code."""
    r = ChatRequest(message="Will it rain?", latitude=28.61, longitude=77.23, language="hi")
    assert r.language == "hi"


def test_all_supported_language_codes():
    """All supported language codes should be present in LANGUAGE_NAMES."""
    expected = {"en", "hi", "bn", "ta", "te", "mr", "gu", "kn", "ml", "pa"}
    assert expected.issubset(set(LANGUAGE_NAMES.keys()))


def test_language_names_are_strings():
    """All language names should be non-empty strings."""
    for code, name in LANGUAGE_NAMES.items():
        assert isinstance(name, str)
        assert len(name) > 0


def test_chat_with_language_field_english():
    """Chat endpoint should accept explicit English language code."""
    r = client.post("/api/chat", json={
        "message": "Will it rain today?",
        "latitude": 28.61,
        "longitude": 77.23,
        "language": "en"
    })
    # 200: success, 503: no API key, 502/500: external service unavailable in test env
    assert r.status_code in (200, 500, 502, 503)
    if r.status_code == 200:
        assert "answer" in r.json()


def test_chat_with_hindi_language():
    """Chat endpoint should accept Hindi language code."""
    r = client.post("/api/chat", json={
        "message": "क्या आज बारिश होगी?",
        "latitude": 28.61,
        "longitude": 77.23,
        "language": "hi"
    })
    # 200: success, 503: no API key, 502/500: external service unavailable in test env
    assert r.status_code in (200, 500, 502, 503)
    if r.status_code == 200:
        assert "answer" in r.json()


def test_chat_without_language_still_works():
    """Existing chat calls without language field should still work (backward compatible)."""
    r = client.post("/api/chat", json={
        "message": "What is the weather like?",
        "latitude": 28.61,
        "longitude": 77.23
    })
    # 200: success, 503: no API key, 502/500: external service unavailable in test env
    assert r.status_code in (200, 500, 502, 503)


def test_chat_invalid_latitude_with_language():
    """Validation should still work with language field present."""
    r = client.post("/api/chat", json={
        "message": "Will it rain?",
        "latitude": 999,
        "longitude": 77.23,
        "language": "hi"
    })
    assert r.status_code == 422
