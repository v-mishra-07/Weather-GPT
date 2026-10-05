"""
alert_service.py - Rule-based weather alert detection

Checks current weather conditions against simple thresholds.
No ML - just clear, explainable rules that work reliably.
"""

from app.models.schemas import WeatherResponse, AlertResponse


def check_alerts(weather: WeatherResponse) -> AlertResponse:
    """
    Check weather data against alert thresholds.
    Returns the highest-severity alert found, or no-alert if conditions are normal.
    """

    # Heavy rain - high severity
    if weather.rain_probability >= 80:
        return AlertResponse(
            has_alert=True,
            severity="high",
            type="heavy_rain",
            message=f"Heavy rainfall expected in {weather.location}. Rain probability is {weather.rain_probability}%. Avoid unnecessary travel and stay indoors.",
        )

    # Strong wind - high severity
    if weather.wind_speed >= 60:
        return AlertResponse(
            has_alert=True,
            severity="high",
            type="strong_wind",
            message=f"Strong winds in {weather.location}. Wind speed is {weather.wind_speed} km/h. Avoid outdoor activities.",
        )

    # Extreme heat - high severity
    if weather.temperature >= 42:
        return AlertResponse(
            has_alert=True,
            severity="high",
            type="extreme_heat",
            message=f"Extreme heat in {weather.location}. Temperature is {weather.temperature}°C. Stay hydrated and avoid direct sun exposure.",
        )

    # Moderate rain - medium severity
    if weather.rain_probability >= 50:
        return AlertResponse(
            has_alert=True,
            severity="medium",
            type="rain",
            message=f"Rain likely in {weather.location}. Rain probability is {weather.rain_probability}%. Carry an umbrella.",
        )

    # Moderate wind - medium severity
    if weather.wind_speed >= 40:
        return AlertResponse(
            has_alert=True,
            severity="medium",
            type="strong_wind",
            message=f"Moderate winds in {weather.location}. Wind speed is {weather.wind_speed} km/h. Secure loose outdoor items.",
        )

    # Cold wave - medium severity
    if weather.temperature <= 5:
        return AlertResponse(
            has_alert=True,
            severity="medium",
            type="cold_wave",
            message=f"Cold conditions in {weather.location}. Temperature is {weather.temperature}°C. Dress warmly.",
        )

    # No alert
    return AlertResponse(has_alert=False, severity=None, type=None, message=None)
