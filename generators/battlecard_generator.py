"""Agent co-pilot battlecard generator - LLM-powered with mock fallback."""

import os
import json
from openai import AsyncOpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

SYSTEM_PROMPT = """You are an AI sales assistant. Generate a "Battlecard" briefing for a human insurance agent about to call a warm lead.

Return JSON only, no markdown:
{
  "lead_summary": "2-sentence brief about who the customer is and why they're a warm lead",
  "conversion_probability": 65,
  "talking_points": ["point 1", "point 2", "point 3"],
  "objection_handlers": [
    {"objection": "likely objection 1", "response": "how to address it"},
    {"objection": "likely objection 2", "response": "how to address it"}
  ],
  "do_not_mention": ["topic to avoid 1"],
  "recommended_opening": "A suggested opening line for the call"
}

Use Indian context. Be specific and actionable. The conversion_probability should be a number 0-100 based on the match score and customer engagement level."""


def _mock_battlecard(customer: dict, product: dict, match_score: int = 70, memory_context: str = "") -> dict:
    name = customer.get("name", "Customer")
    age = customer.get("age", 30)
    occupation = customer.get("occupation", "Professional")
    city = customer.get("city", "Mumbai")
    income = customer.get("annual_income", 500000)
    events = [e["event"].replace("_", " ") for e in customer.get("life_events", [])]
    event_str = events[0] if events else "financial planning"

    conv_prob = min(95, max(20, match_score - 5))

    do_not_mention = []
    rejections = customer.get("recent_interactions", [])
    for r in rejections:
        if r.get("response") == "rejected":
            if r.get("reason") == "too_expensive":
                do_not_mention.append("High premium amounts or luxury features")
            elif r.get("reason") == "not_interested":
                do_not_mention.append(f"Previous {r.get('product', 'product')} offer")

    if not do_not_mention:
        do_not_mention.append("Competitor comparisons unless customer brings it up")

    return {
        "lead_summary": f"[MOCK] {name} is a {age}-year-old {occupation} from {city} with an annual income of ₹{income:,}. Recent {event_str} makes them a strong candidate for {product.get('name', 'this product')}.",
        "conversion_probability": conv_prob,
        "talking_points": [
            f"[MOCK] Congratulate on their {event_str} and naturally connect it to financial planning",
            f"[MOCK] Highlight that {product.get('name', 'this plan')} starts at just {product.get('premium_range', '₹500/month')} — affordable for their income bracket",
            f"[MOCK] Mention the tax benefits under Section 80C/80D — especially relevant given their {occupation} background"
        ],
        "objection_handlers": [
            {
                "objection": "[MOCK] \"I'll think about it / Not right now\"",
                "response": "I completely understand. Financial decisions deserve careful thought. Could I just share a quick 2-minute illustration specific to your situation? That way you'll have all the info when you're ready to decide."
            },
            {
                "objection": "[MOCK] \"I already have some coverage\"",
                "response": f"That's great that you're already thinking about protection! Many of our customers in {city} find that their existing coverage has gaps, especially after major life events. Would you like me to do a quick gap analysis?"
            }
        ],
        "do_not_mention": [f"[MOCK] {item}" for item in do_not_mention],
        "recommended_opening": f"[MOCK] \"Hi {name.split()[0]}, this is [Agent Name] from [Company]. I hope I'm not catching you at a bad time. I noticed you recently showed interest in financial planning, and I thought you might find our {product.get('name', 'new plan')} really relevant to your situation.\""
    }


async def generate_battlecard(customer: dict, product: dict, match_score: int = 70,
                              memory_context: str = "") -> dict:
    if not OPENAI_API_KEY:
        return _mock_battlecard(customer, product, match_score, memory_context)

    events = ", ".join(e["event"] for e in customer.get("life_events", [])) or "None"
    existing = ", ".join(customer.get("existing_policies", [])) or "None"

    user_prompt = f"""
Customer: {customer['name']}, {customer['age']}yo {customer.get('occupation', 'N/A')}, {customer.get('city', 'N/A')}
Income: ₹{customer.get('annual_income', 0):,}/year
Dependents: {customer.get('dependents', 0)}
Life Events: {events}
Existing Policies: {existing}
Product to Pitch: {product['name']} — {product.get('description', '')}
Match Score: {match_score}/100
Rejection/Memory Context: {memory_context or 'None'}
Current Sentiment: {customer.get('sentiment_state', 'neutral')}

Generate the battlecard."""

    try:
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=800
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)
    except Exception as e:
        result = _mock_battlecard(customer, product, match_score, memory_context)
        result["error"] = f"LLM call failed: {str(e)}, using mock"
        return result
