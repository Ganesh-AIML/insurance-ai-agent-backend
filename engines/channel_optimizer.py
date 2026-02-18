"""Channel selection optimizer - pure rule-based."""


def select_channel(customer: dict, product: dict, match_score: int) -> dict:
    prefs = customer.get("channel_preferences", {})
    age = customer.get("age", 30)
    income = customer.get("annual_income", 500000)
    sentiment = customer.get("sentiment_state", "neutral")
    is_parametric = product.get("parametric", False)

    # Sort channels by open rate
    channels = sorted(prefs.items(), key=lambda x: x[1].get("open_rate", 0), reverse=True)
    reasoning = []

    if not channels:
        return {
            "primary_channel": "email",
            "secondary_channel": "sms",
            "reasoning": ["No channel preferences available, defaulting to email"],
            "preferred_time": "10:00"
        }

    primary = channels[0][0]
    secondary = channels[1][0] if len(channels) > 1 else "email"
    reasoning.append(f"Highest open rate: {primary} ({prefs[primary]['open_rate']*100:.0f}%)")

    # Override: Parametric/micro-insurance → urgency channels
    if is_parametric:
        if "app_push" in prefs:
            primary = "app_push"
            secondary = "whatsapp"
            reasoning.append("Parametric product → urgency channel (app push)")
        elif "whatsapp" in prefs:
            primary = "whatsapp"
            secondary = "app_push"
            reasoning.append("Parametric product → urgency channel (WhatsApp)")

    # Override: Senior citizen → prefer SMS/email
    if age > 55:
        if primary in ("whatsapp", "app_push"):
            old_primary = primary
            primary = "sms" if prefs.get("sms", {}).get("open_rate", 0) > prefs.get("email", {}).get("open_rate", 0) else "email"
            secondary = "sms" if primary == "email" else "email"
            reasoning.append(f"Senior customer (age {age}) → switched from {old_primary} to {primary}")

    # Override: Negative sentiment → less intrusive channel
    if sentiment == "negative":
        if primary in ("sms", "app_push", "whatsapp"):
            primary = "email"
            reasoning.append("Negative sentiment → switched to email (less intrusive)")

    # Add agent handoff for high-value leads
    agent_handoff = False
    if match_score > 85 and income > 2000000:
        agent_handoff = True
        reasoning.append(f"High-value lead (score {match_score}, income ₹{income:,}) → agent handoff recommended")

    preferred_time = prefs.get(primary, {}).get("preferred_time", "10:00")

    return {
        "primary_channel": primary,
        "secondary_channel": secondary,
        "agent_handoff": agent_handoff,
        "reasoning": reasoning,
        "preferred_time": preferred_time,
        "channel_scores": {ch: data.get("open_rate", 0) for ch, data in prefs.items()}
    }
