import asyncio, traceback
from app.services.weather_service import get_current_weather, get_forecast
from app.services.ai_service import get_weather_answer

async def test():
    try:
        w = await get_current_weather(28.61, 77.23)
        f = await get_forecast(28.61, 77.23, 7)
        print('Weather fetch OK')
    except Exception as e:
        print('Weather error:', e)
        return
    
    try:
        answer = await get_weather_answer('Will it rain today?', w, f, language='en', mode='general')
        print('AI answer (first 150 chars):', answer[:150])
        print('SUCCESS')
    except Exception as e:
        print('AI error:', type(e).__name__, str(e)[:200])
        traceback.print_exc()

asyncio.run(test())