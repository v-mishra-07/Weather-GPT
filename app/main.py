"""
main.py — WeatherGPT FastAPI application entry point

Responsibilities:
- Create the FastAPI app
- Register all routers
- Provide the /api/health endpoint
- Nothing else — business logic lives in services/
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routes import weather, chat, alerts, climate, predict

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


app = FastAPI(
    title="WeatherGPT API",
    description="Conversational AI for weather forecasting, alerts, and climate information.",
    version="0.1.0",
)

# CORS — allows Flutter (or any client) to call this API from a different origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten this in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers under /api prefix
app.include_router(weather.router, prefix="/api", tags=["Weather"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(alerts.router, prefix="/api", tags=["Alerts"])
app.include_router(climate.router, prefix="/api", tags=["Climate"])
app.include_router(predict.router, prefix="/api", tags=["Predict"])


@app.get("/api/health", tags=["Health"])
async def health():
    """Check whether the WeatherGPT backend is running."""
    return {"status": "ok", "service": settings.app_name}


@app.get("/", include_in_schema=False)
async def frontend_index():
    """Serve the WeatherGPT web UI."""
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")
