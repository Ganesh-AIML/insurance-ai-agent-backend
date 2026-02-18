"""Recommendation endpoints."""

import json
import os
from fastapi import APIRouter, HTTPException

from engines.recommendation_engine import get_recommendations, load_products
from engines.risk_scorer import calculate_risk_score
from engines.life_event_detector import detect_life_events
from engines.memory_engine import get_customer_memory
from engines.explainability import generate_explainability

router = APIRouter(prefix="/api", tags=["recommendations"])

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def _find_customer(customer_id: str):
    with open(os.path.join(DATA_DIR, "customers.json"), "r") as f:
        customers = json.load(f)
    for c in customers:
        if c["id"] == customer_id:
            return c
    return None


@router.get("/customers/{customer_id}/recommendations")
async def get_customer_recommendations(customer_id: str):
    customer = _find_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")

    memory = get_customer_memory(customer_id)
    recommendations = get_recommendations(customer, memory)

    # Add explainability to each recommendation
    for rec in recommendations["recommended_products"]:
        rec["explainability"] = generate_explainability(rec, customer)

    return recommendations


@router.get("/customers/{customer_id}/risk-score")
async def get_risk_score(customer_id: str):
    customer = _find_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    return calculate_risk_score(customer)


@router.get("/customers/{customer_id}/life-events")
async def get_life_events(customer_id: str):
    customer = _find_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    return detect_life_events(customer)


@router.get("/customers/{customer_id}/memory")
async def get_memory(customer_id: str):
    return get_customer_memory(customer_id)
