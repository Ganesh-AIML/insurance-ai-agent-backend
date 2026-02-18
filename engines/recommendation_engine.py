"""Product recommendation engine - weighted scoring system."""

import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def load_products():
    with open(os.path.join(DATA_DIR, "products.json"), "r") as f:
        return json.load(f)


def _parse_premium_monthly(premium_range: str) -> float:
    """Extract approximate monthly premium from range string."""
    try:
        parts = premium_range.split("/")
        period = parts[1] if len(parts) > 1 else "month"
        nums = parts[0].replace(",", "").split("-")
        avg = (float(nums[0]) + float(nums[-1])) / 2
        if period == "year":
            avg /= 12
        elif period in ("trip", "event", "day"):
            avg *= 1  # treat as one-time
        return avg
    except (ValueError, IndexError):
        return 1000


def calculate_match_score(customer: dict, product: dict, memory_context: dict = None) -> dict:
    score = 0
    importance = {}

    # Check if already owned
    existing = [p.lower().replace(" ", "_") for p in customer.get("existing_policies", [])]
    product_cat = product.get("category", "")

    # Map existing policies to categories
    owned_categories = set()
    for p in existing:
        if "health" in p:
            owned_categories.add("health")
        if "life" in p or "term" in p:
            owned_categories.add("life")
        if "motor" in p:
            owned_categories.add("motor")
        if "home" in p or "property" in p:
            owned_categories.add("property")
        if "travel" in p:
            owned_categories.add("travel")
        if "child" in p or "education" in p:
            owned_categories.add("investment")

    if product_cat in owned_categories and product_cat not in ("parametric",):
        return {
            "product_id": product["id"],
            "product_name": product["name"],
            "match_score": 0,
            "feature_importance": {"Already owns this category": 0},
            "explanation_summary": f"Customer already has {product_cat} coverage.",
            "blocked": True
        }

    # 1. Life Event Match (+30)
    customer_events = [e["event"] for e in customer.get("life_events", [])]
    target_events = product.get("target_life_events", [])
    matching_events = set(customer_events) & set(target_events)
    if matching_events:
        score += 30
        events_str = ", ".join(matching_events)
        importance[f"Life events match ({events_str})"] = 30

    # Also check engagement -> marriage mapping
    if "engagement" in customer_events and "marriage" in target_events:
        if "engagement" not in target_events:
            score += 15
            importance["Upcoming marriage (engaged)"] = 15

    # 2. Age Fit (+15, +10 sweet spot)
    age = customer.get("age", 30)
    target_age = product.get("target_age", [0, 100])
    if target_age[0] <= age <= target_age[1]:
        score += 15
        importance[f"Age {age} within target range"] = 15

        # Sweet spot bonuses
        if product["id"] == "term_life" and 28 <= age <= 35:
            score += 10
            importance[f"Age in sweet spot ({age}) for term life"] = 10
        elif product["id"] == "child_education" and 28 <= age <= 40:
            score += 10
            importance[f"Age in sweet spot ({age}) for child plan"] = 10
        elif product["id"] in ("micro_weather", "micro_adventure") and 20 <= age <= 35:
            score += 10
            importance[f"Age in sweet spot ({age}) for micro-insurance"] = 10

    # 3. Gap Analysis (+20)
    if product_cat not in owned_categories:
        score += 20
        importance[f"No existing {product_cat} cover"] = 20

    # 4. Income Fit (+15)
    income = customer.get("annual_income", 500000)
    monthly_income = income / 12
    monthly_premium = _parse_premium_monthly(product.get("premium_range", "500-1000/month"))
    if monthly_premium < monthly_income * 0.10:
        score += 15
        importance["Income supports premium"] = 15
    elif monthly_premium < monthly_income * 0.20:
        score += 8
        importance["Premium is affordable but stretching"] = 8

    # 5. Dependents Factor (+10)
    dependents = customer.get("dependents", 0)
    if dependents > 0 and product_cat in ("life", "health", "investment"):
        score += 10
        importance[f"{dependents} dependent(s) need protection"] = 10

    # 6. Risk Score Adjustment (+10)
    from engines.risk_scorer import calculate_risk_score
    risk = calculate_risk_score(customer)
    if risk["risk_level"] == "high" and product_cat in ("health", "life"):
        score += 10
        importance["High risk profile needs comprehensive cover"] = 10

    # Additional contextual boosts
    if product["id"] == "travel_insurance":
        txns = customer.get("monthly_transactions", [])
        travel_spend = sum(t["amount"] for t in txns if "travel" in t.get("category", ""))
        if travel_spend > 30000:
            score += 10
            importance[f"High travel spending (₹{travel_spend:,})"] = 10

    if product["id"] == "micro_adventure":
        txns = customer.get("monthly_transactions", [])
        adventure_spend = sum(t["amount"] for t in txns if "adventure" in t.get("category", ""))
        if adventure_spend > 0:
            score += 15
            importance[f"Adventure sports enthusiast"] = 15

    score = min(score, 100)

    # Generate explanation
    top_factors = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:3]
    explanation_parts = [f[0] for f in top_factors]
    explanation = f"Based on: {', '.join(explanation_parts).lower()}."

    return {
        "product_id": product["id"],
        "product_name": product["name"],
        "category": product_cat,
        "match_score": score,
        "feature_importance": importance,
        "explanation_summary": explanation,
        "blocked": False
    }


def get_recommendations(customer: dict, memory_context: dict = None) -> dict:
    products = load_products()
    results = []

    for product in products:
        result = calculate_match_score(customer, product, memory_context)
        if not result.get("blocked") and result["match_score"] > 0:
            results.append(result)

    results.sort(key=lambda x: x["match_score"], reverse=True)
    top_3 = results[:3]

    return {
        "recommended_products": top_3,
        "total_evaluated": len(products),
        "customer_id": customer["id"]
    }
