"""Campaign simulation endpoint - the star endpoint."""

import json
import os
from fastapi import APIRouter, HTTPException

from engines.risk_scorer import calculate_risk_score
from engines.life_event_detector import detect_life_events
from engines.memory_engine import get_customer_memory
from engines.sentiment_analyzer import analyze_sentiment
from engines.crisis_guard import check_crisis
from engines.recommendation_engine import get_recommendations, load_products
from engines.channel_optimizer import select_channel
from engines.timing_optimizer import optimize_timing
from engines.explainability import generate_explainability
from engines.weather_trigger import check_weather
from generators.message_generator import generate_all_messages
from generators.whatif_generator import generate_whatif
from generators.battlecard_generator import generate_battlecard

router = APIRouter(prefix="/api", tags=["campaign"])

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def _find_customer(customer_id: str):
    with open(os.path.join(DATA_DIR, "customers.json"), "r") as f:
        customers = json.load(f)
    for c in customers:
        if c["id"] == customer_id:
            return c
    return None


@router.post("/campaign/simulate/{customer_id}")
async def simulate_campaign(customer_id: str):
    pipeline_log = []

    # Step 1: Load Customer
    customer = _find_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    pipeline_log.append(f"Step 1: Loaded customer {customer['name']} ({customer_id})")

    # Step 2: Risk Score
    risk_score = calculate_risk_score(customer)
    pipeline_log.append(f"Step 2: Calculated risk score — {risk_score['risk_score']} ({risk_score['risk_level']})")

    # Step 3: Life Events
    life_events = detect_life_events(customer)
    pipeline_log.append(f"Step 3: Detected {life_events['total_detected']} life events")

    # Step 4: Memory Check
    memory = get_customer_memory(customer_id)
    pipeline_log.append(f"Step 4: Memory check — {memory['total_rejections']} past rejections, {len(memory['blocked_products'])} blocked products")

    # Step 5: Sentiment Analysis
    sentiment_result = await analyze_sentiment(customer)
    pipeline_log.append(f"Step 5: Sentiment analysis — {sentiment_result.get('sentiment', 'neutral')} (confidence: {sentiment_result.get('confidence', 0):.0%})")

    # Step 6: Crisis Guard
    crisis_status = check_crisis(customer, sentiment_result)
    pipeline_log.append(f"Step 6: Crisis guard — status: {crisis_status['status']}, mode: {crisis_status['mode']}")

    # Step 7: Weather Check
    city = customer.get("city", "Mumbai")
    weather_check = await check_weather(city)
    pipeline_log.append(f"Step 7: Weather check for {city} — alert level: {weather_check['alert_level']}")

    # Step 8: Recommendations
    recommendations = get_recommendations(customer, memory)
    for rec in recommendations["recommended_products"]:
        rec["explainability"] = generate_explainability(rec, customer)
    pipeline_log.append(f"Step 8: Generated {len(recommendations['recommended_products'])} product recommendations")

    # Select top product
    products_map = {p["id"]: p for p in load_products()}
    selected_product = None
    top_rec = None
    if recommendations["recommended_products"]:
        top_rec = recommendations["recommended_products"][0]
        selected_product = products_map.get(top_rec["product_id"])
        pipeline_log.append(f"Step 8b: Top recommendation — {top_rec['product_name']} (score: {top_rec['match_score']})")

    # Step 9: Channel & Timing
    channel_decision = None
    timing_decision = None
    if selected_product:
        match_score = top_rec["match_score"] if top_rec else 50
        channel_decision = select_channel(customer, selected_product, match_score)
        timing_decision = optimize_timing(customer, selected_product, channel_decision, memory, crisis_status)
        pipeline_log.append(f"Step 9: Channel → {channel_decision['primary_channel']}, Timing → {timing_decision['urgency_level']}")

    # Step 10: Generate Messages
    generated_messages = {}
    if selected_product:
        mode = crisis_status.get("mode", "sales")
        feature_importance = top_rec.get("feature_importance", {}) if top_rec else {}
        generated_messages = await generate_all_messages(
            customer, selected_product, mode,
            memory.get("memory_context", ""), feature_importance
        )
        pipeline_log.append(f"Step 10: Generated messages for all 4 channels (mode: {mode})")

    # Step 11: What-If
    whatif_projection = {}
    if selected_product:
        whatif_projection = await generate_whatif(customer, selected_product)
        pipeline_log.append("Step 11: Generated What-If projection")

    # Step 12: Battlecard
    battlecard = {}
    if selected_product:
        match_score = top_rec["match_score"] if top_rec else 50
        battlecard = await generate_battlecard(
            customer, selected_product, match_score, memory.get("memory_context", "")
        )
        pipeline_log.append("Step 12: Generated agent battlecard")

    pipeline_log.append("Pipeline complete!")

    return {
        "customer": customer,
        "risk_score": risk_score,
        "life_events": life_events,
        "memory_check": memory,
        "sentiment_check": sentiment_result,
        "crisis_guard": crisis_status,
        "weather_check": weather_check,
        "recommendations": recommendations,
        "selected_product": selected_product,
        "channel_decision": channel_decision,
        "timing_decision": timing_decision,
        "generated_messages": generated_messages,
        "whatif_projection": whatif_projection,
        "battlecard": battlecard,
        "explainability": top_rec.get("explainability") if top_rec else {},
        "pipeline_log": pipeline_log
    }
