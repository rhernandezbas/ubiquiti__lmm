from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import logging
from app.application.services.diagnostic_service import DiagnosticService
from app.domain.entities.device import DiagnosticResult, Device
from app.utils.dependencies import get_diagnostic_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])

class DiagnosticResponse(BaseModel):
    device_id: str
    timestamp: datetime
    status: str
    issues: List[str]
    recommendations: List[str]
    confidence: float
    patterns_matched: List[str]
    error_message: Optional[str] = None
    summary: Optional[str] = None
    ethernet: Optional[str] = None
    tiempo_encendido: Optional[str] = None
    cortes_recientes: Optional[str] = None
    
    class Config:
        from_attributes = True

class DeviceResponse(BaseModel):
    id: str
    name: str
    ip_address: str
    mac_address: str
    model: str
    status: str
    last_seen: datetime
    firmware_version: str = None
    uptime: int = None
    
    class Config:
        from_attributes = True

@router.post("/by-ip", response_model=DiagnosticResponse)
async def diagnose_device_by_ip(
    ip_address: str = Query(..., description="IP address of the device to diagnose"),
    use_patterns: bool = Query(True, description="Use predefined diagnostic patterns"),
    diagnostic_service: DiagnosticService = Depends(get_diagnostic_service)
) -> DiagnosticResponse:
    try:
        result = await diagnostic_service.diagnose_device_by_ip(ip_address, use_patterns=use_patterns)
        
        # Extraer campos adicionales del raw_data si existen
        raw_data = result.raw_data or {}
        llm_analysis = raw_data.get("llm_analysis", {})
        
        return DiagnosticResponse(
            device_id=result.device_id,
            timestamp=result.timestamp,
            status=result.status.value,
            issues=result.issues,
            recommendations=result.recommendations,
            confidence=result.confidence,
            patterns_matched=result.patterns_matched,
            error_message=result.error_message,
            summary=llm_analysis.get("summary"),
            ethernet=llm_analysis.get("ethernet"),
            tiempo_encendido=llm_analysis.get("tiempo_encendido"),
            cortes_recientes=llm_analysis.get("cortes_recientes")
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=f"Error de conexión con UISP: {str(e)}")
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.post("/{device_id}", response_model=DiagnosticResponse)
async def diagnose_device(
    device_id: str,
    use_patterns: bool = Query(True, description="Use predefined diagnostic patterns"),
    diagnostic_service: DiagnosticService = Depends(get_diagnostic_service)
) -> DiagnosticResponse:
    try:
        result = await diagnostic_service.diagnose_device(device_id, use_patterns=use_patterns)
        return DiagnosticResponse(
            device_id=result.device_id,
            timestamp=result.timestamp,
            status=result.status.value,
            issues=result.issues,
            recommendations=result.recommendations,
            confidence=result.confidence,
            patterns_matched=result.patterns_matched,
            error_message=result.error_message
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scan-aps/by-ip")
async def scan_nearby_aps_by_ip(
    ip_address: str = Query(..., description="IP address of the device to scan from"),
    ssh_username: Optional[str] = Query(None, description="Usuario SSH"),
    ssh_password: Optional[str] = Query(None, description="Contraseña SSH")
):
    """
    Escanea APs cercanos desde un dispositivo específico por IP usando SSH.
    NOTA: El endpoint de UISP /spectrum-scan no está disponible en v2.1
    """
    from app.utils.dependencies import get_uisp_client
    from app.config.settings import settings
    from app.infrastructure.ssh import UbiquitiSSHClient
    
    try:
        # Buscar dispositivo por IP
        uisp_client = get_uisp_client()
        
        devices_data = await uisp_client.get_devices()
        device_data = None
        for device in devices_data:
            if device.get("ipAddress") == ip_address:
                device_data = device
                break
        
        if not device_data:
            raise HTTPException(status_code=404, detail=f"No se encontró dispositivo con IP {ip_address}")
        
        device_id = device_data.get("identification", {}).get("id")
        device_name = device_data.get("identification", {}).get("name")
        
        # Escanear APs vía SSH
        logger.info(f"Escaneando APs vía SSH en {device_name} ({ip_address})")
        
        ssh_client = UbiquitiSSHClient(
            default_username=ssh_username or settings.UBIQUITI_SSH_USERNAME,
            default_password=ssh_password or settings.UBIQUITI_SSH_PASSWORD
        )
        
        # Usar iwlist scan para obtener señal en dBm
        scan_result = await ssh_client.scan_nearby_aps_detailed(
            host=ip_address,
            interface="ath0",
            username=ssh_username,
            password=ssh_password
        )
        
        if not scan_result.get("success"):
            raise HTTPException(
                status_code=500, 
                detail=f"Error escaneando APs: {scan_result.get('message', 'Unknown error')}"
            )
        
        # Ordenar por señal (mejor primero)
        aps = scan_result.get("aps", [])
        aps.sort(key=lambda x: x.get("signal_dbm", -100), reverse=True)
        
        return {
            "device_id": device_id,
            "device_name": device_name,
            "ip_address": ip_address,
            "total_aps": scan_result.get("total_aps", 0),
            "aps": aps,
            "best_ap": aps[0] if aps else None,
            "method": "SSH (iwlist scan - señal en dBm)",
            "note": "APs ordenados por señal (mejor primero). signal_dbm es la señal real en dBm (ej: -54 dBm)"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze-complete/by-ip")
async def analyze_complete_by_ip(
    ip_address: str = Query(..., description="IP del dispositivo a analizar"),
    use_ai: bool = Query(True, description="Usar IA para el análisis (si False, solo patrones)"),
    signal_threshold: float = Query(-65.0, description="Umbral de señal para activar análisis de APs (dBm)"),
    enable_all_frequencies: bool = Query(True, description="Habilitar todas las frecuencias si solo tiene una activa")
):
    """
    Análisis completo unificado:
    1. Diagnóstico del dispositivo con IA (opcional)
    2. Si es station y tiene solo una frecuencia, habilita todas (opcional)
    3. Si señal débil (> threshold), escanea APs cercanos
    4. Si encuentra mejor AP nuestro, lo incluye en el análisis
    5. Retorna diagnóstico completo con recomendación de cambio de AP si aplica
    """
    from app.utils.dependencies import get_diagnostic_service, get_uisp_client, get_llm_service
    import asyncio
    
    diagnostic_service = get_diagnostic_service()
    uisp_client = get_uisp_client()
    llm_service = get_llm_service()
    
    try:
        # 1. DIAGNÓSTICO INICIAL
        logger.info(f"Iniciando análisis completo para IP {ip_address}")
        result = await diagnostic_service.diagnose_device_by_ip(ip_address, use_patterns=True)
        
        # Extraer información del dispositivo
        raw_data = result.raw_data or {}
        device_data = raw_data.get("device_data", {})
        overview = device_data.get("overview", {})
        signal_dbm = overview.get("signal")
        
        device_id = result.device_id
        device_name = device_data.get("identification", {}).get("name", "Unknown")
        role = device_data.get("identification", {}).get("role")
        
        # 2. HABILITAR TODAS LAS FRECUENCIAS SI ES NECESARIO
        frequency_change_info = None
        
        if role == "station" and enable_all_frequencies:
            logger.info("Verificando configuración wireless del station...")
            try:
                wireless_config = await uisp_client.get_device_wireless_config(device_id)
                current_frequency = wireless_config.get("frequency")
                channel_width = wireless_config.get("channelWidth")
                
                logger.info(f"Frecuencia actual: {current_frequency} MHz")
                
                # Determinar banda actual
                banda_actual = "5 GHz" if current_frequency and current_frequency >= 5000 else "2.4 GHz"
                
                # Solo informar, no intentar cambiar (API no disponible)
                if banda_actual == "2.4 GHz":
                    frequency_change_info = {
                        "cambio_realizado": False,
                        "razon": "API de configuración no disponible en esta versión de UISP",
                        "configuracion_actual": {
                            "frecuencia_mhz": current_frequency,
                            "banda": banda_actual,
                            "ancho_canal_mhz": channel_width
                        },
                        "recomendacion": "Considera cambiar a 5 GHz manualmente para mejor rendimiento",
                        "instrucciones": f"UISP Web → Devices → {device_name} → Configuration → Wireless → Cambiar a 5 GHz"
                    }
                else:
                    frequency_change_info = {
                        "cambio_realizado": False,
                        "configuracion_actual": {
                            "frecuencia_mhz": current_frequency,
                            "banda": banda_actual,
                            "ancho_canal_mhz": channel_width
                        },
                        "mensaje": "Ya está en 5 GHz (óptimo)"
                    }
            except Exception as e:
                logger.error(f"Error verificando configuración wireless: {str(e)}")
                frequency_change_info = {
                    "cambio_realizado": False,
                    "error": str(e)
                }
        
        # Preparar respuesta base
        response = {
            "diagnostico": {
                "device_id": result.device_id,
                "device_name": device_name,
                "ip_address": ip_address,
                "timestamp": result.timestamp.isoformat(),
                "status": result.status.value,
                "summary": raw_data.get("llm_analysis", {}).get("summary", ""),
                "issues": result.issues,
                "recommendations": result.recommendations,
                "confidence": result.confidence,
                "signal_dbm": signal_dbm,
                "link_score": overview.get("linkScore", {}).get("linkScore") if isinstance(overview.get("linkScore"), dict) else overview.get("linkScore")
            },
            "cambio_frecuencias": frequency_change_info,
            "optimizacion_ap": None
        }
        
        # 3. VERIFICAR SI NECESITA ANÁLISIS DE APs
        # Si la señal es débil (peor que el umbral, ej: -72 es peor que -65)
        if signal_dbm is not None and signal_dbm < signal_threshold:
            logger.info(f"Señal débil detectada ({signal_dbm} dBm < {signal_threshold} dBm). Iniciando análisis de APs...")
            
            if role == "station":
                try:
                    # 3. OBTENER APs NUESTROS
                    our_aps = await uisp_client.get_all_aps()
                    our_bssids = {ap.get("identification", {}).get("mac") for ap in our_aps}
                    
                    # 4. INICIAR ESCANEO
                    logger.info("Iniciando escaneo de APs cercanos...")
                    try:
                        await uisp_client.trigger_site_survey(device_id)
                    except Exception as e:
                        logger.warning(f"No se pudo iniciar site survey: {str(e)}")
                    
                    # 5. ESPERAR RESULTADOS
                    await asyncio.sleep(45)
                    
                    # 6. OBTENER RESULTADOS
                    survey_data = await uisp_client.get_device_site_survey(device_id)
                    
                    # 7. FORMATEAR APs
                    aps_cercanos = []
                    if isinstance(survey_data, list):
                        for ap in survey_data:
                            bssid = ap.get("bssid", "")
                            ap_info = {
                                "ssid": ap.get("ssid", "Oculto"),
                                "bssid": bssid,
                                "frecuencia_mhz": ap.get("frequency"),
                                "canal": ap.get("channel"),
                                "señal_dbm": ap.get("signal"),
                                "ruido_dbm": ap.get("noise"),
                                "es_nuestro": bssid in our_bssids
                            }
                            aps_cercanos.append(ap_info)
                    
                    # Ordenar por señal
                    aps_cercanos.sort(key=lambda x: x.get("señal_dbm", -100), reverse=True)
                    
                    # 8. BUSCAR MEJOR AP NUESTRO
                    mejor_ap_nuestro = None
                    for ap in aps_cercanos:
                        if ap["es_nuestro"] and ap.get("señal_dbm", -100) > signal_dbm:
                            mejor_ap_nuestro = ap
                            break
                    
                    # 9. ANALIZAR CON IA SI HAY MEJOR AP
                    if mejor_ap_nuestro and use_ai:
                        logger.info("Mejor AP encontrado. Analizando con IA...")
                        
                        current_ap_info = {
                            "ssid": device_data.get("attributes", {}).get("ssid"),
                            "signal_dbm": signal_dbm,
                            "frequency_mhz": overview.get("frequency"),
                            "link_score": overview.get("linkScore", {}).get("linkScore") if isinstance(overview.get("linkScore"), dict) else overview.get("linkScore")
                        }
                        
                        # Importar función de análisis
                        from app.interfaces.api.v1.endpoints.ap_optimization import analyze_aps_with_ai
                        ai_analysis = await analyze_aps_with_ai(llm_service, aps_cercanos, current_ap_info, our_aps)
                    else:
                        ai_analysis = None
                    
                    # 10. AGREGAR INFO DE OPTIMIZACIÓN
                    response["optimizacion_ap"] = {
                        "analisis_realizado": True,
                        "razon": f"Señal débil detectada ({signal_dbm} dBm)",
                        "total_aps_detectados": len(aps_cercanos),
                        "aps_nuestros": len([ap for ap in aps_cercanos if ap["es_nuestro"]]),
                        "mejor_ap_nuestro": mejor_ap_nuestro,
                        "mejora_estimada_dbm": (mejor_ap_nuestro.get("señal_dbm", 0) - signal_dbm) if mejor_ap_nuestro else 0,
                        "analisis_ia": ai_analysis,
                        "top_5_aps": aps_cercanos[:5]
                    }
                    
                    # 11. ACTUALIZAR RECOMENDACIONES SI HAY MEJOR AP
                    if mejor_ap_nuestro:
                        mejora_dbm = mejor_ap_nuestro.get("señal_dbm", 0) - signal_dbm
                        nueva_recomendacion = f"🔄 CAMBIO DE AP RECOMENDADO: Cambiar a '{mejor_ap_nuestro['ssid']}' (señal {mejor_ap_nuestro['señal_dbm']} dBm, mejora de {mejora_dbm:.1f} dBm)"
                        response["diagnostico"]["recommendations"].insert(0, nueva_recomendacion)
                        
                        # Actualizar summary si existe
                        if response["diagnostico"]["summary"]:
                            response["diagnostico"]["summary"] += f"\n\n🔄 IMPORTANTE: Se detectó un AP nuestro con mejor señal: '{mejor_ap_nuestro['ssid']}' con {mejor_ap_nuestro['señal_dbm']} dBm (mejora de {mejora_dbm:.1f} dBm). Se recomienda cambiar de AP."
                    
                except Exception as e:
                    logger.error(f"Error en análisis de APs: {str(e)}", exc_info=True)
                    response["optimizacion_ap"] = {
                        "analisis_realizado": False,
                        "error": str(e)
                    }
            else:
                logger.info(f"Dispositivo no es station (role={role}), omitiendo análisis de APs")
                response["optimizacion_ap"] = {
                    "analisis_realizado": False,
                    "razon": f"Dispositivo no es station (role={role})"
                }
        else:
            logger.info(f"Señal aceptable ({signal_dbm} dBm >= {signal_threshold} dBm), omitiendo análisis de APs")
            response["optimizacion_ap"] = {
                "analisis_realizado": False,
                "razon": f"Señal aceptable ({signal_dbm} dBm)"
            }
        
        return response
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=f"Error de conexión con UISP: {str(e)}")
    except Exception as e:
        logger.error(f"Error en análisis completo: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.get("/{device_id}/history", response_model=List[DiagnosticResponse])
async def get_device_diagnostics(
    device_id: str,
    limit: int = Query(10, ge=1, le=100),
    diagnostic_service: DiagnosticService = Depends(get_diagnostic_service)
) -> List[DiagnosticResponse]:
    try:
        results = await diagnostic_service.get_device_history(device_id, limit=limit)
        return [
            DiagnosticResponse(
                device_id=r.device_id,
                timestamp=r.timestamp,
                status=r.status.value,
                issues=r.issues,
                recommendations=r.recommendations,
                confidence=r.confidence,
                patterns_matched=r.patterns_matched,
                error_message=r.error_message
            )
            for r in results
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
