"""SHAP-style explainability engine - generates feature importance breakdowns."""


def generate_explainability(recommendation: dict, customer: dict) -> dict:
    feature_importance = recommendation.get("feature_importance", {})

    # Normalize to percentages
    total = sum(feature_importance.values()) if feature_importance else 1
    normalized = {k: round((v / total) * 100, 1) for k, v in feature_importance.items()}

    # Sort by importance
    sorted_features = sorted(normalized.items(), key=lambda x: x[1], reverse=True)

    # Build visual-friendly data
    chart_data = [
        {"feature": name, "importance": pct, "raw_score": feature_importance.get(name, 0)}
        for name, pct in sorted_features
    ]

    # Categorize factors
    positive_factors = [f for f in chart_data if f["raw_score"] > 0]
    negative_factors = [f for f in chart_data if f["raw_score"] < 0]

    return {
        "product_id": recommendation.get("product_id"),
        "match_score": recommendation.get("match_score", 0),
        "chart_data": chart_data,
        "positive_factors": positive_factors,
        "negative_factors": negative_factors,
        "top_driver": sorted_features[0][0] if sorted_features else "N/A",
        "explanation": recommendation.get("explanation_summary", ""),
        "confidence": min(recommendation.get("match_score", 0) / 100, 1.0)
    }
