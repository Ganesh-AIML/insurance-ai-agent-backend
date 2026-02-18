"""Risk scoring engine - pure rule-based logic."""

HIGH_RISK_OCCUPATIONS = {
    "construction", "mining", "delivery", "farmer", "driver",
    "construction contractor", "mining supervisor", "gig worker - delivery"
}


def calculate_risk_score(customer: dict) -> dict:
    score = 30
    factors = []

    age = customer.get("age", 30)
    if age > 60:
        score += 25
        factors.append({"factor": f"Age {age} (above 60)", "impact": 25})
    elif age > 50:
        score += 15
        factors.append({"factor": f"Age {age} (above 50)", "impact": 15})

    credit_score = customer.get("credit_score", 700)
    if credit_score < 600:
        score += 20
        factors.append({"factor": f"Low credit score ({credit_score})", "impact": 20})
    elif credit_score < 700:
        score += 10
        factors.append({"factor": f"Below-average credit score ({credit_score})", "impact": 10})

    interactions = customer.get("recent_interactions", [])
    claims = sum(1 for i in interactions if i.get("type") == "claim")
    if claims > 2:
        score += 15
        factors.append({"factor": f"Multiple claims ({claims})", "impact": 15})

    occupation = customer.get("occupation", "").lower()
    if any(occ in occupation for occ in HIGH_RISK_OCCUPATIONS):
        score += 10
        factors.append({"factor": f"High-risk occupation ({customer['occupation']})", "impact": 10})

    city = customer.get("city", "")
    tier3_cities = {"Bhubaneswar", "Lucknow", "Chandigarh"}
    if city in tier3_cities:
        score += 5
        factors.append({"factor": f"Tier 3 city ({city}) - limited healthcare", "impact": 5})

    score = min(score, 100)

    if score <= 35:
        risk_level = "low"
    elif score <= 60:
        risk_level = "medium"
    else:
        risk_level = "high"

    return {
        "risk_score": score,
        "risk_level": risk_level,
        "contributing_factors": factors,
        "base_score": 30
    }
