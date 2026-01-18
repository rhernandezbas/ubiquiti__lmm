import logging
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

class LLMService:
    """
    Servicio LLM simplificado.
    El análisis LLM se hace directamente en unified_analysis.py
    Esta clase solo mantiene la configuración básica del cliente.
    """
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model
        self.client = AsyncOpenAI(api_key=api_key)
