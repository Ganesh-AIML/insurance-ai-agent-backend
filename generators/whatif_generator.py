"""What-If scenario projection generator - LLM-powered with mock fallback."""

import os
import json
from openai import AsyncOpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

SYSTEM_PROMPT = """You are a financial advisor AI. Generate a "What-If" scenario projection for an insurance/investment product.
Return JSON only, no markdown:
{
  "narrative": "A 2-3 sentence personalized story about the customer's future",
  "projection_data": [{"year": 2026, "with_policy": 100000, "without_policy": 0}, ...],
  "key_insight": "One compelling takeaway sentence"
}
Generate 10-15 years of projection data.
Use realistic Indian financial figures (₹). Consider inflation at 6% and policy returns based on the product type.
For term life: show death benefit protection vs no coverage gap.
For health: show cumulative medical expense coverage vs out-of-pocket.
For investment/child: show corpus growth with and without systematic investment.
For motor/property: show asset protection value vs replacement cost risk."""


def _mock_projection(customer: dict, product: dict) -> dict:
    age = customer.get("age", 30)
    income = customer.get("annual_income", 500000)
    name = customer.get("name", "Customer").split()[0]
    product_cat = product.get("category", "life")
    dependents = customer.get("dependents", 0)

    base_year = 2026
    data = []

    if product_cat == "life":
        cover = product.get("min_cover", 5000000)
        for i in range(15):
            year = base_year + i
            with_policy = cover
            without_policy = max(0, income * (15 - i) * 0.3)
            data.append({"year": year, "with_policy": int(with_policy), "without_policy": int(without_policy)})
        narrative = f"[MOCK] If the unexpected happens, {name}'s family of {dependents + 1} would receive ₹{cover/100000:.0f}L immediately — enough to maintain their lifestyle for 15+ years. Without coverage, the family would face a growing financial gap."
        insight = f"[MOCK] A ₹{cover/100000:.0f}L term plan costs less than 1% of {name}'s income but protects 100% of the family's future."

    elif product_cat == "health":
        for i in range(12):
            year = base_year + i
            medical_costs = int(100000 * (1.10 ** i))
            with_policy = min(medical_costs, product.get("min_cover", 1000000))
            without_policy = medical_costs
            data.append({"year": year, "with_policy": int(with_policy), "without_policy": int(without_policy)})
        narrative = f"[MOCK] Medical inflation in India runs at 10-14% annually. By {base_year + 10}, {name}'s family could face medical bills of ₹2.5L+ for a single hospitalization. A family floater ensures zero out-of-pocket stress."
        insight = f"[MOCK] Today's ₹1L hospital bill will cost ₹2.6L in 10 years. Health insurance is not optional — it's essential."

    elif product_cat == "investment":
        monthly_premium = 5000
        for i in range(15):
            year = base_year + i
            with_policy = int(monthly_premium * 12 * i * 1.08)
            without_policy = int(monthly_premium * 12 * i * 1.04)
            data.append({"year": year, "with_policy": int(with_policy), "without_policy": int(without_policy)})
        narrative = f"[MOCK] Starting a ₹5,000/month child education plan now, {name} could build a corpus of ₹15L+ by the time their child reaches college — enough for a top-tier education in India."
        insight = f"[MOCK] Starting 5 years late could mean ₹4-5L less in the education corpus. Time is the biggest factor."

    else:
        for i in range(10):
            year = base_year + i
            asset_value = int(500000 * (1.05 ** i))
            with_policy = asset_value
            without_policy = max(0, asset_value - int(200000 * (1 + i * 0.1)))
            data.append({"year": year, "with_policy": int(with_policy), "without_policy": int(without_policy)})
        narrative = f"[MOCK] {name}'s assets appreciate over time, but so do the risks. Comprehensive coverage ensures the full value is protected against unforeseen events."
        insight = f"[MOCK] The cost of not insuring is always higher than the premium — one event can wipe out years of savings."

    return {
        "narrative": narrative,
        "projection_data": data,
        "key_insight": insight
    }


async def generate_whatif(customer: dict, product: dict) -> dict:
    if not OPENAI_API_KEY:
        return _mock_projection(customer, product)

    life_events = ", ".join(e["event"] for e in customer.get("life_events", [])) or "None"
    goals = []
    for e in customer.get("life_events", []):
        ev = e["event"]
        if "child" in ev:
            goals.append("child's education")
        elif "marriage" in ev or "engagement" in ev:
            goals.append("family protection")
        elif "retirement" in ev:
            goals.append("retirement corpus")
        elif "home" in ev:
            goals.append("home protection")
    goal = goals[0] if goals else "financial security"

    user_prompt = f"""
Customer: {customer['name']}, age {customer['age']}, income ₹{customer.get('annual_income', 500000):,}/year, {customer.get('dependents', 0)} dependents
Product: {product['name']} ({product.get('category', 'general')})
Monthly Premium: ₹{product.get('premium_range', '1000-5000/month')}
Goal: {goal}

Generate the What-If projection."""

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
        result = _mock_projection(customer, product)
        result["error"] = f"LLM call failed: {str(e)}, using mock"
        return result
