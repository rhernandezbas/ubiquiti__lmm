"""
    Servicio LLM simplificado.
"""

import logging
import os
from openai import AsyncOpenAI
from app_fast_api.services.api_key_service import api_key_service


logger = logging.getLogger(__name__)

class LLMService:
    """
    Servicio LLM simplificado.
    Esta clase solo mantiene la configuración básica del cliente.
    """
    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini"):
        # Si no se proporciona API Key, obtener de variable de entorno
        if not api_key:
            api_key = api_key_service.get_api_key_from_env()
        
        if not api_key:
            raise ValueError("❌ No se encontró API Key de OpenAI. Configura OPENAI_API_KEY.")
        
        # Validar formato de API Key
        if not api_key_service.validate_api_key(api_key):
            raise ValueError("❌ API Key de OpenAI inválida.")
        
        self.api_key = api_key
        self.model = model
        self.client = AsyncOpenAI(api_key=api_key)
        
        # Enmascarar API Key para logs
        masked_key = api_key_service.mask_api_key(api_key)
        logger.info(f"🤖 LLM Service inicializado con API Key: {masked_key}")



    async def analyze(self, data: dict) -> str:
        """
        Analiza cualquier promt enviado
        """

        try:
            client = AsyncOpenAI(api_key=self.api_key)

            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system",
                     "content": "Eres técnico de NOC. Resumen MUY BREVE (2-3 párrafos). Enfócate en problemas detectados y da recomendación clara y directa."},
                    {"role": "user", "content": data.get("prompt")}
                ],
                max_completion_tokens=500
            )

            if response.choices and len(response.choices) > 0:
                summary = response.choices[0].message.content.strip()
                logger.info(f"✅ Análisis LLM generado: {len(summary)} caracteres")
                return summary
            else:
                logger.warning("⚠️ LLM no generó respuesta")
                return "No se pudo generar el análisis"

        except Exception as e:
            logger.error(f"Error generando análisis LLM: {str(e)}")
            return f"Error generando análisis: {str(e)}"

