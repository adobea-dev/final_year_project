# config/models_config.py
from __future__ import annotations

from google.adk.models.lite_llm import LiteLlm
from config.settings import settings


class ModelConfig:
    """
    Configuration for all LLM, vector DB, and embedding parameters.
    """

    @staticmethod
    def get_ollama_model() -> LiteLlm:
        return LiteLlm(model=f"ollama/{settings.DEFAULT_MODEL}")


model_config = ModelConfig()
