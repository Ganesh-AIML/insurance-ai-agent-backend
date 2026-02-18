"""LLM-powered marketing message generator."""

import os
import json
from openai import AsyncOpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

SYSTEM_PROMPT = """You are an expert insurance marketing copywriter for an Indian insurance company.
Generate a personalized marketing message for the given customer and product.

RULES:
- Be warm, personal, and trustworthy — never salesy or pushy
- Reference the customer's specific life situation naturally
- Include 1-2 specific product benefits relevant to their situation
- Include a soft CTA (call to action)
- Adapt tone and length to the channel:
  - SMS: Max 160 characters, punchy, include short link placeholder [LINK]
  - Email: 150-200 words, professional, include subject line
  - WhatsApp: 50-80 words, conversational, use 1-2 emojis naturally
  - App Push: Max 100 characters, urgent/compelling
- If mode is "empathy": Do NOT sell. Instead, acknowledge their situation and offer support/help resources.
- Use Indian context (₹ currency, Indian names, Indian life situations)

Return JSON only, no markdown:
{
  "subject": "email subject line (only for email channel, null for others)",
  "message_body": "the message text",
  "cta": "call to action text"
}"""


def _mock_messages(customer: dict, product: dict, mode: str) -> dict:
    name = customer.get("name", "Customer").split()[0]
    product_name = product.get("name", "Insurance Plan")

    if mode == "empathy":
        return {
            "sms": {"subject": None, "message_body": f"[MOCK] Hi {name}, we noticed you had a concern. Your satisfaction matters to us. Reply HELP for support. [LINK]", "cta": "Reply HELP", "channel": "sms", "mode": "empathy"},
            "email": {"subject": f"We're here for you, {name}", "message_body": f"[MOCK] Dear {name},\n\nWe understand you've had a recent concern with our services. We want you to know that your experience matters deeply to us.\n\nOur dedicated support team is ready to assist you personally. Please don't hesitate to reach out — we're committed to resolving any issues and ensuring you feel valued as our customer.\n\nWarm regards,\nYour Insurance Partner", "cta": "Contact Our Support Team", "channel": "email", "mode": "empathy"},
            "whatsapp": {"subject": None, "message_body": f"[MOCK] Hi {name} 🙏\n\nWe noticed you had a concern recently. We're sorry about that. Our team is here to help — just reply to this message and we'll connect you with a dedicated support person.", "cta": "Reply to connect", "channel": "whatsapp", "mode": "empathy"},
            "app_push": {"subject": None, "message_body": f"[MOCK] {name}, we're here to help. Tap to reach our support team.", "cta": "Get Support", "channel": "app_push", "mode": "empathy"}
        }

    events = [e["event"] for e in customer.get("life_events", [])]
    event_str = events[0].replace("_", " ") if events else "your future plans"

    return {
        "sms": {"subject": None, "message_body": f"[MOCK] Hi {name}! Secure your family with {product_name}. Starting ₹{product.get('premium_range', '500/month').split('-')[0]}/month. Know more: [LINK]", "cta": "Know more", "channel": "sms", "mode": "sales"},
        "email": {"subject": f"{name}, a smart move for your {event_str}", "message_body": f"[MOCK] Dear {name},\n\nCongratulations on your {event_str}! As you embrace this exciting new chapter, it's the perfect time to think about securing your family's future.\n\n{product_name} offers you:\n• {product.get('benefits', ['Comprehensive coverage'])[0]}\n• {product.get('benefits', ['', 'Tax benefits'])[1] if len(product.get('benefits', [])) > 1 else 'Flexible premium options'}\n\nStarting at just {product.get('premium_range', '₹500/month')}, it's an affordable way to ensure peace of mind.\n\nWould you like to learn more? Our advisor can walk you through a personalized plan.\n\nWarm regards,\nYour Insurance Partner", "cta": "Schedule a Free Consultation", "channel": "email", "mode": "sales"},
        "whatsapp": {"subject": None, "message_body": f"[MOCK] Hi {name}! 👋\n\nWith your {event_str}, now's a great time to consider {product_name}. It starts at just {product.get('premium_range', '₹500/month')} and gives you peace of mind 🛡️\n\nWant me to share more details?", "cta": "Yes, tell me more", "channel": "whatsapp", "mode": "sales"},
        "app_push": {"subject": None, "message_body": f"[MOCK] {name}, protect your family with {product_name} — from {product.get('premium_range', '₹500/month')}!", "cta": "View Plan", "channel": "app_push", "mode": "sales"}
    }


async def generate_message(customer: dict, product: dict, channel: str, mode: str = "sales",
                           memory_context: str = "", feature_importance: dict = None) -> dict:
    if not OPENAI_API_KEY:
        mock = _mock_messages(customer, product, mode)
        return mock.get(channel, mock["email"])

    life_events = ", ".join(e["event"] for e in customer.get("life_events", [])) or "None detected"
    importance_str = json.dumps(feature_importance or {})

    user_prompt = f"""
Customer: {customer['name']}, {customer['age']}yo, {customer.get('occupation', 'N/A')}, {customer.get('city', 'N/A')}
Life Events: {life_events}
Recommended Product: {product['name']} — {product.get('description', '')}
Key Reasons (from AI): {importance_str}
Channel: {channel}
Mode: {mode}
Rejection History: {memory_context or 'None'}

Generate the marketing message for the {channel} channel."""

    try:
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        result = json.loads(content)
        result["channel"] = channel
        result["mode"] = mode
        return result
    except Exception as e:
        mock = _mock_messages(customer, product, mode)
        result = mock.get(channel, mock["email"])
        result["error"] = f"LLM call failed: {str(e)}, using mock"
        return result


async def generate_all_messages(customer: dict, product: dict, mode: str = "sales",
                                memory_context: str = "", feature_importance: dict = None) -> dict:
    if not OPENAI_API_KEY:
        return _mock_messages(customer, product, mode)

    channels = ["sms", "email", "whatsapp", "app_push"]
    results = {}
    for ch in channels:
        results[ch] = await generate_message(customer, product, ch, mode, memory_context, feature_importance)
    return results
