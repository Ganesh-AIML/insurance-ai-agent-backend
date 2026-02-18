"""Customer endpoints."""

import json
import os
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api", tags=["customers"])

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def _load_customers():
    with open(os.path.join(DATA_DIR, "customers.json"), "r") as f:
        return json.load(f)


def _find_customer(customer_id: str):
    customers = _load_customers()
    for c in customers:
        if c["id"] == customer_id:
            return c
    return None


@router.get("/customers")
async def list_customers():
    customers = _load_customers()
    return {"customers": customers, "total": len(customers)}


@router.get("/customers/{customer_id}")
async def get_customer(customer_id: str):
    customer = _find_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    return customer


@router.get("/products")
async def list_products():
    with open(os.path.join(DATA_DIR, "products.json"), "r") as f:
        products = json.load(f)
    return {"products": products, "total": len(products)}
