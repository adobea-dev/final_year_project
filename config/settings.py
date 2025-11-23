class Settings:
    """
    Global configuration for the Autochek Agentic System.
    Central place to update scoring logic and category thresholds.
    """

    # === Dealer Scoring Weights ===
    SALES_GROWTH_WEIGHT = 0.40
    INVENTORY_FREQ_WEIGHT = 0.25
    APPLICATIONS_WEIGHT = 0.25
    LEADS_WEIGHT = 0.10

    # === Dealer Tier Thresholds ===
    DEALER_TIERS = {
        "Bronze": (0, 40),
        "Silver": (41, 60),
        "Gold": (61, 80),
        "Platinum": (81, 100),
    }

    # === LLM Default Model ===
    
    DEFAULT_MODEL = "tinyllama"  

settings = Settings()