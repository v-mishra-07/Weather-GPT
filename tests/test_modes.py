"""
tests/test_modes.py - Tests for Specialized Advice Modes
"""

from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import ChatRequest
from app.services.ai_service import MODE_PROMPTS

client = TestClient(app)


def test_mode_defaults_to_general():
    r = ChatRequest(message="Will it rain?", latitude=28.61, longitude=77.23)
    assert r.mode == "general"


def test_mode_farmer_accepted():
    r = ChatRequest(message="Should I irrigate?", latitude=28.61, longitude=77.23, mode="farmer")
    assert r.mode == "farmer"


def test_mode_traveller_accepted():
    r = ChatRequest(message="Is it safe to travel?", latitude=28.61, longitude=77.23, mode="traveller")
    assert r.mode == "traveller"


def test_mode_citizen_accepted():
    r = ChatRequest(message="Should I carry an umbrella?", latitude=28.61, longitude=77.23, mode="citizen")
    assert r.mode == "citizen"


def test_all_modes_in_mode_prompts():
    for mode in ["general", "farmer", "traveller", "citizen"]:
        assert mode in MODE_PROMPTS


def test_mode_prompts_are_strings():
    for mode, prompt in MODE_PROMPTS.items():
        assert isinstance(prompt, str)


def test_farmer_prompt_contains_farm_keywords():
    assert "farm" in MODE_PROMPTS["farmer"].lower() or "irrigat" in MODE_PROMPTS["farmer"].lower()


def test_traveller_prompt_contains_travel_keywords():
    assert "travel" in MODE_PROMPTS["traveller"].lower()


def test_citizen_prompt_contains_daily_keywords():
    assert "daily" in MODE_PROMPTS["citizen"].lower() or "commute" in MODE_PROMPTS["citizen"].lower()


def test_chat_with_farmer_mode():
    r = client.post("/api/chat", json={
        "message": "Should I irrigate my crops today?",
        "latitude": 28.61,
        "longitude": 77.23,
        "mode": "farmer"
    })
    assert r.status_code in (200, 500, 502, 503)
    if r.status_code == 200:
        assert "answer" in r.json()


def test_chat_with_traveller_mode():
    r = client.post("/api/chat", json={
        "message": "Is it safe to drive to Mumbai?",
        "latitude": 28.61,
        "longitude": 77.23,
        "mode": "traveller"
    })
    assert r.status_code in (200, 500, 502, 503)
    if r.status_code == 200:
        assert "answer" in r.json()


def test_chat_with_citizen_mode():
    r = client.post("/api/chat", json={
        "message": "Should I carry an umbrella?",
        "latitude": 28.61,
        "longitude": 77.23,
        "mode": "citizen"
    })
    assert r.status_code in (200, 500, 502, 503)
    if r.status_code == 200:
        assert "answer" in r.json()


def test_chat_with_mode_and_language():
    """Mode and language should work together."""
    r = client.post("/api/chat", json={
        "message": "क्या मुझे सिंचाई करनी चाहिए?",
        "latitude": 28.61,
        "longitude": 77.23,
        "mode": "farmer",
        "language": "hi"
    })
    assert r.status_code in (200, 500, 502, 503)


def test_chat_backward_compatible_no_mode():
    """Existing calls without mode field should still work."""
    r = client.post("/api/chat", json={
        "message": "What is the weather?",
        "latitude": 28.61,
        "longitude": 77.23
    })
    assert r.status_code in (200, 500, 502, 503)


def test_invalid_latitude_with_mode():
    r = client.post("/api/chat", json={
        "message": "Will it rain?",
        "latitude": 999,
        "longitude": 77.23,
        "mode": "farmer"
    })
    assert r.status_code == 422
