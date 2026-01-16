from __future__ import annotations

from typing import Any, Dict

from config.settings import settings


def get_scoring_config() -> Dict[str, Any]:
    """
    ADK tool: return the scoring weights and tier thresholds from config.settings.
    This prevents hardcoding these values in the prompt.
    """
    return {
        "weights": {
            "sales_growth": settings.SALES_GROWTH_WEIGHT,
            "inventory_update_count": settings.INVENTORY_FREQ_WEIGHT,
            "applications_count": settings.APPLICATIONS_WEIGHT,
            "leads_count": settings.LEADS_WEIGHT,
        },
        "tiers": settings.DEALER_TIERS,
        "model_default": settings.DEFAULT_MODEL,
        "notes": "overall_score is computed from normalized metric scores (0 to 100) within the selected slice (country filter and optional date range).",
    }
