"""Sentiment analysis - LLM-based with mock fallback."""

import os
import json
from openai import AsyncOpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

SYSTEM_PROMPT = """Analyze the sentiment of this customer interaction text.
Return JSON only, no markdown: { "sentiment": "positive" | "neutral" | "negative" | "distressed", "confidence": 0.0-1.0, "key_signals": ["list of detected emotional signals"], "recommended_action": "proceed" | "pause" | "empathy_outreach" }"""


def _mock_sentiment(customer: dict) -> dict:
    sentiment = customer.get("sentiment_state", "neutral")
    ticket = customer.get("last_support_ticket")

    if ticket and ticket.get("status") == "open":
        text = ticket.get("text", "").lower()
        if any(w in text for w in ("harassment", "complaint", "irdai", "leave me alone")):
            return {
                "sentiment": "distressed",
                "confidence": 0.92,
                "key_signals": [
                    "[MOCK] Strong negative language detected",
                    "[MOCK] Regulatory complaint threat",
                    "[MOCK] Explicit opt-out request"
                ],
                "recommended_action": "pause"
            }
        elif any(w in text for w in ("frustrated", "disappointed", "unacceptable", "waiting")):
            return {
                "sentiment": "negative",
                "confidence": 0.85,
                "key_signals": [
                    "[MOCK] Frustration signals detected",
                    "[MOCK] Service dissatisfaction",
                    "[MOCK] Unresolved complaint"
                ],
                "recommended_action": "empathy_outreach"
            }

    if sentiment == "negative":
        return {
            "sentiment": "negative",
            "confidence": 0.70,
            "key_signals": ["[MOCK] Previously flagged negative sentiment"],
            "recommended_action": "empathy_outreach"
        }

    if sentiment == "positive":
        return {
            "sentiment": "positive",
            "confidence": 0.80,
            "key_signals": ["[MOCK] Positive engagement history"],
            "recommended_action": "proceed"
        }

    return {
        "sentiment": "neutral",
        "confidence": 0.75,
        "key_signals": ["[MOCK] No strong sentiment signals"],
        "recommended_action": "proceed"
    }


async def analyze_sentiment(customer: dict) -> dict:
    ticket = customer.get("last_support_ticket")
    interactions = customer.get("recent_interactions", [])

    # Build analysis text
    text_parts = []
    if ticket:
        text_parts.append(f"Support ticket ({ticket.get('subject', 'N/A')}): {ticket.get('text', '')}")
    for interaction in interactions[-3:]:
        text_parts.append(
            f"Interaction on {interaction.get('date')}: {interaction.get('type')} via {interaction.get('channel')} — "
            f"Response: {interaction.get('response')}, Reason: {interaction.get('reason', 'N/A')}"
        )

    if not text_parts:
        text_parts.append(f"Customer sentiment state: {customer.get('sentiment_state', 'neutral')}. No recent interactions.")

    analysis_text = "\n".join(text_parts)

    if not OPENAI_API_KEY:
        return _mock_sentiment(customer)

    try:
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": analysis_text}
            ],
            temperature=0.3,
            max_tokens=300
        )
        content = response.choices[0].message.content.strip()
        # Try to parse JSON
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)
    except Exception as e:
        result = _mock_sentiment(customer)
        result["error"] = f"LLM call failed: {str(e)}, using mock"
        return result
