"""
Rutas para ver logs de la aplicación
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

router = APIRouter(prefix="/api/v1/logs", tags=["logs"])

# Configurar logging para capturar logs de la aplicación
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

# Capturar logs en una lista para la API
logs_storage = []

class LogEntry(BaseModel):
    """Modelo para entrada de log"""
    timestamp: datetime = Field(default_factory=datetime.now)
    level: str = Field(..., description="Nivel del log (INFO, ERROR, WARNING)")
    logger_name: str = Field(..., description="Nombre del logger")
    message: str = Field(..., description="Mensaje del log")
    module: str = Field(..., description="Módulo que generó el log")
    function_name: Optional[str] = Field(None, description="Nombre de la función")

class LogsResponse(BaseModel):
    """Respuesta para logs"""
    logs: List[LogEntry]
    total_count: int
    message: str

class LogFilter(BaseModel):
    """Filtros para consultar logs"""
    level: Optional[str] = Field(None, description="Filtrar por nivel (INFO, ERROR, WARNING)")
    logger_name: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = Field(100, description="Límite de logs a retornar")

class LogHandler(logging.Handler):
    """Handler personalizado para capturar logs en la API"""
    def emit(self, record):
        # Guardar logs en almacenamiento temporal
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created),
            "level": record.levelname,
            "logger_name": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function_name": getattr(record, "funcName", None)
        }
        logs_storage.append(log_entry)
        
        # No necesitamos pasar al handler original, solo guardamos en memoria

# Configurar el handler personalizado
logging.getLogger().addHandler(LogHandler())

@router.get("/", response_model=LogsResponse)
async def get_logs(filter: LogFilter = LogFilter()) -> LogsResponse:
    """
    Obtener logs de la aplicación con filtros opcionales
    """
    try:
        # Filtrar logs según los criterios
        filtered_logs = []
        
        for log in logs_storage:
            # Filtrar por nivel
            if filter.level and log["level"] != filter.level:
                continue
            
            # Filtrar por logger name
            if filter.logger_name and filter.logger_name not in log["logger_name"]:
                continue
            
            # Filtrar por tiempo
            if filter.start_time and log["timestamp"] < filter.start_time:
                continue
            
            if filter.end_time and log["timestamp"] > filter.end_time:
                continue
            
            filtered_logs.append(log)
        
        # Aplicar límite
        if filter.limit > 0:
            filtered_logs = filtered_logs[-filter.limit:]
        
        return LogsResponse(
            logs=filtered_logs,
            total_count=len(logs_storage),
            message=f"Obtenidos {len(filtered_logs)} logs de {len(logs_storage)} totales"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo logs: {str(e)}")

@router.get("/recent", response_model=LogsResponse)
async def get_recent_logs(limit: int = 50) -> LogsResponse:
    """
    Obtener logs recientes
    """
    try:
        # Obtener los logs más recientes
        recent_logs = logs_storage[-limit:] if len(logs_storage) > limit else logs_storage
        
        return LogsResponse(
            logs=recent_logs,
            total_count=len(logs_storage),
            message=f"Últimos {len(recent_logs)} logs de {len(logs_storage)} totales"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo logs recientes: {str(e)}")

@router.get("/search", response_model=LogsResponse)
async def search_logs(query: str, limit: int = 100) -> LogsResponse:
    """
    Buscar logs por texto
    """
    try:
        # Buscar logs que contengan el query
        search_results = []
        
        for log in logs_storage:
            if query.lower() in log["message"].lower():
                search_results.append(log)
        
        # Aplicar límite
        if limit > 0:
            search_results = search_results[:limit]
        
        return LogsResponse(
            logs=search_results,
            total_count=len(search_results),
            message=f"Encontrados {len(search_results)} logs con '{query}' de {len(logs_storage)} totales"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error buscando logs: {str(e)}")

@router.delete("/clear", response_model=Dict[str, str])
async def clear_logs() -> Dict[str, str]:
    """
    Limpiar todos los logs almacenados
    """
    try:
        global logs_storage
        logs_storage.clear()
        
        return {"message": "Logs limpiados exitosamente"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error limpiando logs: {str(e)}")
