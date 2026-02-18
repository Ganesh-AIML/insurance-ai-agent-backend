"""Contextual memory engine - tracks rejections and learning."""

import json
import os
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def load_memory_store():
    path = os.path.join(DATA_DIR, "memory_store.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}


def load_interaction_history():
    path = os.path.join(DATA_DIR, "interaction_history.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}


def get_customer_memory(customer_id: str) -> dict:
    memory_store = load_memory_store()
    history = load_interaction_history()

    customer_memory = memory_store.get(customer_id, {"rejections": [], "preferences_learned": []})
    customer_history = history.get(customer_id, [])

    now = datetime.now()
    blocked_products = []
    cooldown_products = []
    reapproach_products = []
    clear_products = []

    rejections = customer_memory.get("rejections", [])

    # Also scan interaction history for rejections not in memory store
    for interaction in customer_history:
        if interaction.get("response") == "rejected":
            already_tracked = any(
                r["product"] == interaction.get("product") and r["date"] == interaction.get("date")
                for r in rejections
            )
            if not already_tracked:
                rejections.append({
                    "product": interaction.get("product", "unknown"),
                    "category": _product_to_category(interaction.get("product", "")),
                    "date": interaction.get("date", ""),
                    "reason": interaction.get("reason", "unknown"),
                    "channel": interaction.get("channel", "unknown")
                })

    # Analyze each rejection
    for rej in rejections:
        try:
            rej_date = datetime.strptime(rej["date"], "%Y-%m-%d")
            days_since = (now - rej_date).days
        except (ValueError, KeyError):
            days_since = 999

        product = rej.get("product", "unknown")
        reason = rej.get("reason", "unknown")

        if reason == "already_covered":
            blocked_products.append({
                "product": product,
                "reason": "Customer already has coverage",
                "action": "remove_permanently",
                "days_since_rejection": days_since
            })
        elif reason == "not_interested" and days_since < 90:
            cooldown_products.append({
                "product": product,
                "reason": f"Not interested (rejected {days_since}d ago, 90d cooldown)",
                "action": "cooldown_90_days",
                "days_remaining": max(0, 90 - days_since),
                "days_since_rejection": days_since
            })
        elif reason == "too_expensive" and days_since < 30:
            cooldown_products.append({
                "product": product,
                "reason": f"Too expensive (rejected {days_since}d ago, waiting for income signal)",
                "action": "wait_for_income_bump",
                "days_remaining": max(0, 30 - days_since),
                "days_since_rejection": days_since
            })
        elif reason == "too_expensive" and days_since >= 30:
            reapproach_products.append({
                "product": product,
                "reason": "Previously rejected for price — try budget-friendly framing",
                "action": "reapproach_budget_friendly",
                "days_since_rejection": days_since
            })
        elif days_since < 30:
            cooldown_products.append({
                "product": product,
                "reason": f"Recently rejected ({days_since}d ago)",
                "action": "cooldown_30_days",
                "days_remaining": max(0, 30 - days_since),
                "days_since_rejection": days_since
            })

    blocked_ids = {p["product"] for p in blocked_products}
    cooldown_ids = {p["product"] for p in cooldown_products}
    rejected_ids = {rej.get("product") for rej in rejections}

    return {
        "customer_id": customer_id,
        "blocked_products": blocked_products,
        "cooldown_products": cooldown_products,
        "reapproach_products": reapproach_products,
        "rejection_history": rejections,
        "total_rejections": len(rejections),
        "preferences_learned": customer_memory.get("preferences_learned", []),
        "memory_context": _build_context_string(blocked_products, cooldown_products, reapproach_products)
    }


def _product_to_category(product_id: str) -> str:
    mapping = {
        "term_life": "life", "health_family": "health", "health_basic": "health",
        "child_education": "investment", "motor_comprehensive": "motor",
        "home_insurance": "property", "travel_insurance": "travel",
        "micro_weather": "parametric", "micro_adventure": "parametric"
    }
    return mapping.get(product_id, "unknown")


def _build_context_string(blocked, cooldown, reapproach) -> str:
    parts = []
    if blocked:
        parts.append(f"Blocked products: {', '.join(p['product'] for p in blocked)}")
    if cooldown:
        parts.append(f"In cooldown: {', '.join(p['product'] for p in cooldown)}")
    if reapproach:
        parts.append(f"Can re-approach with new framing: {', '.join(p['product'] for p in reapproach)}")
    return "; ".join(parts) if parts else "No rejection history — all products open."
