import httpx
import os


WEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
DEFAULT_CITY = os.getenv("WEATHER_DEFAULT_CITY", "Toronto")


async def get_weather(city: str = DEFAULT_CITY) -> dict:
    """
    Fetch current weather from OpenWeatherMap (free tier).
    Returns a dict with temperature, description, humidity, wind.
    Falls back gracefully if API key not set.
    """
    if not WEATHER_API_KEY:
        return {
            "city": city,
            "temperature": "N/A",
            "description": "Weather service not configured",
            "humidity": "N/A",
            "wind_speed": "N/A",
        }

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": WEATHER_API_KEY,
        "units": "metric",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return {
                "city": data.get("name", city),
                "temperature": f"{data['main']['temp']}°C",
                "description": data["weather"][0]["description"].capitalize(),
                "humidity": f"{data['main']['humidity']}%",
                "wind_speed": f"{data['wind']['speed']} m/s",
            }
        except Exception as e:
            return {
                "city": city,
                "temperature": "N/A",
                "description": f"Could not fetch weather: {str(e)}",
                "humidity": "N/A",
                "wind_speed": "N/A",
            }
