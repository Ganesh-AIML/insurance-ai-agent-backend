"""Sentiment analysis endpoints."""

import json
import os
from fastapi import APIRouter, HTTPException

from engines.sentiment_analyzer import analyze_sentiment
from engines.crisis_guard import check_crisis

router = APIRouter(prefix="/api", tags=["sentiment"])

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def _find_customer(customer_id: str):
    with open(os.path.join(DATA_DIR, "customers.json"), "r") as f:
        customers = json.load(f)
    for c in customers:
        if c["id"] == customer_id:
            return c
    return None


@router.get("/customers/{customer_id}/sentiment")
async def get_sentiment(customer_id: str):
    customer = _find_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")

    sentiment_result = await analyze_sentiment(customer)
    crisis_status = check_crisis(customer, sentiment_result)

    return {
        "sentiment": sentiment_result,
        "crisis_guard": crisis_status
    }
