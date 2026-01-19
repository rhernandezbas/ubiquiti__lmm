"""
Validaciones de tipo de dispositivo y modo de operación
"""

from typing import Dict, Any, Optional
from app.infrastructure.ssh.ubiquiti_ssh_client import UbiquitiSSHClient
from app.config.device_frequencies import get_frequencies_for_model
import logging

logger = logging.getLogger(__name__)


async def validate_device_type_and_mode(
    ssh_client: UbiquitiSSHClient,
    device_ip: str,
    device_model: str,
    ssh_username: str,
    ssh_password: str
) -> Dict[str, Any]:
    """
    Valida el tipo de dispositivo y modo de operación
    
    Args:
        ssh_client: Cliente SSH
        device_ip: IP del dispositivo
        device_model: Modelo del dispositivo
        ssh_username: Usuario SSH
        ssh_password: Contraseña SSH
        
    Returns:
        Diccionario con validación de tipo y modo
    """
    try:
        # Determinar tipo de equipo por modelo
        device_type = determine_device_type(device_model)
        
        # Obtener modo de operación via SSH
        mode_result = await get_device_mode(ssh_client, device_ip, ssh_username, ssh_password)
        
        is_station = mode_result.get("is_station", False)
        is_ap = mode_result.get("is_ap", False)
        wireless_mode = mode_result.get("mode", "unknown")
        
        validation_result = {
            "success": True,
            "device_model": device_model,
            "device_type": device_type,  # "M5_AC" o "M2"
            "is_station": is_station,
            "is_ap": is_ap,
            "wireless_mode": wireless_mode,
            "supports_current_logic": device_type == "M5_AC" and is_station,
            "recommendation": get_device_recommendation(device_type, is_station, is_ap),
            "mode_details": mode_result
        }
        
        logger.info(f"Dispositivo {device_ip}: {device_model} - Tipo: {device_type}, Modo: {wireless_mode}")
        
        return validation_result
        
    except Exception as e:
        logger.error(f"Error validando dispositivo {device_ip}: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "device_model": device_model,
            "supports_current_logic": False
        }


def determine_device_type(device_model: str) -> str:
    """
    Determina el tipo de dispositivo basado en el modelo
    
    Args:
        device_model: Modelo del dispositivo
        
    Returns:
        "M5_AC" o "M2"
    """
    model_upper = device_model.upper()
    
    # M2 Equipment - Prioridad alta
    if model_upper == "M2" or " M2 " in model_upper or model_upper.endswith(" M2"):
        return "M2"
    
    # M5/AC Equipment - Frecuencias 5 GHz
    if "M5" in model_upper or "AC" in model_upper:
        return "M5_AC"
    
    # Default - Asumir M5/AC para equipos desconocidos
    return "M5_AC"


async def get_device_mode(
    ssh_client: UbiquitiSSHClient,
    device_ip: str,
    ssh_username: str,
    ssh_password: str
) -> Dict[str, Any]:
    """
    Obtiene el modo de operación del dispositivo via SSH
    
    Args:
        ssh_client: Cliente SSH
        device_ip: IP del dispositivo
        ssh_username: Usuario SSH
        ssh_password: Contraseña SSH
        
    Returns:
        Diccionario con información del modo
    """
    try:
        conn = await ssh_client.connect(device_ip, ssh_username, ssh_password)
        
        # Obtener configuración wireless
        result = await ssh_client.execute_command(conn, "iwconfig ath0")
        
        if not result["success"]:
            return {
                "success": False,
                "error": result.get("stderr"),
                "mode": "unknown",
                "is_station": False,
                "is_ap": False
            }
        
        output = result["stdout"]
        
        # Parsear modo
        is_station = False
        is_ap = False
        mode = "unknown"
        
        for line in output.split("\n"):
            line = line.strip()
            
            if "Mode:" in line:
                mode_part = line.split("Mode:")[1].split()[0]
                mode = mode_part
                
                if mode_part.lower() == "managed":
                    is_station = True
                elif mode_part.lower() == "master" or mode_part.lower() == "ap":
                    is_ap = True
                break
        
        # Verificar también si está conectado a un AP
        connected_to_ap = False
        if "Access Point:" in output:
            connected_to_ap = True
            # Si está conectado a un AP, es una estación
            is_station = True
            is_ap = False
        
        await conn.close()
        await conn.wait_closed()
        
        return {
            "success": True,
            "mode": mode,
            "is_station": is_station,
            "is_ap": is_ap,
            "connected_to_ap": connected_to_ap,
            "raw_output": output
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo modo del dispositivo {device_ip}: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "mode": "unknown",
            "is_station": False,
            "is_ap": False
        }


def get_device_recommendation(device_type: str, is_station: bool, is_ap: bool) -> str:
    """
    Obtiene recomendación basada en tipo y modo del dispositivo
    
    Args:
        device_type: "M5_AC" o "M2"
        is_station: True si es estación
        is_ap: True si es AP
        
    Returns:
        Recomendación de qué hacer con el dispositivo
    """
    if device_type == "M2":
        if is_station:
            return "Dispositivo M2 Station - Usar lógica de frecuencias M2"
        elif is_ap:
            return "Dispositivo M2 AP - Verificar clientes y configuración M2"
        else:
            return "Dispositivo M2 - Modo no identificado"
    
    elif device_type == "M5_AC":
        if is_station:
            return "Dispositivo M5/AC Station - Aplicar lógica completa actual"
        elif is_ap:
            return "Dispositivo M5/AC AP - Verificar clientes y optimización"
        else:
            return "Dispositivo M5/AC - Modo no identificado"
    
    else:
        return "Tipo de dispositivo desconocido"


def should_apply_current_logic(validation_result: Dict[str, Any]) -> bool:
    """
    Determina si se debe aplicar la lógica actual de análisis
    
    Args:
        validation_result: Resultado de validate_device_type_and_mode
        
    Returns:
        True si se aplica lógica actual, False si necesita otra lógica
    """
    return (
        validation_result.get("success", False) and
        validation_result.get("supports_current_logic", False)
    )
