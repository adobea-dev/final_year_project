from dotenv import load_dotenv
import os

# Load environment variables from .env file at project root
load_dotenv()


class Settings:
    """
    Global configuration for the Autochek Agentic System.
    Central place to update scoring logic, category thresholds and core infra settings.
    """

    # === Dealer Scoring Weights ===
    SALES_GROWTH_WEIGHT = 0.40
    INVENTORY_FREQ_WEIGHT = 0.25
    APPLICATIONS_WEIGHT = 0.25
    LEADS_WEIGHT = 0.10

    # === Dealer Tier Thresholds ===
    DEALER_TIERS = {
        "Bronze": (0, 40.999999),
        "Silver": (41.0, 60.999999),
        "Gold": (61.0, 80.999999),
        "Platinum": (81.0, 100.0),
    }

    # === LLM Default Model ===
   # DEFAULT_MODEL = "tinyllama"
   # DEFAULT_MODEL = "qwen2.5:7b-instruct"
# or
    DEFAULT_MODEL = "llama3.1:8b"


    # === Database settings (from environment) ===
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB = os.getenv("POSTGRES_DB", "dealer_ai")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "changeme")


settings = Settings()
