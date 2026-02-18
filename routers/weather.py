"""Weather trigger endpoints."""

from fastapi import APIRouter
from engines.weather_trigger import check_weather

router = APIRouter(prefix="/api", tags=["weather"])


@router.get("/weather/{city}")
async def get_weather(city: str):
    return await check_weather(city)
