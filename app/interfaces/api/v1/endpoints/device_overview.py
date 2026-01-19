"""
Endpoint para obtener el overview completo del dispositivo desde UISP
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, List
from app.infrastructure.api.uisp_client import UISPClient
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["device-overview"])


async def get_uisp_client() -> UISPClient:
    """Obtener cliente UISP configurado"""
    return UISPClient(
        base_url=settings.UISP_BASE_URL,
        token=settings.UISP_TOKEN
    )


@router.get("/search-devices")
async def search_devices(
    query: str = Query(..., description="Buscar por IP, nombre o MAC")
) -> List[Dict[str, Any]]:
    """
    Busca dispositivos en UISP por IP, nombre o MAC
    
    Args:
        query: Término de búsqueda (IP, nombre o MAC parcial)
        
    Returns:
        Lista de dispositivos que coinciden con la búsqueda
    """
    try:
        # Inicializar cliente UISP
        uisp_client = await get_uisp_client()
        
        # Obtener todos los dispositivos
        devices = await uisp_client.get_devices()
        
        # Buscar coincidencias
        results = []
        query_lower = query.lower()
        
        for device in devices:
            identification = device.get("identification", {})
            ip_address = device.get("ipAddress", "")
            name = identification.get("name", "")
            mac = identification.get("mac", "")
            
            # Buscar en IP, nombre o MAC
            if (query_lower in ip_address.lower() or 
                query_lower in name.lower() or 
                query_lower in mac.lower()):
                
                results.append({
                    "device_id": identification.get("id"),
                    "name": name,
                    "ip_address": ip_address,
                    "mac_address": mac,
                    "model": identification.get("model"),
                    "status": device.get("status")
                })
        
        return results
        
    except Exception as e:
        logger.error(f"Error buscando dispositivos: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error buscando dispositivos: {str(e)}")


@router.get("/debug-device-overview")
async def get_device_overview(
    ip_address: str = Query(..., description="IP del dispositivo a consultar")
) -> Dict[str, Any]:
    """
    Obtiene el overview completo del dispositivo desde UISP API
    
    Args:
        ip_address: IP del dispositivo
        
    Returns:
        Overview completo con todas las métricas del dispositivo
    """
    try:
        # Inicializar cliente UISP
        uisp_client = await get_uisp_client()
        
        # Buscar dispositivo por IP
        devices = await uisp_client.get_devices()
        device_data = None
        
        for device in devices:
            if device.get("ipAddress") == ip_address:
                device_data = device
                break
        
        if not device_data:
            raise HTTPException(status_code=404, detail=f"Dispositivo {ip_address} no encontrado en UISP")
        
        # Extraer información del dispositivo
        identification = device_data.get("identification", {})
        overview = device_data.get("overview", {})
        
        # Obtener todas las keys del overview
        overview_keys = list(overview.keys()) if overview else []
        
        return {
            "device_name": identification.get("name"),
            "device_id": identification.get("id"),
            "ip_address": device_data.get("ipAddress"),
            "model": identification.get("model"),
            "mac_address": identification.get("mac"),
            "status": device_data.get("status"),
            "overview_keys": overview_keys,
            "overview_full": overview,
            "identification": identification
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo overview del dispositivo {ip_address}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo overview: {str(e)}")


@router.get("/debug-device-overview/{device_id}")
async def get_device_overview_by_id(
    device_id: str
) -> Dict[str, Any]:
    """
    Obtiene el overview completo del dispositivo desde UISP API por ID
    
    Args:
        device_id: ID del dispositivo en UISP
        
    Returns:
        Overview completo con todas las métricas del dispositivo
    """
    try:
        # Inicializar cliente UISP
        uisp_client = await get_uisp_client()
        
        # Obtener dispositivo por ID
        device_data = await uisp_client.get_device(device_id)
        
        if not device_data:
            raise HTTPException(status_code=404, detail=f"Dispositivo {device_id} no encontrado en UISP")
        
        # Extraer información del dispositivo
        identification = device_data.get("identification", {})
        overview = device_data.get("overview", {})
        
        # Obtener todas las keys del overview
        overview_keys = list(overview.keys()) if overview else []
        
        return {
            "device_name": identification.get("name"),
            "device_id": identification.get("id"),
            "ip_address": device_data.get("ipAddress"),
            "model": identification.get("model"),
            "mac_address": identification.get("mac"),
            "status": device_data.get("status"),
            "overview_keys": overview_keys,
            "overview_full": overview,
            "identification": identification
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo overview del dispositivo {device_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo overview: {str(e)}")
