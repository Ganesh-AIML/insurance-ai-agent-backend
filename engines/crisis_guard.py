"""Crisis detection and pause logic."""

from datetime import datetime


def check_crisis(customer: dict, sentiment_result: dict = None) -> dict:
    sentiment_state = customer.get("sentiment_state", "neutral")
    ticket = customer.get("last_support_ticket")
    now = datetime.now()

    status = "active"
    mode = "sales"
    reason = None
    signals = []

    # Check support ticket recency
    if ticket:
        try:
            ticket_date = datetime.strptime(ticket["date"], "%Y-%m-%d")
            days_since = (now - ticket_date).days
            if days_since < 7:
                signals.append(f"Open support ticket ({days_since}d ago): {ticket.get('subject', 'N/A')}")
                if ticket.get("status") == "open":
                    signals.append("Ticket still unresolved")
        except (ValueError, KeyError):
            pass

    # Check base sentiment
    if sentiment_state in ("negative", "distressed"):
        signals.append(f"Customer sentiment: {sentiment_state}")

    # Use LLM sentiment result if available
    if sentiment_result:
        llm_sentiment = sentiment_result.get("sentiment", "neutral")
        if llm_sentiment in ("negative", "distressed"):
            signals.append(f"AI sentiment analysis: {llm_sentiment} (confidence: {sentiment_result.get('confidence', 0):.0%})")
            if sentiment_result.get("key_signals"):
                signals.extend(sentiment_result["key_signals"][:3])

    # Determine crisis status
    if any("distressed" in s.lower() for s in signals):
        status = "paused"
        mode = "empathy"
        reason = "Customer shows signs of distress — all marketing paused"
    elif len(signals) >= 2:
        status = "paused"
        mode = "empathy"
        reason = "Multiple negative signals detected — marketing paused for empathy outreach"
    elif signals:
        status = "active"
        mode = "empathy"
        reason = "Some negative signals — proceed with empathetic tone only"

    if not reason:
        reason = "No crisis signals — marketing active"

    return {
        "status": status,
        "mode": mode,
        "reason": reason,
        "signals": signals,
        "sentiment_state": sentiment_state,
        "has_open_ticket": bool(ticket and ticket.get("status") == "open"),
        "campaign_allowed": status == "active"
    }
