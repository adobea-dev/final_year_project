# agents/dealer_copilot/recommendation_agent.py
from __future__ import annotations

from typing import Any, Dict, Optional, List

from .scoring_agent import score_dealers


def recommend_dealer_actions(
    country: Optional[str] = None,
    top_n: int = 5,
) -> Dict[str, Any]:
    """
    Generate practical recommendations for dealer management.

    Uses score_dealers to get scores, then groups dealers into:
    - top performers
    - at risk dealers
    - mid tier growth opportunities
    """
    scoring_result = score_dealers(
        country=country,
        period_start_date=None,
        period_end_date=None,
        top_n=top_n,
    )

    scores: List[Dict[str, Any]] = scoring_result.get("scores", [])
    if not scores:
        return {
            "summary": "No scores were available so no recommendations were generated.",
            "details": scoring_result,
        }

    sorted_scores = sorted(scores, key=lambda r: r.get("overall_score", 0), reverse=True)

    top = sorted_scores[:top_n]
    bottom = sorted_scores[-top_n:] if len(sorted_scores) >= top_n else sorted_scores
    middle = sorted_scores[top_n:-top_n] if len(sorted_scores) > 2 * top_n else []

    output: Dict[str, Any] = {
        "summary": f"Generated recommendations for {len(sorted_scores)} dealers.",
        "top_performers": [],
        "at_risk_dealers": [],
        "growth_opportunities": [],
    }

    for row in top:
        output["top_performers"].append(
            {
                "dealer_id": row.get("dealer_id"),
                "dealership_name": row.get("dealership_name"),
                "country": row.get("country"),
                "tier": row.get("tier"),
                "overall_score": row.get("overall_score"),
                "message": (
                    "Maintain close relationship and explore upsell or cross sell opportunities. "
                    "This dealer already shows strong activity across listings, leads, applications and sales."
                ),
            }
        )

    for row in bottom:
        output["at_risk_dealers"].append(
            {
                "dealer_id": row.get("dealer_id"),
                "dealership_name": row.get("dealership_name"),
                "country": row.get("country"),
                "tier": row.get("tier"),
                "overall_score": row.get("overall_score"),
                "message": (
                    "Engage this dealer with targeted support. Check for blocked inventory, weak lead follow up, "
                    "or financing issues and plan an action with the local account manager."
                ),
            }
        )

    for row in middle:
        output["growth_opportunities"].append(
            {
                "dealer_id": row.get("dealer_id"),
                "dealership_name": row.get("dealership_name"),
                "country": row.get("country"),
                "tier": row.get("tier"),
                "overall_score": row.get("overall_score"),
                "message": (
                    "This dealer is mid tier. Focus on small improvements in listing freshness and loan application "
                    "conversion to move them into a higher tier."
                ),
            }
        )

    return output


# ADK tool wrapper
def recommend_dealer_actions_tool(
    country: Optional[str] = None,
    top_n: int = 5,
) -> Dict[str, Any]:
    return recommend_dealer_actions(country=country, top_n=top_n)
