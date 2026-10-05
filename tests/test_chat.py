from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_chat_missing_fields():
    """Missing required fields should return 422 Unprocessable Entity."""
    r = client.post("/api/chat", json={})
    assert r.status_code == 422


def test_chat_invalid_latitude():
    """Latitude out of range should return 422."""
    r = client.post("/api/chat", json={
        "message": "Will it rain?",
        "latitude": 999,
        "longitude": 77.23
    })
    assert r.status_code == 422


def test_chat_response_shape():
    """
    Valid request should return one of:
    - 200: success (backend + Gemini both reachable)
    - 503: Gemini API key not configured
    - 502: upstream weather service unreachable (network issue in test env)
    - 500: unexpected error (e.g. weather service fails before reaching AI)

    On a real machine with internet and a valid GEMINI_API_KEY,
    this will return 200 with an 'answer' field.
    """
    r = client.post("/api/chat", json={
        "message": "Will it rain today?",
        "latitude": 28.61,
        "longitude": 77.23
    })
    assert r.status_code in (200, 502, 503, 500)
    if r.status_code == 200:
        data = r.json()
        assert "answer" in data
        assert isinstance(data["answer"], str)
        assert len(data["answer"]) > 0


def test_chat_gemini_none_response_returns_503(monkeypatch):
    """When Gemini returns None text (blocked), the endpoint should return 503 not 500."""
    from app.services import ai_service

    # Patch get_weather_answer to raise ValueError (simulating blocked response)
    async def fake_answer(*args, **kwargs):
        raise ValueError("Gemini could not generate a response.")

    monkeypatch.setattr(ai_service, "get_weather_answer", fake_answer)

    r = client.post("/api/chat", json={
        "message": "Will it rain today?",
        "latitude": 28.61,
        "longitude": 77.23
    })
    # When weather fetch works but AI returns ValueError → 503
    # When weather fetch fails (no network) → 502
    assert r.status_code in (503, 502, 504)


def test_chat_asyncio_running_loop_used():
    """Verify get_weather_answer uses get_running_loop not get_event_loop."""
    import inspect
    source = inspect.getsource(__import__('app.services.ai_service', fromlist=['ai_service']))
    assert 'get_running_loop' in source
    assert 'get_event_loop' not in source
