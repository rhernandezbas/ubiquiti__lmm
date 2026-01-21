"""
Routes para analizar estaciones y dispositivos Ubiquiti
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging
import traceback
import asyncio

from app_fast_api.services.uisp_services import UISPService
from app_fast_api.services.llm_services import LLMService
from app_fast_api.services.ubiquiti_ssh_client import UbiquitiSSHClient
from app_fast_api.services.analyze_stations_services import AnalyzeStationsServices
from app_fast_api.services.ubiquiti_data_service import UbiquitiDataService
from app_fast_api.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/stations", tags=["Station Analysis"])

# Instancias singleton de servicios
_uisp_service = None
_llm_service = None
_ssh_service = None
_analyze_service = None
_data_service = None

def get_services():
    """Obtiene instancias singleton de los servicios"""
    global _uisp_service, _llm_service, _ssh_service, _analyze_service, _data_service
    
    if _uisp_service is None:
        _uisp_service = UISPService("https://190.7.234.36/", "cb53a0bc-48e8-480c-aa47-19e1042e4897")
        _llm_service = LLMService()  # Usará API Key de variable de entorno (codificada)
        _ssh_service = UbiquitiSSHClient()
        _analyze_service = AnalyzeStationsServices(_llm_service, _uisp_service, _ssh_service)
        _data_service = UbiquitiDataService()
    
    return _uisp_service, _llm_service, _ssh_service, _analyze_service, _data_service

# Pydantic models
class DeviceRequest(BaseModel):
    ip: str
    mac: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    interface: Optional[str] = "ath0"

class FrequencyRequest(BaseModel):
    ip: str
    mac: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    device_model: Optional[str] = None

class PingRequest(BaseModel):
    ip: str
    max_wait_time: Optional[int] = 360
    check_interval: Optional[int] = 5

@router.post("/analyze")
async def analyze_station(device: DeviceRequest) -> Dict[str, Any]:
    """
    Analiza una estación completa: identifica modelo, escanea APs y genera recomendaciones LLM
    """
    try:
        logger.info(f"🚀 Iniciando análisis completo para dispositivo {device.ip}")
        
        # Obtener servicios
        uisp_service, llm_service, ssh_service, analyze_service, data_service = get_services()
        
        # Paso 1: Identificar dispositivo
        logger.info("📡 Paso 1: Identificando dispositivo en UISP...")
        device_data = await analyze_service.match_device_data(device.ip, device.mac)
        
        if not device_data:
            logger.warning(f"⚠️ Dispositivo {device.ip} no encontrado en UISP")
            return {
                "status": "error",
                "message": f"Dispositivo {device.ip} no encontrado en UISP",
                "device_info": {"ip": device.ip, "mac": device.mac}
            }
        
        logger.info(f"✅ Dispositivo encontrado: {device_data.get('identification', {}).get('name', 'Unknown')}")
        
        # Paso 2: Escanear APs cercanos
        logger.info("📡 Paso 2: Escaneando APs cercanos...")
        scan_result = await ssh_service.scan_nearby_aps_detailed(
            device.ip, 
            device.interface, 
            device.username, 
            device.password
        )
        
        if not scan_result.get("success", False):
            logger.warning(f"⚠️ Error en escaneo de APs: {scan_result.get('error', 'Unknown error')}")
            return {
                "status": "error",
                "message": "Error escaneando APs",
                "error": scan_result.get("error"),
                "device_info": device_data
            }
        
        logger.info(f"✅ Escaneo completado: {scan_result.get('total_aps', 0)} APs encontrados")
        
        # Paso 3: Analizar con LLM
        logger.info("🤖 Paso 3: Generando análisis con LLM...")
        
        # Preparar datos para LLM
        complete_data = {
            "device_info": await analyze_service.get_device_data(device_data),
            "scan_results": scan_result,
            "connectivity": await ssh_service.ping_device_seconds(device.ip, 10),
            "lan_info": {},  # TODO: Implementar obtención de info LAN
            "capacity": {},  # TODO: Implementar obtención de capacidad
            "link_quality": {}  # TODO: Implementar cálculo de calidad de enlace
        }
        
        # Generar análisis LLM
        llm_analysis = await llm_service.analyze(complete_data)
        
        if not llm_analysis:
            logger.error("❌ Error generando análisis LLM")
            return {
                "status": "error",
                "message": "Error generando análisis LLM",
                "device_info": device_data,
                "scan_results": scan_result
            }
        
        logger.info(f"✅ Análisis LLM generado: {len(llm_analysis)} caracteres")
        
        # Paso 4: Guardar en base de datos
        logger.info("💾 Paso 4: Guardando análisis en base de datos...")
        try:
            analysis = data_service.save_device_analysis(complete_data, llm_analysis)
            logger.info(f"✅ Análisis guardado con ID: {analysis.id}")
        except Exception as e:
            logger.warning(f"⚠️ Error guardando en base de datos: {str(e)}")
            # Continuar aunque falle el guardado
        
        # Preparar respuesta
        result = {
            "status": "success",
            "message": "Análisis completado exitosamente",
            "device_info": complete_data.get("device_info"),
            "scan_results": scan_result,
            "llm_analysis": llm_analysis,
            "analysis_id": analysis.id if 'analysis' in locals() else None,
            "timestamp": logger.info("🎉 Análisis completado exitosamente")
        }
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error en análisis de estación: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}\n{traceback.format_exc()}")

@router.post("/identify-device")
async def identify_device(device: DeviceRequest) -> Dict[str, Any]:
    """
    Identifica un dispositivo por IP o MAC
    """
    try:
        logger.info(f"🔍 Identificando dispositivo: IP={device.ip}, MAC={device.mac}")
        
        uisp_service, _, _, _, _ = get_services()
        device_data = await uisp_service.get_device_by_ip(device.ip)
        
        if not device_data:
            return {
                "status": "error",
                "message": f"Dispositivo {device.ip} no encontrado",
                "device_found": False
            }
        
        return {
            "status": "success",
            "message": "Dispositivo encontrado",
            "device_found": True,
            "device_data": device_data
        }
        
    except Exception as e:
        logger.error(f"❌ Error identificando dispositivo: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/enable-frequencies")
async def enable_frequencies(request: FrequencyRequest) -> Dict[str, Any]:
    """
    Habilita frecuencias para M5/M2
    """
    try:
        logger.info(f"📡 Habilitando frecuencias para dispositivo {request.ip}")
        
        _, _, ssh_service, _, _ = get_services()
        
        result = await ssh_service.enable_all_m5_frequencies(
            request.ip,
            request.device_model,
            request.username,
            request.password
        )
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error habilitando frecuencias: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/wait-for-connection")
async def wait_for_connection(request: PingRequest) -> Dict[str, Any]:
    """
    Espera a que el dispositivo vuelva a estar online después de habilitar frecuencias
    """
    try:
        logger.info(f"⏳ Esperando reconexión de dispositivo {request.ip}")
        
        _, _, ssh_service, _, _ = get_services()
        
        result = await ssh_service.ping_until_connected(
            request.ip,
            request.max_wait_time,
            request.check_interval
        )
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error esperando conexión: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/flow-status/{ip}")
async def get_flow_status(ip: str) -> Dict[str, Any]:
    """
    Obtiene el estado actual del flujo para una IP
    """
    try:
        logger.info(f"📊 Obteniendo estado del flujo para {ip}")
        
        # TODO: Implementar estado del flujo
        return {
            "status": "pending",
            "ip": ip,
            "message": "Estado del flujo no implementado aún"
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo estado del flujo: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
