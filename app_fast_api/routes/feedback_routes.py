"""
Rutas para manejar feedback de análisis y logs de la aplicación
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])

# Almacenamiento temporal de feedback (en producción usar BD)
feedback_storage = []
application_logs = []

class FeedbackRequest(BaseModel):
    """Modelo para guardar feedback de análisis"""
    analysis_id: Optional[int] = Field(None, description="ID del análisis")
    device_ip: str = Field(..., description="IP del dispositivo")
    feedback_type: str = Field(..., description="positivo|negativo|parcial")
    rating: int = Field(ge=1, le=5, description="Rating 1-5")
    comments: Optional[str] = Field(None, description="Comentarios adicionales")
    timestamp: datetime = Field(default_factory=datetime.now)
    user_name: Optional[str] = Field(None, description="Nombre del usuario")

class FeedbackResponse(BaseModel):
    """Respuesta para feedback guardado"""
    success: bool
    message: str
    feedback_id: Optional[int] = None

@router.post("/submit", response_model=FeedbackResponse)
async def submit_feedback(feedback: FeedbackRequest) -> FeedbackResponse:
    """
    Guardar feedback de un análisis
    """
    try:
        logger.info(f"Guardando feedback para análisis {feedback.analysis_id} - {feedback.feedback_type}")
        
        # Guardar feedback en almacenamiento temporal
        feedback_data = feedback.dict()
        feedback_data["id"] = len(feedback_storage) + 1
        feedback_storage.append(feedback_data)
        
        logger.info(f"Feedback guardado: {feedback.feedback_type} para análisis {feedback.analysis_id} por {feedback.user_name}")
        
        return FeedbackResponse(
            success=True,
            message="Feedback guardado exitosamente",
            feedback_id=feedback_data["id"]
        )
        
    except Exception as e:
        logger.error(f"Error guardando feedback: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error guardando feedback: {str(e)}")

@router.get("/list", response_model=List[Dict[str, Any]])
async def list_feedback() -> List[Dict[str, Any]]:
    """
    Obtener todos los feedbacks guardados
    """
    try:
        return feedback_storage
    except Exception as e:
        logger.error(f"Error obteniendo feedbacks: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo feedbacks: {str(e)}")

@router.get("/analysis/{analysis_id}/feedback", response_model=List[Dict[str, Any]])
async def get_feedback_by_analysis(analysis_id: int) -> List[Dict[str, Any]]:
    """
    Obtener feedbacks de un análisis específico
    """
    try:
        analysis_feedbacks = [f for f in feedback_storage if f.get("analysis_id") == analysis_id]
        return analysis_feedbacks
    except Exception as e:
        logger.error(f"Error obteniendo feedbacks del análisis {analysis_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo feedbacks del análisis {analysis_id}: {str(e)}")
