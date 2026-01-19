"""
Endpoint para debug de comandos SSH
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.infrastructure.ssh.ubiquiti_ssh_client import UbiquitiSSHClient
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["debug"])


@router.get("/debug-ssh-commands")
async def debug_ssh_commands(
    ip_address: str = Query(..., description="IP del dispositivo"),
    ssh_username: Optional[str] = Query(None, description="Usuario SSH"),
    ssh_password: Optional[str] = Query(None, description="Contraseña SSH")
) -> dict:
    """
    Endpoint para debug de comandos SSH y ver qué devuelven
    """
    try:
        ssh_client = UbiquitiSSHClient()
        
        results = {}
        
        # Probar diferentes comandos para obtener clientes
        commands_to_test = [
            "iwpriv ath0 get_sta_list",
            "iwconfig ath0 station list", 
            "wlanconfig ath0 list",
            "cat /proc/net/wireless",
            "brctl show",
            "cat /etc/version"
        ]
        
        conn = await ssh_client.connect(ip_address, ssh_username, ssh_password)
        
        for cmd in commands_to_test:
            try:
                result = await ssh_client.execute_command(conn, cmd)
                results[cmd] = {
                    "success": result["success"],
                    "stdout": result["stdout"][:500] if result["stdout"] else "",
                    "stderr": result["stderr"][:200] if result["stderr"] else "",
                    "lines_count": len(result["stdout"].split('\n')) if result["stdout"] else 0
                }
            except Exception as e:
                results[cmd] = {
                    "success": False,
                    "error": str(e)
                }
        
        await conn.close()
        await conn.wait_closed()
        
        return {
            "device_ip": ip_address,
            "commands_tested": results
        }
        
    except Exception as e:
        logger.error(f"Error en debug SSH: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/debug-station-info")
async def debug_station_info(
    ip_address: str = Query(..., description="IP del dispositivo"),
    ssh_username: Optional[str] = Query(None, description="Usuario SSH"),
    ssh_password: Optional[str] = Query(None, description="Contraseña SSH")
) -> dict:
    """
    Verifica si el dispositivo es estación o AP
    """
    try:
        ssh_client = UbiquitiSSHClient()
        
        conn = await ssh_client.connect(ip_address, ssh_username, ssh_password)
        
        # Verificar modo de operación
        iwconfig_result = await ssh_client.execute_command(conn, "iwconfig ath0")
        
        info = {
            "device_ip": ip_address,
            "iwconfig_output": iwconfig_result["stdout"] if iwconfig_result["success"] else "",
            "iwconfig_error": iwconfig_result["stderr"] if iwconfig_result["success"] else "",
            "is_station": False,
            "is_ap": False,
            "analysis": ""
        }
        
        if iwconfig_result["success"]:
            output = iwconfig_result["stdout"]
            if "Mode:Managed" in output:
                info["is_station"] = True
                info["analysis"] = "Dispositivo es STATION (cliente) - no puede tener clientes conectados"
            elif "Mode:Master" in output:
                info["is_ap"] = True
                info["analysis"] = "Dispositivo es AP - debería poder tener clientes conectados"
            else:
                info["analysis"] = "Modo no identificado en iwconfig"
        
        await conn.close()
        await conn.wait_closed()
        
        return info
        
    except Exception as e:
        logger.error(f"Error debug station info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
