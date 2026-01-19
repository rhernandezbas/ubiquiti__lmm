"""
Endpoints para consultar logs de la aplicación
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, Literal
from pathlib import Path
import os

router = APIRouter()

LOG_DIR = Path("/app/logs")
LOG_FILES = {
    "app": "app.log",
    "error": "error.log"
}


@router.get("/logs")
async def get_logs(
    log_type: Literal["app", "error"] = Query(
        default="app",
        description="Tipo de log a consultar: 'app' para logs generales, 'error' para logs de errores"
    ),
    lines: int = Query(
        default=100,
        ge=1,
        le=10000,
        description="Número de líneas a retornar (últimas N líneas del archivo)"
    ),
    search: Optional[str] = Query(
        default=None,
        description="Texto a buscar en los logs (case-insensitive)"
    )
):
    """
    Obtiene los logs de la aplicación.
    
    Args:
        log_type: Tipo de log ('app' o 'error')
        lines: Número de líneas a retornar (últimas N líneas)
        search: Texto opcional para filtrar logs
    
    Returns:
        Dict con información de los logs
    
    Examples:
        - GET /api/v1/logs?log_type=app&lines=50
        - GET /api/v1/logs?log_type=error&lines=100
        - GET /api/v1/logs?log_type=app&lines=200&search=ERROR
    """
    try:
        # Obtener ruta del archivo de log
        log_filename = LOG_FILES.get(log_type)
        if not log_filename:
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de log inválido: {log_type}. Use 'app' o 'error'"
            )
        
        log_path = LOG_DIR / log_filename
        
        # Verificar que el archivo existe
        if not log_path.exists():
            return {
                "success": True,
                "log_type": log_type,
                "log_file": log_filename,
                "lines_requested": lines,
                "lines_returned": 0,
                "total_size_bytes": 0,
                "logs": [],
                "message": f"Archivo de log {log_filename} no existe aún"
            }
        
        # Obtener tamaño del archivo
        file_size = log_path.stat().st_size
        
        # Leer el archivo
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
        
        # Obtener las últimas N líneas
        log_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        # Filtrar por búsqueda si se proporciona
        if search:
            search_lower = search.lower()
            log_lines = [
                line for line in log_lines
                if search_lower in line.lower()
            ]
        
        # Limpiar líneas (remover saltos de línea extra)
        log_lines = [line.rstrip('\n') for line in log_lines]
        
        return {
            "success": True,
            "log_type": log_type,
            "log_file": log_filename,
            "log_path": str(log_path),
            "lines_requested": lines,
            "lines_returned": len(log_lines),
            "total_lines_in_file": len(all_lines),
            "total_size_bytes": file_size,
            "total_size_mb": round(file_size / (1024 * 1024), 2),
            "search_filter": search,
            "logs": log_lines
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al leer logs: {str(e)}"
        )


@router.get("/logs/stats")
async def get_logs_stats():
    """
    Obtiene estadísticas de los archivos de logs.
    
    Returns:
        Dict con estadísticas de cada archivo de log
    """
    try:
        stats = {}
        
        for log_type, log_filename in LOG_FILES.items():
            log_path = LOG_DIR / log_filename
            
            if log_path.exists():
                file_size = log_path.stat().st_size
                
                # Contar líneas
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    line_count = sum(1 for _ in f)
                
                # Obtener fecha de última modificación
                mtime = log_path.stat().st_mtime
                
                stats[log_type] = {
                    "filename": log_filename,
                    "path": str(log_path),
                    "exists": True,
                    "size_bytes": file_size,
                    "size_mb": round(file_size / (1024 * 1024), 2),
                    "total_lines": line_count,
                    "last_modified": mtime
                }
            else:
                stats[log_type] = {
                    "filename": log_filename,
                    "path": str(log_path),
                    "exists": False,
                    "size_bytes": 0,
                    "size_mb": 0,
                    "total_lines": 0,
                    "last_modified": None
                }
        
        return {
            "success": True,
            "log_directory": str(LOG_DIR),
            "stats": stats
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener estadísticas de logs: {str(e)}"
        )


@router.delete("/logs")
async def clear_logs(
    log_type: Literal["app", "error", "all"] = Query(
        default="all",
        description="Tipo de log a limpiar: 'app', 'error' o 'all'"
    )
):
    """
    Limpia (vacía) los archivos de logs.
    
    Args:
        log_type: Tipo de log a limpiar ('app', 'error' o 'all')
    
    Returns:
        Dict con resultado de la operación
    
    Warning:
        Esta operación es irreversible. Los logs se eliminarán permanentemente.
    """
    try:
        cleared = []
        
        if log_type == "all":
            files_to_clear = LOG_FILES.items()
        else:
            if log_type not in LOG_FILES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Tipo de log inválido: {log_type}"
                )
            files_to_clear = [(log_type, LOG_FILES[log_type])]
        
        for ltype, filename in files_to_clear:
            log_path = LOG_DIR / filename
            
            if log_path.exists():
                # Vaciar el archivo (no eliminarlo, solo vaciarlo)
                with open(log_path, 'w') as f:
                    f.write("")
                
                cleared.append({
                    "log_type": ltype,
                    "filename": filename,
                    "cleared": True
                })
            else:
                cleared.append({
                    "log_type": ltype,
                    "filename": filename,
                    "cleared": False,
                    "reason": "File does not exist"
                })
        
        return {
            "success": True,
            "message": f"Logs limpiados: {log_type}",
            "cleared": cleared
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al limpiar logs: {str(e)}"
        )
