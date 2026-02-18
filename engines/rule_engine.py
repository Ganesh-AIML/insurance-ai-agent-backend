"""Central rule engine - orchestrates all rule-based engines."""

from engines.risk_scorer import calculate_risk_score
from engines.life_event_detector import detect_life_events
from engines.recommendation_engine import get_recommendations
from engines.channel_optimizer import select_channel
from engines.timing_optimizer import optimize_timing
from engines.memory_engine import get_customer_memory
from engines.crisis_guard import check_crisis
from engines.explainability import generate_explainability


def run_full_pipeline(customer: dict, product: dict = None, sentiment_result: dict = None) -> dict:
    """Run the complete rule engine pipeline for a customer."""

    risk = calculate_risk_score(customer)
    life_events = detect_life_events(customer)
    memory = get_customer_memory(customer["id"])
    crisis = check_crisis(customer, sentiment_result)
    recommendations = get_recommendations(customer, memory)

    selected_product = product
    if not selected_product and recommendations["recommended_products"]:
        # Load product details for the top recommendation
        from engines.recommendation_engine import load_products
        products = {p["id"]: p for p in load_products()}
        top_rec = recommendations["recommended_products"][0]
        selected_product = products.get(top_rec["product_id"], {})

    channel_decision = None
    timing_decision = None

    if selected_product:
        match_score = 0
        for rec in recommendations["recommended_products"]:
            if rec["product_id"] == selected_product.get("id"):
                match_score = rec["match_score"]
                break

        channel_decision = select_channel(customer, selected_product, match_score)
        timing_decision = optimize_timing(customer, selected_product, channel_decision, memory, crisis)

    return {
        "risk_score": risk,
        "life_events": life_events,
        "memory_check": memory,
        "crisis_status": crisis,
        "recommendations": recommendations,
        "selected_product": selected_product,
        "channel_decision": channel_decision,
        "timing_decision": timing_decision
    }
