"""
Rutas para manejar feedback de análisis (con persistencia en BD)
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

from app_fast_api.repositories.feedback_repository import FeedbackRepository
from app_fast_api.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])

# Initialize repository
feedback_repo = FeedbackRepository()


class FeedbackRequest(BaseModel):
    """Modelo para guardar feedback de análisis"""
    analysis_id: Optional[int] = Field(None, description="ID del análisis (opcional)")
    device_ip: str = Field(..., description="IP del dispositivo")
    device_mac: Optional[str] = Field(None, description="MAC del dispositivo (opcional)")
    feedback_type: str = Field(..., description="positivo|negativo|parcial")
    rating: int = Field(ge=1, le=5, description="Rating 1-5 estrellas")
    comments: Optional[str] = Field(None, description="Comentarios adicionales")
    user_name: Optional[str] = Field(None, description="Nombre del usuario")
    user_email: Optional[str] = Field(None, description="Email del usuario (opcional)")


class FeedbackResponse(BaseModel):
    """Respuesta para feedback guardado"""
    success: bool
    message: str
    feedback_id: Optional[int] = None


@router.post("/submit", response_model=FeedbackResponse)
async def submit_feedback(feedback: FeedbackRequest) -> FeedbackResponse:
    """
    Guardar feedback de un análisis en base de datos.

    El feedback se guarda permanentemente y puede ser consultado después.
    """
    try:
        logger.info(f"Guardando feedback para análisis {feedback.analysis_id} - {feedback.feedback_type}")

        # Validate feedback_type
        if feedback.feedback_type not in ['positivo', 'negativo', 'parcial']:
            raise HTTPException(
                status_code=400,
                detail="feedback_type debe ser 'positivo', 'negativo' o 'parcial'"
            )

        # Prepare feedback data (exclude timestamp as it's auto-generated)
        feedback_data = feedback.dict(exclude={'timestamp'} if hasattr(feedback, 'timestamp') else set())

        # Save to database
        saved_feedback = feedback_repo.create_feedback(feedback_data)

        logger.info(
            f"✅ Feedback guardado en BD: {saved_feedback.feedback_type} "
            f"para análisis {saved_feedback.analysis_id} por {saved_feedback.user_name}"
        )

        return FeedbackResponse(
            success=True,
            message="Feedback guardado exitosamente en base de datos",
            feedback_id=saved_feedback.id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error guardando feedback: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error guardando feedback: {str(e)}")


@router.get("/list", response_model=List[Dict[str, Any]])
async def list_feedback(
    limit: int = Query(100, ge=1, le=500, description="Máximo número de registros"),
    offset: int = Query(0, ge=0, description="Número de registros a saltar")
) -> List[Dict[str, Any]]:
    """
    Obtener todos los feedbacks guardados (con paginación).
    """
    try:
        feedbacks = feedback_repo.get_all_feedback(limit=limit, offset=offset)
        return [f.to_dict() for f in feedbacks]
    except Exception as e:
        logger.error(f"Error obteniendo feedbacks: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo feedbacks: {str(e)}")


@router.get("/analysis/{analysis_id}", response_model=List[Dict[str, Any]])
async def get_feedback_by_analysis(analysis_id: int) -> List[Dict[str, Any]]:
    """
    Obtener feedbacks de un análisis específico.
    """
    try:
        feedbacks = feedback_repo.get_feedback_by_analysis(analysis_id)
        return [f.to_dict() for f in feedbacks]
    except Exception as e:
        logger.error(f"Error obteniendo feedbacks del análisis {analysis_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo feedbacks del análisis {analysis_id}: {str(e)}"
        )


@router.get("/device/{device_ip}", response_model=List[Dict[str, Any]])
async def get_feedback_by_device(
    device_ip: str,
    limit: int = Query(50, ge=1, le=200, description="Máximo número de registros")
) -> List[Dict[str, Any]]:
    """
    Obtener todos los feedbacks de un dispositivo específico.
    """
    try:
        feedbacks = feedback_repo.get_feedback_by_device(device_ip, limit=limit)
        return [f.to_dict() for f in feedbacks]
    except Exception as e:
        logger.error(f"Error obteniendo feedbacks del dispositivo {device_ip}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo feedbacks del dispositivo {device_ip}: {str(e)}"
        )


@router.get("/type/{feedback_type}", response_model=List[Dict[str, Any]])
async def get_feedback_by_type(
    feedback_type: str,
    limit: int = Query(100, ge=1, le=500, description="Máximo número de registros")
) -> List[Dict[str, Any]]:
    """
    Obtener feedbacks por tipo (positivo, negativo, parcial).
    """
    try:
        if feedback_type not in ['positivo', 'negativo', 'parcial']:
            raise HTTPException(
                status_code=400,
                detail="feedback_type debe ser 'positivo', 'negativo' o 'parcial'"
            )

        feedbacks = feedback_repo.get_feedback_by_type(feedback_type, limit=limit)
        return [f.to_dict() for f in feedbacks]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo feedbacks tipo {feedback_type}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo feedbacks tipo {feedback_type}: {str(e)}"
        )


@router.get("/stats", response_model=Dict[str, Any])
async def get_feedback_stats() -> Dict[str, Any]:
    """
    Obtener estadísticas de feedbacks.

    Retorna:
    - Total de feedbacks
    - Cantidad por tipo (positivo, negativo, parcial)
    - Rating promedio
    """
    try:
        stats = feedback_repo.get_feedback_stats()
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo estadísticas: {str(e)}")


@router.delete("/{feedback_id}", response_model=Dict[str, Any])
async def delete_feedback(feedback_id: int) -> Dict[str, Any]:
    """
    Eliminar un feedback por ID.
    """
    try:
        deleted = feedback_repo.delete_feedback(feedback_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Feedback {feedback_id} no encontrado")

        return {
            "success": True,
            "message": f"Feedback {feedback_id} eliminado exitosamente"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando feedback {feedback_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error eliminando feedback: {str(e)}")
