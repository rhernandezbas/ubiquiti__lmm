"""
Routes para analizar estaciones y dispositivos Ubiquiti
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import traceback
from datetime import datetime
from app_fast_api.services.uisp_services import UISPService
from app_fast_api.services.llm_services import LLMService
from app_fast_api.services.ubiquiti_ssh_client import UbiquitiSSHClient
from app_fast_api.services.analyze_stations_services import AnalyzeStationsServices
from app_fast_api.services.ubiquiti_data_service import UbiquitiDataService
from app_fast_api.services.statistics_analyzer_service import StatisticsAnalyzerService
from app_fast_api.utils.logger import get_logger
from app_fast_api.utils.timezone import now_argentina

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
        
        if not ping_result.get("status") == "success":
            logger.warning(f"⚠️ Dispositivo {device.ip} no responde a ping")
            return {
                "status": "error",
                "message": f"Dispositivo {device.ip} no responde a ping",
                "device_info": device_data,
                "ping_result": ping_result
            }
        
        logger.info(f"✅ Ping exitoso: {ping_result.get('avg_ms', 'N/A')}ms de latencia")
        
        # Paso 3: Escanear y filtrar APs (usando función directa)
        logger.info("📡 Paso 3: Escaneando y filtrando APs...")
        scan_result = await analyze_service.scan_and_match_aps_direct(
            device_data=device_data,
            interface="ath0"
        )
        
        if not scan_result.get("status") == "success":
            logger.warning(f"⚠️ Error en escaneo de APs: {scan_result.get('error', 'Unknown error')}")
            return {
                "status": "error",
                "message": "Error escaneando APs",
                "error": scan_result.get("error"),
                "device_info": device_data,
                "ping_result": ping_result
            }
        
        logger.info(f"✅ Escaneo completado: {scan_result.get('our_aps_count', 0)} APs nuestros, {scan_result.get('foreign_aps_count', 0)} APs extranjeros")

        # Paso 3.5: Obtener estadísticas históricas (series temporales)
        # TEMPORAL: Deshabilitado hasta resolver formato de UISP
        statistics_analysis = None
        enable_statistics = True  # Cambiar a True para habilitar

        if enable_statistics:
            logger.info("📊 Paso 3.5: Obteniendo estadísticas históricas del dispositivo...")
            device_id = device_data.get('identification', {}).get('id')

            if device_id:
                logger.info(f"🔍 Device ID: {device_id}")
                statistics = await uisp_service.get_device_statistics(device_id, interval='fourhours')

                if statistics:
                    logger.info(f"✅ Estadísticas obtenidas")
                    # DEBUG: Ver estructura real de las estadísticas
                    logger.info(f"🔍 Tipo de statistics: {type(statistics)}")
                    logger.info(f"🔍 Keys de statistics: {statistics.keys() if isinstance(statistics, dict) else 'No es dict'}")

                    # Log complete structure for debugging
                    import json
                    try:
                        logger.info(f"🔍 ESTRUCTURA COMPLETA DE STATISTICS:")
                        logger.info(json.dumps(statistics, indent=2, default=str)[:2000])
                    except Exception as e:
                        logger.warning(f"⚠️ No se pudo serializar statistics: {e}")
                        logger.info(f"🔍 Statistics raw: {str(statistics)[:1000]}")

                    # Analizar series temporales
                    try:
                        statistics_analysis = StatisticsAnalyzerService.get_comprehensive_analysis(statistics)
                        logger.info(f"✅ Análisis de estadísticas completado")
                    except Exception as stats_error:
                        logger.error(f"⚠️ Error analizando estadísticas: {stats_error}")
                        statistics_analysis = None
                else:
                    logger.warning("⚠️ No se pudieron obtener estadísticas del dispositivo")
            else:
                logger.warning("⚠️ Device ID no disponible, omitiendo estadísticas")

        # Paso 4: Analizar con LLM
        logger.info("🤖 Paso 4: Generando análisis con LLM...")

        # Obtener información detallada del dispositivo
        device_info_detail = await analyze_service.get_device_data(device_data)
        analysis = device_info_detail

        # Obtener información completa del AP actual (incluyendo clientes)
        logger.info("📡 Obteniendo información completa del AP actual...")
        ap_complete_info = await analyze_service.get_current_ap_data(device_data)

        # Construir data completa para el prompt con la estructura correcta
        complete_data = {
            "device_info": {
                "ip": device.ip,
                "mac": device.mac if device.mac else 'No especificada',
                "identified_model": analysis.get('basic_info', {}).get('model', 'N/A'),
                "name": analysis.get('basic_info', {}).get('name', 'N/A'),
                "model": analysis.get('basic_info', {}).get('model', 'N/A'),
                "role": analysis.get('basic_info', {}).get('role', 'N/A'),
                "signal_dbm": analysis.get('signal_info', {}).get('signal_dbm', 'N/A'),
                "frequency_mhz": analysis.get('signal_info', {}).get('frequency_mhz', 'N/A'),
                "cpu_percent": analysis.get('system_info', {}).get('cpu_usage_percent', 'N/A'),
                "ram_percent": analysis.get('system_info', {}).get('ram_usage_percent', 'N/A')
            },
            "lan_info": {
                "ip_address": analysis.get('basic_info', {}).get('ip_address', 'N/A'),
                "ip_address_list": device_data.get('ipAddressList', []),
                "interface_id": analysis.get('interface_info', {}).get('interface_id', 'N/A'),
                "available_speed": analysis.get('interface_info', {}).get('available_speed', 'N/A')
            },
            "capacity": {
                "downlink_mbps": analysis.get('capacity_info', {}).get('downlink_capacity_mbps', 'N/A'),
                "uplink_mbps": analysis.get('capacity_info', {}).get('uplink_capacity_mbps', 'N/A')
            },
            "link_quality": {
                "overall_score": analysis.get('link_info', {}).get('overall_score', 'N/A'),
                "uplink_score": analysis.get('link_info', {}).get('uplink_score', 'N/A'),
                "downlink_score": analysis.get('link_info', {}).get('downlink_score', 'N/A')
            },
            "ap_info": {
                "name": ap_complete_info.get('basic_info', {}).get('name', analysis.get('ap_info', {}).get('ap_name', 'N/A')),
                "model": ap_complete_info.get('basic_info', {}).get('model', analysis.get('ap_info', {}).get('ap_model', 'N/A')),
                "ip": ap_complete_info.get('basic_info', {}).get('ip', '0.0.0.0'),
                "mac": ap_complete_info.get('basic_info', {}).get('mac', '00:00:00:00:00:00'),
                "site_name": ap_complete_info.get('basic_info', {}).get('site_name', 'Unknown'),
                "total_clients": ap_complete_info.get('clients', {}).get('total_clients', 0),
                "active_clients": ap_complete_info.get('clients', {}).get('active_clients', 0)
            },
            "scan_results": {
                "total_aps": scan_result.get('our_aps_count', 0) + scan_result.get('foreign_aps_count', 0),
                "our_aps": scan_result.get('our_aps', []),
                "our_aps_count": scan_result.get('our_aps_count', 0),
                "foreign_aps_count": scan_result.get('foreign_aps_count', 0)
            },
            "connectivity": {
                "ping_avg_ms": ping_result.get('avg_ms', 'N/A'),
                "packet_loss": ping_result.get('packet_loss', 100),
                "ping_status": ping_result.get('status', 'error')
            },
            "statistics": statistics_analysis if statistics_analysis else {
                "signal_analysis": {"error": "No data available"},
                "outage_analysis": {"error": "No data available"},
                "capacity_analysis": {"error": "No data available"}
            }
        }

        logger.info(f"✅ Data completa para el prompt: {complete_data}")
        
        # Debug: Verificar ping_result
        logger.info(f"🔍 Ping result completo: {ping_result}")
        logger.info(f"🔍 Ping avg_ms: {ping_result.get('avg_ms')} (tipo: {type(ping_result.get('avg_ms'))})")
        
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
- Latencia promedio: {complete_data['connectivity'].get('ping_avg_ms', 'N/A')} ms
- Pérdida de paquetes: {complete_data['connectivity'].get('packet_loss', 0)}%
- Estado de ping: {complete_data['connectivity'].get('ping_status', 'Unknown')}

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
- Clientes totales: {complete_data['ap_info'].get('total_clients', 0)}
- Clientes activos: {complete_data['ap_info'].get('active_clients', 0)}

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
HISTÓRICO (ÚLTIMAS 4 HORAS)
========================
SEÑAL:
- Señal actual: {complete_data['statistics']['signal_analysis'].get('current_signal_dbm', 'N/A')} dBm
- Señal promedio: {complete_data['statistics']['signal_analysis'].get('avg_signal_dbm', 'N/A')} dBm
- Señal mínima: {complete_data['statistics']['signal_analysis'].get('min_signal_dbm', 'N/A')} dBm
- Señal máxima: {complete_data['statistics']['signal_analysis'].get('max_signal_dbm', 'N/A')} dBm
- Estabilidad: {complete_data['statistics']['signal_analysis'].get('signal_stability', 'N/A')}
- Caídas detectadas: {complete_data['statistics']['signal_analysis'].get('drops_detected', 0)}

CAÍDAS/OUTAGES:
- Puntos de caída: {complete_data['statistics']['outage_analysis'].get('total_outage_points', 0)}
- Períodos de caída: {complete_data['statistics']['outage_analysis'].get('outage_periods', 0)}
- Caída reciente (última hora): {complete_data['statistics']['outage_analysis'].get('has_recent_outage', False)}

CAPACIDAD (HISTÓRICO):
- Downlink promedio: {complete_data['statistics']['capacity_analysis'].get('downlink_avg_mbps', 'N/A')} Mbps
- Uplink promedio: {complete_data['statistics']['capacity_analysis'].get('uplink_avg_mbps', 'N/A')} Mbps

========================
FORMATO DE RESPUESTA (OBLIGATORIO)
========================

1️⃣ CONECTIVIDAD (PING):
- Latencia: {complete_data['connectivity'].get('ping_avg_ms', 'N/A')} ms → Buena / Aceptable / Alta
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
- Clientes conectados: {complete_data['ap_info'].get('total_clients', 0)} ({complete_data['ap_info'].get('active_clients', 0)} activos)
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

7️⃣ HISTÓRICO (ÚLTIMAS 4 HORAS):
- Estabilidad de señal: {complete_data['statistics']['signal_analysis'].get('signal_stability', 'N/A')}
- Caídas detectadas: {complete_data['statistics']['signal_analysis'].get('drops_detected', 0)}
- ¿Hubo caída reciente?: {complete_data['statistics']['outage_analysis'].get('has_recent_outage', False)}
- Evaluación: Estable / Inestable / Crítico
- ¿Afecta diagnóstico?: Sí / No

8️⃣ RECOMENDACIÓN NOC (UNA SOLA, CLARA):
- Mantener AP actual (óptimo)
- Cambiar a AP [nombre] (mejor balance señal/clientes)
- Monitorear (historial inestable)
- Ajustar RF
- Escalar a técnico de campo (caídas frecuentes)

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
        analysis_id = None
        try:
            # Preparar llm_analysis como diccionario con la estructura esperada
            llm_analysis_dict = {
                "summary": llm_analysis,  # El análisis completo como summary
                "recommendations": [],  # TODO: Extraer recomendaciones del LLM
                "diagnosis": "Generated by LLM analysis",
                "needs_frequency_enable": False,
                "generated_at": now_argentina().isoformat(),
                "model": "gpt-4o-mini"
            }
            analysis = data_service.save_device_analysis(complete_data, llm_analysis_dict)
            if analysis and hasattr(analysis, 'id'):
                analysis_id = analysis.id
                logger.info(f"✅ Análisis guardado con ID: {analysis_id}")
        except Exception as e:
            logger.warning(f"⚠️ Error guardando en base de datos: {str(e)}")
            # Continuar aunque falle el guardado
        
        # Preparar respuesta (filtrar foreign_aps y matched_aps)
        our_aps_list = scan_result.get("our_aps", [])
        our_count = len(our_aps_list)
        foreign_count = scan_result.get("foreign_aps_count", 0)

        filtered_scan_result = {
            "status": scan_result.get("status"),
            "our_aps": our_aps_list,
            "our_aps_count": our_count,
            "foreign_aps_count": foreign_count,
            "total_aps": our_count + foreign_count
        }

        result = {
            "status": "success",
            "message": "Análisis completado exitosamente",
            "device_info": complete_data.get("device_info"),
            "scan_results": filtered_scan_result,
            "statistics_analysis": statistics_analysis,
            "ping_result": ping_result,  # Agregar resultado del ping
            "llm_analysis": llm_analysis,
            "analysis_id": analysis_id,
            "timestamp": logger.info("🎉 Análisis completado exitosamente")
        }
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error en análisis de estación: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}\n{traceback.format_exc()}")


@router.post("/statistics")
async def get_device_statistics(device: DeviceRequest, interval: str = 'fourhours') -> Dict[str, Any]:
    """
    Obtiene y analiza estadísticas históricas de un dispositivo.

    Args:
        device: IP/MAC del dispositivo
        interval: 'hour', 'fourhours', 'day', 'week', 'month'

    Returns:
        Análisis de series temporales (señal, caídas, capacidad)
    """
    try:
        logger.info(f"📊 Obteniendo estadísticas para {device.ip} (interval: {interval})")

        # Obtener servicios
        uisp_service, _, _, analyze_service, _ = get_services()

        # Paso 1: Identificar dispositivo para obtener ID
        logger.info("📡 Identificando dispositivo en UISP...")
        device_data = await analyze_service.match_device_data(device.ip, device.mac)

        if not device_data:
            raise HTTPException(
                status_code=404,
                detail=f"Dispositivo {device.ip} no encontrado en UISP"
            )

        device_id = device_data.get('identification', {}).get('id')
        if not device_id:
            raise HTTPException(
                status_code=404,
                detail="Device ID no disponible en UISP"
            )

        logger.info(f"✅ Device ID: {device_id}")

        # Paso 2: Obtener estadísticas
        logger.info(f"📊 Consultando estadísticas (interval: {interval})...")
        statistics = await uisp_service.get_device_statistics(device_id, interval)

        if not statistics:
            raise HTTPException(
                status_code=500,
                detail="No se pudieron obtener estadísticas de UISP"
            )

        logger.info(f"✅ Estadísticas obtenidas: {len(statistics)} métricas")

        # Paso 3: Analizar series temporales
        logger.info("🔍 Analizando series temporales...")
        analysis = StatisticsAnalyzerService.get_comprehensive_analysis(statistics)

        return {
            "status": "success",
            "device_ip": device.ip,
            "device_id": device_id,
            "device_name": device_data.get('identification', {}).get('name', 'Unknown'),
            "interval": interval,
            "raw_statistics": statistics,
            "analysis": analysis,
            "timestamp": now_argentina().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error obteniendo estadísticas: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

