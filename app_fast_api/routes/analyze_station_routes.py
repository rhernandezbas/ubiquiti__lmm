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
        try:
            logger.info("🔧 Inicializando servicios...")
            
            _uisp_service = UISPService("https://190.7.234.36/", "cb53a0bc-48e8-480c-aa47-19e1042e4897")
            logger.info("✅ UISP Service inicializado")
            
            _llm_service = LLMService()  # Usará API Key de variable de entorno (codificada)
            logger.info("✅ LLM Service inicializado")
            
            _ssh_service = UbiquitiSSHClient()
            logger.info("✅ SSH Service inicializado")
            
            _analyze_service = AnalyzeStationsServices(_llm_service, _uisp_service, _ssh_service)
            logger.info("✅ Analyze Service inicializado")
            
            _data_service = UbiquitiDataService()
            logger.info("✅ Data Service inicializado")
            
            logger.info("🎉 Todos los servicios inicializados correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando servicios: {str(e)}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Error inicializando servicios: {str(e)}")
    
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
        
        # Paso 2: Verificar conectividad con ping (10 segundos)
        logger.info("🏓 Paso 2: Verificando conectividad con ping (10 segundos)...")
        ping_result = await ssh_service.ping_device_seconds(device.ip, 10)
        
        if not ping_result.get("success", False):
            logger.warning(f"⚠️ Dispositivo {device.ip} no responde a ping")
            return {
                "status": "error",
                "message": f"Dispositivo {device.ip} no responde a ping",
                "device_info": device_data,
                "ping_result": ping_result
            }
        
        logger.info(f"✅ Ping exitoso: {ping_result.get('avg_latency', 'N/A')}ms de latencia")
        
        # Paso 3: Escanear APs cercanos
        logger.info("📡 Paso 3: Escaneando APs cercanos...")
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
        
        # Paso 4: Analizar con LLM
        logger.info("🤖 Paso 4: Generando análisis con LLM...")
        
        # Obtener información detallada del dispositivo
        device_info_detail = await analyze_service.get_device_data(device_data)
        
        # Construir data completa para el prompt
        complete_data = {
            "device_info": device_info_detail,
            "scan_results": scan_result,
            "connectivity": ping_result,
            "lan_info": {
                "ip_address": device_data.get("overview", {}).get("ipAddress", "N/A"),
                "ip_address_list": device_data.get("overview", {}).get("ipAddressList", []),
                "interface_id": device_data.get("mainInterfaceSpeed", {}).get("interfaceId", "eth0"),
                "available_speed": device_data.get("mainInterfaceSpeed", {}).get("availableSpeed", "N/A")
            },
            "capacity": {
                "downlink_mbps": device_data.get("statistics", {}).get("rxRate", 0) // 1000000 if device_data.get("statistics", {}).get("rxRate") else 0,
                "uplink_mbps": device_data.get("statistics", {}).get("txRate", 0) // 1000000 if device_data.get("statistics", {}).get("txRate") else 0
            },
            "link_quality": {
                "overall_score": device_data.get("linkQuality", {}).get("overallScore", 0),
                "downlink_score": device_data.get("linkQuality", {}).get("downlinkScore", 0),
                "uplink_score": device_data.get("linkQuality", {}).get("uplinkScore", 0)
            },
            "ap_info": await analyze_service.get_current_ap_data(device_data)
        }

        logger.info(f"✅ Data completa para el prompt: {complete_data}")
        
        # Construir prompt con toda la data
        prompt = f"""
Actúa como operador NOC de primer nivel de un ISP.

Analiza el siguiente dispositivo y responde de forma SIMPLE, DIRECTA y OPERATIVA.
Evita explicaciones largas o teóricas. Usa solo los datos disponibles.

========================
DISPOSITIVO
========================
- Nombre: {complete_data['device_info'].get('name', 'Unknown')}
- Modelo: {complete_data['device_info'].get('model', 'Unknown')}
- Rol: {complete_data['device_info'].get('role', 'Unknown')}
- IP: {complete_data['device_info'].get('ip', device.ip)}
- MAC: {complete_data['device_info'].get('mac', 'Unknown')}

HARDWARE:
- CPU: {complete_data['device_info'].get('cpu_percent', 0)}%
- RAM: {complete_data['device_info'].get('ram_percent', 0)}%

========================
CONECTIVIDAD (PING)
========================
- Latencia promedio: {complete_data['connectivity'].get('avg_latency', 'N/A')} ms
- Pérdida de paquetes: {complete_data['connectivity'].get('packet_loss', 0)}%
- Estado de ping: {complete_data['connectivity'].get('status', 'Unknown')}

========================
LAN
========================
- IP LAN: {complete_data['lan_info'].get('ip_address', 'N/A')}
- Interfaces IP: {complete_data['lan_info'].get('ip_address_list', [])}
- Puerto: {complete_data['lan_info'].get('interface_id', 'N/A')}
- Velocidad Ethernet: {complete_data['lan_info'].get('available_speed', 'N/A')}

========================
WIRELESS ACTUAL
========================
- Señal: {complete_data['device_info'].get('signal_dbm', 'N/A')} dBm
- Frecuencia: {complete_data['device_info'].get('frequency_mhz', 'N/A')} MHz
- AP conectado: {complete_data['ap_info'].get('name', 'N/A')} ({complete_data['ap_info'].get('model', 'N/A')})
- clientes: {complete_data['ap_info'].get('clients', 0)}

========================
CAPACIDAD
========================
- Downlink: {complete_data['capacity'].get('downlink_mbps', 0)} Mbps
- Uplink: {complete_data['capacity'].get('uplink_mbps', 0)} Mbps

========================
LINK SCORE
========================
- Score total: {complete_data['link_quality'].get('overall_score', 0)}
- Downlink score: {complete_data['link_quality'].get('downlink_score', 0)}
- Uplink score: {complete_data['link_quality'].get('uplink_score', 0)}

========================
SCAN / SITE SURVEY
========================
- APS detectados: {complete_data['scan_results'].get('total_aps', 0)}
- APS disponibles:
{complete_data['scan_results'].get('our_aps', [])}

========================
FORMATO DE RESPUESTA (OBLIGATORIO)
========================

1️⃣ CONECTIVIDAD (PING):
- Latencia: {complete_data['connectivity'].get('avg_latency', 'N/A')} ms → Buena / Aceptable / Alta
- Pérdida: {complete_data['connectivity'].get('packet_loss', 0)}% → OK / Problema
- Diagnóstico de conectividad: OK / DEGRADADO / CRÍTICO

2️⃣ ESTADO GENERAL:
- Estado del equipo: OK / DEGRADADO / CRÍTICO
- Motivo principal (1 línea, claro y técnico)

3️⃣ LAN:
- Velocidad Ethernet: {complete_data['lan_info'].get('available_speed', 'N/A')}
- ¿Es un cuello de botella?: Sí / No

4️⃣ WIRELESS / AP ACTUAL:
- AP actual: {complete_data['ap_info'].get('name', 'N/A')}
- Señal: {complete_data['device_info'].get('signal_dbm', 'N/A')} dBm → Excelente / Buena / Regular / Mala
- Frecuencia: {complete_data['device_info'].get('frequency_mhz', 'N/A')} MHz
- Capacidad: {complete_data['capacity'].get('downlink_mbps', 0)}/{complete_data['capacity'].get('uplink_mbps', 0)} Mbps
- AP actual adecuado: Sí / No

5️⃣ APS ALTERNATIVOS (SCAN):
- ¿Hay APs mejores?: Sí / No
- Si hay mejores:
  - Indicar AP recomendado
  - Comparar señal (dBm) y carga
  - Considerar cambio solo si:
    - Diferencia ≤ 3 dBm
    - Menor cantidad de clientes
- Si no hay mejores:
  - Confirmar que el AP actual es el óptimo

6️⃣ LINK SCORE:
- Score total: {complete_data['link_quality'].get('overall_score', 0)}
- Evaluación: Excelente / Bueno / Regular / Malo
- Impacta en el servicio: Sí / No

7️⃣ RECOMENDACIÓN NOC (UNA SOLA, CLARA):
- Mantener AP actual (óptimo)
- Cambiar a AP [nombre] (mejor balance señal/clientes)
- Monitorear
- Ajustar RF
- Escalar a técnico de campo

Usa nombres reales de los APs y decisiones basadas en señal, ping y carga.
"""
        
        # Generar análisis LLM con el prompt construido
        llm_analysis = await llm_service.analyze({"prompt": prompt})
        
        if not llm_analysis:
            logger.error("❌ Error generando análisis LLM")
            return {
                "status": "error",
                "message": "Error generando análisis LLM",
                "device_info": device_data,
                "scan_results": scan_result
            }
        
        logger.info(f"✅ Análisis LLM generado: {len(llm_analysis)} caracteres")
        
        # Paso 5: Guardar en base de datos
        logger.info("💾 Paso 5: Guardando análisis en base de datos...")
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
            "ping_result": ping_result,  # Agregar resultado del ping
            "llm_analysis": llm_analysis,
            "analysis_id": analysis.id if 'analysis' in locals() else None,
            "timestamp": logger.info("🎉 Análisis completado exitosamente")
        }
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error en análisis de estación: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}\n{traceback.format_exc()}")

