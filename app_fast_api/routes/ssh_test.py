from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging

from app_fast_api.services.ubiquiti_ssh_client import UbiquitiSSHClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ssh-test", tags=["SSH Test"])

# Instancia del cliente SSH
ssh_client = UbiquitiSSHClient()

class SSHConnectionRequest(BaseModel):
    host: str
    username: Optional[str] = None
    password: Optional[str] = None
    port: int = 22

class CommandRequest(BaseModel):
    host: str
    command: str
    username: Optional[str] = None
    password: Optional[str] = None
    port: int = 22

class ScanRequest(BaseModel):
    host: str
    interface: str = "ath0"
    username: Optional[str] = None
    password: Optional[str] = None

@router.post("/connect")
async def test_connection(request: SSHConnectionRequest) -> Dict[str, Any]:
    """
    Prueba la conexión SSH a un dispositivo
    """
    try:
        conn = await ssh_client.connect(
            host=request.host,
            username=request.username,
            password=request.password,
            port=request.port
        )
        
        # Probar ejecutando un comando simple
        result = await conn.run("uname -a", check=True)
        
        conn.close()
        await conn.wait_closed()
        
        return {
            "success": True,
            "host": request.host,
            "message": "Conexión SSH exitosa",
            "command_result": result.stdout.strip()
        }
        
    except Exception as e:
        logger.error(f"Error en conexión SSH a {request.host}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error de conexión SSH: {str(e)}")

@router.post("/command")
async def execute_command(request: CommandRequest) -> Dict[str, Any]:
    """
    Ejecuta un comando en el dispositivo vía SSH
    """
    try:
        result = await ssh_client.execute_command_with_auth(
            host=request.host,
            command=request.command,
            username=request.username,
            password=request.password,
            port=request.port
        )
        
        return {
            "success": result["success"],
            "host": request.host,
            "command": request.command,
            "stdout": result["stdout"],
            "stderr": result["stderr"],
            "exit_status": result["exit_status"]
        }
        
    except (HTTPException, ValueError, KeyError) as e:
        logger.error(f"Error ejecutando comando en {request.host}: {str(e)}")
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=f"Error ejecutando comando: {str(e)}")

@router.post("/scan-aps")
async def scan_nearby_aps(request: ScanRequest) -> Dict[str, Any]:
    """
    Escanea APs cercanos usando iwlist (puede tardar 15-30 segundos)
    """
    try:
        logger.info(f"Iniciando escaneo de APs en {request.host} (puede tardar 15-30 segundos)")
        
        result = await ssh_client.scan_nearby_aps_detailed(
            host=request.host,
            interface=request.interface,
            username=request.username,
            password=request.password
        )
        
        logger.info(f"Escaneo completado para {request.host}")
        
        return {
            "success": result["success"],
            "host": request.host,
            "interface": request.interface,
            "aps_found": result.get("aps_count", 0),
            "scan_duration": result.get("scan_duration", "unknown"),
            "scan_data": result
        }
        
    except Exception as e:
        logger.error(f"Error escaneando APs en {request.host}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error escaneando APs: {str(e)}")

@router.post("/device-info")
async def get_device_info(request: SSHConnectionRequest) -> Dict[str, Any]:
    """
    Obtiene información básica del dispositivo
    """
    try:
        commands = {
            "system_info": "uname -a",
            "uptime": "uptime",
            "memory": "free -m",
            "disk": "df -h",
            "interfaces": "ip link show"
        }
        
        results = {}
        conn = await ssh_client.connect(
            host=request.host,
            username=request.username,
            password=request.password,
            port=request.port
        )
        
        for name, cmd in commands.items():
            try:
                result = await conn.run(cmd, check=True)
                results[name] = {
                    "success": True,
                    "output": result.stdout.strip()
                }
            except Exception as e:
                results[name] = {
                    "success": False,
                    "error": str(e)
                }
        
        conn.close()
        await conn.wait_closed()
        
        return {
            "success": True,
            "host": request.host,
            "device_info": results
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo info del dispositivo {request.host}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo información: {str(e)}")

class EnableACFreqRequest(BaseModel):
    host: str
    device_model: str
    username: Optional[str] = None
    password: Optional[str] = None

@router.post("/enable-ac-freq")
async def enable_ac_frequencies(request: EnableACFreqRequest) -> Dict[str, Any]:
    """
    Habilita todas las frecuencias AC para dispositivos Ubiquiti
    """
    try:
        result = await ssh_client.enable_all_AC_frequencies(
            host=request.host,
            device_model=request.device_model,
            username=request.username,
            password=request.password
        )
        
        return {
            "success": result["success"],
            "host": request.host,
            "device_model": request.device_model,
            "message": result.get("message", ""),
            "action": result.get("action", ""),
            "frequencies_before": result.get("frequencies_before", 0),
            "frequencies_after": result.get("frequencies_after", 0),
            "frequencies_added": result.get("frequencies_added", 0),
            "frequency_range": result.get("frequency_range", ""),
            "current_config": result.get("current_config", ""),
            "new_config": result.get("new_config", "")
        }
        
    except Exception as e:
        logger.error(f"Error habilitando frecuencias AC en {request.host}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error habilitando frecuencias AC: {str(e)}")

@router.post("/enable-m5-freq")
async def enable_m5_frequencies(request: EnableACFreqRequest) -> Dict[str, Any]:
    """
    Habilita todas las frecuencias M5/AC para dispositivos Ubiquiti
    """
    try:
        result = await ssh_client.enable_all_m5_frequencies(
            host=request.host,
            device_model=request.device_model,
            username=request.username,
            password=request.password
        )
        
        return {
            "success": result["success"],
            "host": request.host,
            "device_model": request.device_model,
            "message": result.get("message", ""),
            "action": result.get("action", ""),
            "step": result.get("step", ""),
            "frequencies_before": result.get("frequencies_before", 0),
            "frequencies_after": result.get("frequencies_after", 0),
            "frequencies_added": result.get("frequencies_added", 0),
            "frequency_range": result.get("frequency_range", ""),
            "current_config": result.get("current_config", ""),
            "new_config": result.get("new_config", ""),
            "commands_executed": result.get("commands_executed", []),
            "error": result.get("error", ""),
            "debug_info": result.get("debug_info", {})
        }
        
    except Exception as e:
        logger.error(f"Error habilitando frecuencias M5 en {request.host}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error habilitando frecuencias M5: {str(e)}")

@router.get("/test-endpoints")
async def test_endpoints():
    """
    Endpoint de prueba para verificar que las rutas funcionan
    """
    return {
        "message": "SSH Test API funcionando",
        "available_endpoints": [
            "POST /ssh-test/connect - Prueba conexión SSH",
            "POST /ssh-test/command - Ejecuta comando",
            "POST /ssh-test/scan-aps - Escanea APs cercanos",
            "POST /ssh-test/device-info - Obtiene info del dispositivo",
            "POST /ssh-test/enable-ac-freq - Habilita frecuencias AC",
            "POST /ssh-test/enable-m5-freq - Habilita frecuencias M5/AC",
            "GET /ssh-test/test-endpoints - Este endpoint"
        ]
    }
