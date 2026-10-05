"""
ai_service.py - AI response generation using Google Gemini

Uses Google Gemini to answer natural-language weather questions.
Weather facts always come from Open-Meteo — Gemini only interprets them.
"""

import asyncio

from app.config import settings
from app.models.schemas import WeatherResponse, ForecastResponse

# System instructions for Gemini
SYSTEM_PROMPT_BASE = (
    "You are WeatherGPT, a helpful weather assistant.\n"
    "RULES:\n"
    "- ALWAYS base your answers on the weather data provided below.\n"
    "- NEVER invent temperatures or forecasts.\n"
    "- Keep answers short and actionable (2-4 sentences).\n"
    "- Always mention the location name if known.\n"
    "- Respond in the language specified in the user prompt."
)

MODE_PROMPTS = {
    "general": "",
    "farmer": (
        "\nFARMER MODE: The user is a farmer. Focus your advice on:\n"
        "- Whether it is safe to irrigate, spray pesticides, or work in the field.\n"
        "- Risk of crop damage from rain, wind, or extreme temperatures.\n"
        "- Best time of day for outdoor farm work."
    ),
    "traveller": (
        "\nTRAVELLER MODE: The user is planning to travel. Focus your advice on:\n"
        "- Whether road or air travel is safe given current and forecast conditions.\n"
        "- Visibility, wind, and rain risks for the journey.\n"
        "- Whether travel should be postponed."
    ),
    "citizen": (
        "\nCITIZEN MODE: The user is a regular citizen planning daily activities. Focus on:\n"
        "- Commute safety and outdoor activity suitability.\n"
        "- What to wear and whether to carry an umbrella.\n"
        "- Simple, practical daily life advice."
    ),
}

LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "bn": "Bengali",
    "ta": "Tamil",
    "te": "Telugu",
    "mr": "Marathi",
    "gu": "Gujarati",
    "kn": "Kannada",
    "ml": "Malayalam",
    "pa": "Punjabi",
}


def _build_context(w, f):
    """Build a plain-text weather summary to inject into the prompt."""
    l = [
        "LOCATION: " + w.location,
        "CURRENT WEATHER:",
        "  Condition: " + w.condition,
        "  Temp: " + str(w.temperature) + "C",
        "  Humidity: " + str(w.humidity) + "%",
        "  Wind: " + str(w.wind_speed) + " km/h",
        "  Rain: " + str(w.rain_probability) + "%",
        "",
        "7-DAY FORECAST:",
    ]
    for d in f.days[:7]:
        l.append(
            "  " + d.date + ": " + d.condition
            + " max " + str(d.max_temp) + "C"
            + " min " + str(d.min_temp) + "C"
            + " rain " + str(d.rain_probability) + "%"
        )
    return "\n".join(l)


async def get_weather_answer(m, w, f, language="en", mode="general"):
    """
    Send the user question + trusted weather context to Google Gemini.
    Returns a concise actionable answer string.
    """
    if not settings.gemini_api_key:
        raise ValueError(
            "Gemini API key not configured. Add GEMINI_API_KEY to your .env file."
        )

    lang_name = LANGUAGE_NAMES.get(language, "English")
    mode_instruction = MODE_PROMPTS.get(mode, "")
    system_instruction = SYSTEM_PROMPT_BASE + mode_instruction

    context = _build_context(w, f)
    user_prompt = (
        "Weather data:\n"
        + context
        + "\n\nUser question: " + m
        + "\n\nIMPORTANT: Please respond in " + lang_name + " only."
        + "\n\nPlease answer based only on the weather data above."
    )

    # Import Gemini only when chat is used — package import can hang at startup.
    from google import genai
    from google.genai import types

    # Configure Gemini client with the API key
    client = genai.Client(api_key=settings.gemini_api_key, http_options={"api_version": "v1"})

    # Use asyncio.get_running_loop() — required in Python 3.10+ inside async context
    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(
        None,
        lambda: client.models.generate_content(
            model="gemini-3.6-flash",
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
            ),
        )
    )

    # response.text is None when Gemini blocks the content (safety filters).
    # Return a safe fallback message instead of crashing with AttributeError.
    if response.text is None:
        raise ValueError(
            "Gemini could not generate a response for this request. "
            "The content may have been blocked by safety filters."
        )

    return response.text.strip()
