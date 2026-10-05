# WeatherGPT Backend

**Team NEXUS | SIH Problem Statement SIH26068**
Conversational AI for Weather Forecasting, Alerts, and Climate Information.

---

## Technology Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Framework | FastAPI |
| Validation | Pydantic v2 |
| AI | OpenAI API |
| Weather Data | Open-Meteo (free, no key required) |
| Server | Uvicorn |
| Testing | Pytest |

---

## Folder Structure

```
weathergpt/
├── app/
│   ├── main.py          # App entry point, router registration
│   ├── config.py        # Environment variable loading
│   ├── routes/
│   │   ├── weather.py   # GET /api/weather
│   │   ├── chat.py      # POST /api/chat
│   │   └── alerts.py    # GET /api/alerts
│   ├── services/
│   │   ├── weather_service.py   # Weather API logic (Phase 2)
│   │   ├── ai_service.py        # LLM logic (Phase 4)
│   │   └── alert_service.py     # Alert detection logic (Phase 5)
│   └── models/
│       └── schemas.py   # Pydantic request/response models
├── tests/               # Pytest test files
├── .env                 # Your secrets (never commit this)
├── .env.example         # Template for environment variables
├── requirements.txt     # Python dependencies
└── README.md
```

---

## Installation

**1. Clone / navigate to the project folder:**
```bash
cd weathergpt
```

**2. Create and activate a virtual environment:**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

**3. Install dependencies:**
```bash
pip install -r requirements.txt
```

**4. Set up environment variables:**
```bash
cp .env.example .env
# Edit .env and fill in your API keys
```

---

## Environment Variables

| Variable | Description | Required |
|---|---|---|
| `WEATHER_API_KEY` | Weather provider API key | Phase 2+ |
| `OPENAI_API_KEY` | OpenAI API key | Phase 4+ |
| `OPENAI_MODEL` | Model name (default: gpt-3.5-turbo) | Phase 4+ |
| `APP_NAME` | Application name | No |
| `DEBUG` | Debug mode (true/false) | No |

---

## Running the Server

```bash
uvicorn app.main:app --reload
```

The server starts at: **http://localhost:8000**

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Check if the backend is running |
| GET | `/api/weather` | Get current weather for a location |
| POST | `/api/chat` | Ask a natural-language weather question |
| GET | `/api/alerts` | Get weather alerts for a location |

---

## Example Requests

**Health check:**
```
GET http://localhost:8000/api/health
```

**Current weather:**
```
GET http://localhost:8000/api/weather?latitude=28.61&longitude=77.23
```

**Chat:**
```
POST http://localhost:8000/api/chat
Content-Type: application/json

{
  "message": "Should I carry an umbrella today?",
  "latitude": 28.61,
  "longitude": 77.23
}
```

**Alerts:**
```
GET http://localhost:8000/api/alerts?latitude=28.61&longitude=77.23
```

---

## Example Responses

**Health:**
```json
{ "status": "ok", "service": "WeatherGPT" }
```

**Weather (Phase 2+):**
```json
{
  "location": "Delhi",
  "latitude": 28.61,
  "longitude": 77.23,
  "temperature": 31,
  "feels_like": 35,
  "humidity": 68,
  "wind_speed": 12,
  "rain_probability": 60,
  "condition": "Cloudy"
}
```

**Chat (Phase 4+):**
```json
{
  "answer": "Yes, there is a high chance of rain today. Carry an umbrella.",
  "location": "Delhi"
}
```

**Alert (Phase 5+):**
```json
{
  "has_alert": true,
  "severity": "high",
  "type": "heavy_rain",
  "message": "Heavy rainfall expected. Avoid unnecessary travel."
}
```

---

## Testing APIs

Open Swagger UI in your browser while the server is running:

```
http://localhost:8000/docs
```

All endpoints can be tested directly from Swagger without any extra tools.

---

## Running Tests

```bash
pytest tests/
```

---

## Flutter Integration

Flutter communicates with this backend via HTTP/JSON.
CORS is enabled for all origins — Flutter can call the API from any device.

### Base URL
```
http://<your-machine-ip>:8000
```
Find your machine IP with: `ipconfig` (Windows) or `ifconfig` (Mac/Linux)

### Recommended Flutter packages
- `http: ^1.1.0` — lightweight HTTP client
- `dio: ^5.4.0` — alternative with interceptors and better error handling

### Example Flutter calls

**Get current weather:**
```dart
final response = await http.get(
  Uri.parse('http://192.168.1.x:8000/api/weather?latitude=28.61&longitude=77.23'),
);
final data = jsonDecode(response.body);
// data['temperature'], data['condition'], data['rain_probability'] etc.
```

**Ask WeatherGPT:**
```dart
final response = await http.post(
  Uri.parse('http://192.168.1.x:8000/api/chat'),
  headers: {'Content-Type': 'application/json'},
  body: jsonEncode({
    'message': 'Will it rain today?',
    'latitude': 28.61,
    'longitude': 77.23,
  }),
);
final data = jsonDecode(response.body);
// data['answer'] contains the AI response
```

**Check alerts:**
```dart
final response = await http.get(
  Uri.parse('http://192.168.1.x:8000/api/alerts?latitude=28.61&longitude=77.23'),
);
final data = jsonDecode(response.body);
// data['has_alert'], data['severity'], data['message']
```

### API Contract Summary

| Endpoint | Method | Flutter sends | Flutter receives |
|---|---|---|---|
| `/api/health` | GET | nothing | `{status, service}` |
| `/api/weather` | GET | `latitude`, `longitude` | `{location, temperature, humidity, wind_speed, rain_probability, condition, ...}` |
| `/api/forecast` | GET | `latitude`, `longitude`, `days` (optional, default 7) | `{location, days: [{date, max_temp, min_temp, rain_probability, condition, ...}]}` |
| `/api/chat` | POST | `{message, latitude, longitude}` | `{answer, location}` |
| `/api/alerts` | GET | `latitude`, `longitude` | `{has_alert, severity, type, message}` |

All responses are plain JSON. No authentication required for the prototype.

---

## Development Phases

| Phase | Status | Description |
|---|---|---|
| 1 | ✅ Complete | Project setup, health endpoint |
| 2 | ✅ Complete | Live weather data (Open-Meteo) |
| 3 | ✅ Complete | 7-day forecast data |
| 4 | ✅ Complete | WeatherGPT Chat (OpenAI) |
| 5 | ✅ Complete | Smart Alerts (rule-based) |
| 6 | ✅ Complete | Flutter integration prep |
