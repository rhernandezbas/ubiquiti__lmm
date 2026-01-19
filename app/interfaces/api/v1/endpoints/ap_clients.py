"""
Endpoint para obtener información completa del AP y sus clientes
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, List, Optional
from app.infrastructure.ssh.ubiquiti_ssh_client import UbiquitiSSHClient
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ap-clients"])


async def get_ssh_client() -> UbiquitiSSHClient:
    """Obtener cliente SSH configurado"""
    return UbiquitiSSHClient()


@router.get("/ap-info-with-clients")
async def get_ap_info_with_clients(
    ip_address: str = Query(..., description="IP del dispositivo a consultar"),
    ssh_username: Optional[str] = Query(None, description="Usuario SSH (opcional)"),
    ssh_password: Optional[str] = Query(None, description="Contraseña SSH (opcional)")
) -> Dict[str, Any]:
    """
    Obtiene información completa del AP actual y sus clientes conectados
    
    Args:
        ip_address: IP del dispositivo
        ssh_username: Usuario SSH (opcional, usa default del config)
        ssh_password: Contraseña SSH (opcional, usa default del config)
        
    Returns:
        Información completa del AP y lista de clientes conectados
    """
    try:
        # Inicializar cliente SSH
        ssh_client = await get_ssh_client()
        
        # Obtener información del AP actual
        ap_info = await ssh_client.get_current_ap_info(
            host=ip_address,
            username=ssh_username,
            password=ssh_password
        )
        
        # Obtener clientes conectados
        clients_info = await ssh_client.get_ap_clients(
            host=ip_address,
            username=ssh_username,
            password=ssh_password
        )
        
        # Combinar información
        result = {
            "device_ip": ip_address,
            "ap_info": ap_info,
            "clients_info": clients_info,
            "total_clients": clients_info.get("clients_count", 0),
            "success": ap_info.get("success", False) and clients_info.get("success", False)
        }
        
        if not result["success"]:
            result["error"] = "No se pudo obtener toda la información"
            if not ap_info.get("success"):
                result["ap_error"] = ap_info.get("error", "Error desconocido")
            if not clients_info.get("success"):
                result["clients_error"] = clients_info.get("error", "Error desconocido")
        
        return result
        
    except Exception as e:
        logger.error(f"Error obteniendo información del AP y clientes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo información: {str(e)}")


@router.get("/ap-clients-only")
async def get_ap_clients_only(
    ip_address: str = Query(..., description="IP del dispositivo a consultar"),
    ssh_username: Optional[str] = Query(None, description="Usuario SSH (opcional)"),
    ssh_password: Optional[str] = Query(None, description="Contraseña SSH (opcional)")
) -> Dict[str, Any]:
    """
    Obtiene solo los clientes conectados al AP actual
    
    Args:
        ip_address: IP del dispositivo
        ssh_username: Usuario SSH (opcional)
        ssh_password: Contraseña SSH (opcional)
        
    Returns:
        Lista de clientes conectados al AP
    """
    try:
        ssh_client = await get_ssh_client()
        
        clients_info = await ssh_client.get_ap_clients(
            host=ip_address,
            username=ssh_username,
            password=ssh_password
        )
        
        return clients_info
        
    except Exception as e:
        logger.error(f"Error obteniendo clientes del AP: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo clientes: {str(e)}")
