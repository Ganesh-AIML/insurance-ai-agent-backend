"""Parametric weather trigger logic."""

import os
import random
import httpx

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")

# City coordinates for India
CITY_COORDS = {
    "Mumbai": {"lat": 19.076, "lon": 72.8777},
    "Delhi": {"lat": 28.6139, "lon": 77.209},
    "Bengaluru": {"lat": 12.9716, "lon": 77.5946},
    "Chennai": {"lat": 13.0827, "lon": 80.2707},
    "Kolkata": {"lat": 22.5726, "lon": 88.3639},
    "Jaipur": {"lat": 26.9124, "lon": 75.7873},
    "Lucknow": {"lat": 26.8467, "lon": 80.9462},
    "Kochi": {"lat": 9.9312, "lon": 76.2673},
    "Bhubaneswar": {"lat": 20.2961, "lon": 85.8245},
    "Chandigarh": {"lat": 30.7333, "lon": 76.7794},
    "Ahmedabad": {"lat": 23.0225, "lon": 72.5714},
}

# Mock severe weather for demo
MOCK_SEVERE_CITIES = {"Bhubaneswar", "Mumbai", "Kolkata", "Chennai"}


def _get_mock_weather(city: str) -> dict:
    if city in MOCK_SEVERE_CITIES:
        conditions = {
            "Bhubaneswar": {"main": "Thunderstorm", "description": "severe thunderstorm with heavy rain", "temp": 28, "humidity": 95, "rain_1h": 45},
            "Mumbai": {"main": "Rain", "description": "heavy intensity rain", "temp": 30, "humidity": 90, "rain_1h": 35},
            "Kolkata": {"main": "Thunderstorm", "description": "thunderstorm with flooding risk", "temp": 29, "humidity": 92, "rain_1h": 50},
            "Chennai": {"main": "Extreme", "description": "cyclone warning in effect", "temp": 31, "humidity": 88, "rain_1h": 40},
        }
        return conditions.get(city, {"main": "Clear", "description": "clear sky", "temp": 32, "humidity": 50, "rain_1h": 0})

    return {
        "main": random.choice(["Clear", "Clouds", "Haze"]),
        "description": random.choice(["clear sky", "partly cloudy", "light haze"]),
        "temp": random.randint(20, 38),
        "humidity": random.randint(30, 70),
        "rain_1h": 0
    }


async def check_weather(city: str) -> dict:
    weather_data = None
    source = "mock"

    if WEATHER_API_KEY:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"https://api.openweathermap.org/data/2.5/weather",
                    params={"q": f"{city},IN", "appid": WEATHER_API_KEY, "units": "metric"},
                    timeout=5.0
                )
                if resp.status_code == 200:
                    data = resp.json()
                    weather_data = {
                        "main": data["weather"][0]["main"],
                        "description": data["weather"][0]["description"],
                        "temp": data["main"]["temp"],
                        "humidity": data["main"]["humidity"],
                        "rain_1h": data.get("rain", {}).get("1h", 0)
                    }
                    source = "live"
        except Exception:
            pass

    if not weather_data:
        weather_data = _get_mock_weather(city)
        source = "mock"

    # Evaluate triggers
    alert_level = "normal"
    triggered_product = None
    offer_details = None
    trigger_reason = None

    main = weather_data["main"].lower()
    temp = weather_data.get("temp", 30)
    rain = weather_data.get("rain_1h", 0)

    if main in ("thunderstorm", "extreme") or any(kw in weather_data.get("description", "").lower() for kw in ("flood", "cyclone", "storm")):
        alert_level = "severe"
        triggered_product = "micro_weather"
        trigger_reason = f"Severe weather: {weather_data['description']}"
        offer_details = {
            "product": "FlashCover Weather Shield",
            "premium": "₹99-299",
            "cover": "₹1,00,000",
            "valid_hours": 48,
            "auto_payout": True
        }
    elif rain > 30:
        alert_level = "high"
        triggered_product = "micro_weather"
        trigger_reason = f"Heavy rainfall: {rain}mm/hr"
        offer_details = {
            "product": "FlashCover Weather Shield",
            "premium": "₹49-149",
            "cover": "₹50,000",
            "valid_hours": 48,
            "auto_payout": True
        }
    elif temp > 45:
        alert_level = "high"
        triggered_product = "micro_weather"
        trigger_reason = f"Extreme heat: {temp}°C"
        offer_details = {
            "product": "FlashCover Weather Shield — Heat Cover",
            "premium": "₹49-99",
            "cover": "₹25,000",
            "valid_hours": 48,
            "auto_payout": True
        }

    return {
        "city": city,
        "weather_status": weather_data,
        "alert_level": alert_level,
        "triggered_product": triggered_product,
        "trigger_reason": trigger_reason,
        "offer_details": offer_details,
        "valid_for_hours": 48 if triggered_product else None,
        "source": source,
        "coordinates": CITY_COORDS.get(city, {})
    }
