"""Life event detection from transaction patterns - pure rule-based."""


def detect_life_events(customer: dict) -> dict:
    detected_events = []
    transactions = customer.get("monthly_transactions", [])

    explicit_events = customer.get("life_events", [])

    for txn in transactions:
        category = txn.get("category", "").lower()
        amount = txn.get("amount", 0)
        month = txn.get("month", "")

        if category == "jewelry" and amount > 50000:
            detected_events.append({
                "event": "marriage_or_engagement",
                "confidence": 0.75,
                "evidence": f"High jewelry spend (₹{amount:,}) in {month}",
                "source": "transaction_pattern"
            })

        if category in ("baby_store", "pediatric"):
            detected_events.append({
                "event": "new_child",
                "confidence": 0.85,
                "evidence": f"Baby/pediatric spending (₹{amount:,}) in {month}",
                "source": "transaction_pattern"
            })

        if category in ("real_estate", "home_improvement") and amount > 100000:
            detected_events.append({
                "event": "home_purchase",
                "confidence": 0.80,
                "evidence": f"Large property/home spend (₹{amount:,}) in {month}",
                "source": "transaction_pattern"
            })

        if category == "travel_agency":
            detected_events.append({
                "event": "frequent_traveler",
                "confidence": 0.60,
                "evidence": f"Travel agency spend (₹{amount:,}) in {month}",
                "source": "transaction_pattern"
            })

        if category in ("university", "education") or (category == "education" and amount > 0):
            detected_events.append({
                "event": "child_education_need",
                "confidence": 0.70,
                "evidence": f"Education spending (₹{amount:,}) in {month}",
                "source": "transaction_pattern"
            })

        if category == "adventure_sports":
            detected_events.append({
                "event": "adventure_enthusiast",
                "confidence": 0.80,
                "evidence": f"Adventure sports spending (₹{amount:,}) in {month}",
                "source": "transaction_pattern"
            })

        if category == "wedding_venue":
            detected_events.append({
                "event": "upcoming_wedding",
                "confidence": 0.95,
                "evidence": f"Wedding venue booking (₹{amount:,}) in {month}",
                "source": "transaction_pattern"
            })

    for event in explicit_events:
        detected_events.append({
            "event": event["event"],
            "confidence": 1.0,
            "evidence": f"Self-reported on {event['date']}",
            "source": "customer_profile"
        })

    # Deduplicate by event type, keep highest confidence
    seen = {}
    for ev in detected_events:
        key = ev["event"]
        if key not in seen or ev["confidence"] > seen[key]["confidence"]:
            seen[key] = ev

    unique_events = list(seen.values())
    unique_events.sort(key=lambda x: x["confidence"], reverse=True)

    return {
        "detected_events": unique_events,
        "total_detected": len(unique_events),
        "high_confidence_events": [e for e in unique_events if e["confidence"] >= 0.75]
    }
