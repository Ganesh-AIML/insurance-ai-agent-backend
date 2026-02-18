"""Send-time optimization - pure rule-based."""

from datetime import datetime, timedelta


def optimize_timing(customer: dict, product: dict, channel_decision: dict,
                    memory_context: dict = None, crisis_status: dict = None) -> dict:
    reasoning = []

    base_time = channel_decision.get("preferred_time", "10:00")
    reasoning.append(f"Base time from {channel_decision['primary_channel']} preference: {base_time}")

    now = datetime.now()
    send_date = now
    urgency = "standard"

    # Check crisis guard
    if crisis_status and crisis_status.get("status") == "paused":
        return {
            "recommended_send_time": "PAUSED",
            "send_date": None,
            "urgency_level": "paused",
            "reasoning": [f"PAUSED — {crisis_status.get('reason', 'Crisis detected')}"],
            "preferred_time": base_time
        }

    # Check parametric/weather products → immediate
    is_parametric = product.get("parametric", False)
    if is_parametric:
        urgency = "immediate"
        send_date = now
        reasoning.append("Parametric product → send immediately (time-sensitive)")
        return {
            "recommended_send_time": now.strftime("%Y-%m-%d %H:%M"),
            "send_date": now.strftime("%Y-%m-%d"),
            "urgency_level": "immediate",
            "reasoning": reasoning,
            "preferred_time": base_time
        }

    # Check recent life events → within 48h
    life_events = customer.get("life_events", [])
    for event in life_events:
        try:
            event_date = datetime.strptime(event["date"], "%Y-%m-%d")
            if (now - event_date).days <= 30:
                urgency = "within_48h"
                send_date = now + timedelta(hours=24)
                reasoning.append(f"Recent life event ({event['event']}) within 30 days → send within 48h")
                break
        except (ValueError, KeyError):
            pass

    # Check rejection history
    if memory_context:
        rejections = memory_context.get("rejections", [])
        for rej in rejections:
            try:
                rej_date = datetime.strptime(rej["date"], "%Y-%m-%d")
                days_since = (now - rej_date).days
                reason = rej.get("reason", "")

                if days_since < 14 and reason == "not_interested":
                    urgency = "delayed"
                    send_date = rej_date + timedelta(days=60)
                    reasoning.append(f"Recent 'not interested' rejection ({days_since}d ago) → delay 60 days")
                elif days_since < 30:
                    if urgency != "delayed":
                        urgency = "delayed"
                        send_date = rej_date + timedelta(days=30)
                        reasoning.append(f"Recent rejection ({days_since}d ago) → delay 30 days")
            except (ValueError, KeyError):
                pass

    if urgency == "standard":
        send_date = now + timedelta(days=1)
        reasoning.append("No urgency modifiers → standard scheduling for tomorrow")

    return {
        "recommended_send_time": f"{send_date.strftime('%Y-%m-%d')} {base_time}",
        "send_date": send_date.strftime("%Y-%m-%d"),
        "urgency_level": urgency,
        "reasoning": reasoning,
        "preferred_time": base_time
    }
