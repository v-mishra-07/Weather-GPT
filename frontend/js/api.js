/**
 * api.js - All WeatherGPT backend communication
 * Base URL points to FastAPI backend running on localhost:8000
 */

const API_BASE = 'http://localhost:8000';

/**
 * Check backend health
 * @returns {Promise<{status: string, service: string}>}
 */
async function checkHealth() {
    const response = await fetch(`${API_BASE}/api/health`);
    if (!response.ok) throw new Error(`Health check failed: ${response.status}`);
    return response.json();
}

/**
 * Get current weather for a location
 * @param {number} latitude 
 * @param {number} longitude
 * @returns {Promise<{location, temperature, feels_like, humidity, wind_speed, rain_probability, condition}>}
 */
async function getWeather(latitude, longitude) {
    const response = await fetch(
        `${API_BASE}/api/weather?latitude=${latitude}&longitude=${longitude}`
    );
    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || `Weather request failed: ${response.status}`);
    }
    return response.json();
}

/**
 * Get weather forecast
 * @param {number} latitude
 * @param {number} longitude  
 * @param {number} days - number of forecast days (default 7)
 * @returns {Promise<{location, days: Array<{date, max_temp, min_temp, rain_probability, precipitation_mm, wind_speed, condition}>}>}
 */
async function getForecast(latitude, longitude, days = 7) {
    const response = await fetch(
        `${API_BASE}/api/forecast?latitude=${latitude}&longitude=${longitude}&days=${days}`
    );
    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || `Forecast request failed: ${response.status}`);
    }
    return response.json();
}

/**
 * Send a chat message to WeatherGPT
 * @param {string} message - user's question
 * @param {number} latitude
 * @param {number} longitude
 * @param {string} language - language code (en, hi, bn, ta, te, mr, gu, kn, ml, pa)
 * @param {string} mode - advice mode (general, farmer, traveller, citizen)
 * @returns {Promise<{answer, location}>}
 */
async function sendChatMessage(message, latitude, longitude, language = 'en', mode = 'general') {
    const response = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, latitude, longitude, language, mode })
    });
    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || `Chat request failed: ${response.status}`);
    }
    return response.json();
}

/**
 * Get weather alerts for a location
 * @param {number} latitude
 * @param {number} longitude
 * @returns {Promise<{has_alert, severity, type, message}>}
 */
async function getAlerts(latitude, longitude) {
    const response = await fetch(
        `${API_BASE}/api/alerts?latitude=${latitude}&longitude=${longitude}`
    );
    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || `Alerts request failed: ${response.status}`);
    }
    return response.json();
}

/**
 * Get historical climate summary
 * @param {number} latitude
 * @param {number} longitude
 * @param {number} days - historical days (7–90)
 * @returns {Promise<Object>}
 */
async function getClimate(latitude, longitude, days = 30) {
    const response = await fetch(
        `${API_BASE}/api/climate?latitude=${latitude}&longitude=${longitude}&days=${days}`
    );
    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || `Climate request failed: ${response.status}`);
    }
    return response.json();
}

/**
 * POST /api/predict — ML Random Forest hazard risk prediction
 * @param {Object} payload - 9 weather feature fields (see PredictRequest schema)
 * @returns {Promise<{risk_level, risk_label, confidence, message, disclaimer}>}
 */
async function predictRisk(payload) {
    const response = await fetch(`${API_BASE}/api/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || `Predict request failed: ${response.status}`);
    }
    return response.json();
}
