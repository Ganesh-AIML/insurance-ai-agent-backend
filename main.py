"""FastAPI application entry point."""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(env_path)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import customers, recommendations, messages, weather, sentiment, campaign

app = FastAPI(
    title="AI Insurance Marketing Agent",
    description="Hyper-Personalized Insurance Marketing Agent powered by AI",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(customers.router)
app.include_router(recommendations.router)
app.include_router(messages.router)
app.include_router(weather.router)
app.include_router(sentiment.router)
app.include_router(campaign.router)


@app.get("/")
async def root():
    return {
        "name": "AI Insurance Marketing Agent",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "customers": "/api/customers",
            "products": "/api/products",
            "recommendations": "/api/customers/{id}/recommendations",
            "risk_score": "/api/customers/{id}/risk-score",
            "life_events": "/api/customers/{id}/life-events",
            "memory": "/api/customers/{id}/memory",
            "sentiment": "/api/customers/{id}/sentiment",
            "generate_message": "/api/customers/{id}/generate-message",
            "generate_all_messages": "/api/customers/{id}/generate-all-messages",
            "whatif": "/api/customers/{id}/whatif",
            "battlecard": "/api/customers/{id}/battlecard",
            "weather": "/api/weather/{city}",
            "campaign_simulate": "/api/campaign/simulate/{id}"
        }
    }


@app.get("/api/health")
async def health():
    openai_key = bool(os.getenv("OPENAI_API_KEY"))
    weather_key = bool(os.getenv("WEATHER_API_KEY"))
    return {
        "status": "healthy",
        "openai_configured": openai_key,
        "weather_configured": weather_key,
        "mode": "live" if openai_key else "mock"
    }
