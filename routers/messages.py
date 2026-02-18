"""Message generation endpoints."""

import json
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from generators.message_generator import generate_message, generate_all_messages
from generators.whatif_generator import generate_whatif
from generators.battlecard_generator import generate_battlecard
from engines.recommendation_engine import get_recommendations, load_products
from engines.memory_engine import get_customer_memory

router = APIRouter(prefix="/api", tags=["messages"])

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def _find_customer(customer_id: str):
    with open(os.path.join(DATA_DIR, "customers.json"), "r") as f:
        customers = json.load(f)
    for c in customers:
        if c["id"] == customer_id:
            return c
    return None


def _find_product(product_id: str):
    products = load_products()
    for p in products:
        if p["id"] == product_id:
            return p
    return None


class MessageRequest(BaseModel):
    product_id: str
    channel: str = "email"
    mode: str = "sales"


class ProductRequest(BaseModel):
    product_id: str


@router.post("/customers/{customer_id}/generate-message")
async def gen_message(customer_id: str, req: MessageRequest):
    customer = _find_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")

    product = _find_product(req.product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {req.product_id} not found")

    memory = get_customer_memory(customer_id)
    recs = get_recommendations(customer, memory)
    feature_importance = {}
    for r in recs["recommended_products"]:
        if r["product_id"] == req.product_id:
            feature_importance = r.get("feature_importance", {})
            break

    result = await generate_message(
        customer, product, req.channel, req.mode,
        memory.get("memory_context", ""), feature_importance
    )
    return result


@router.post("/customers/{customer_id}/generate-all-messages")
async def gen_all_messages(customer_id: str, req: ProductRequest):
    customer = _find_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")

    product = _find_product(req.product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {req.product_id} not found")

    memory = get_customer_memory(customer_id)
    recs = get_recommendations(customer, memory)
    feature_importance = {}
    for r in recs["recommended_products"]:
        if r["product_id"] == req.product_id:
            feature_importance = r.get("feature_importance", {})
            break

    crisis_status = None
    from engines.crisis_guard import check_crisis
    crisis_status = check_crisis(customer)
    mode = crisis_status.get("mode", "sales")

    result = await generate_all_messages(
        customer, product, mode,
        memory.get("memory_context", ""), feature_importance
    )
    return result


@router.post("/customers/{customer_id}/whatif")
async def gen_whatif(customer_id: str, req: ProductRequest):
    customer = _find_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")

    product = _find_product(req.product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {req.product_id} not found")

    return await generate_whatif(customer, product)


@router.post("/customers/{customer_id}/battlecard")
async def gen_battlecard(customer_id: str, req: ProductRequest):
    customer = _find_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")

    product = _find_product(req.product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {req.product_id} not found")

    memory = get_customer_memory(customer_id)
    recs = get_recommendations(customer, memory)
    match_score = 70
    for r in recs["recommended_products"]:
        if r["product_id"] == req.product_id:
            match_score = r["match_score"]
            break

    return await generate_battlecard(customer, product, match_score, memory.get("memory_context", ""))
