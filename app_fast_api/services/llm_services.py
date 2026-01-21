"""
    Servicio LLM simplificado.
"""

import logging
from openai import AsyncOpenAI


logger = logging.getLogger(__name__)

class LLMService:
    """
    Servicio LLM simplificado.
    Esta clase solo mantiene la configuración básica del cliente.
    """
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model
        self.client = AsyncOpenAI(api_key=api_key)



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

