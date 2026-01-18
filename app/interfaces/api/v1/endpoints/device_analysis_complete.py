"""
Endpoint de análisis completo de dispositivo con flujo optimizado:
1. Verificar/habilitar frecuencias vía SSH
2. Site survey y filtrar mejores APs por SSID de UISP
3. Obtener métricas completas del dispositivo
4. Análisis LLM con formato natural
"""

import logging
import asyncio
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Query, HTTPException
from openai import AsyncOpenAI

from app.config.settings import settings
from app.infrastructure.ssh import UbiquitiSSHClient
from app.infrastructure.api.uisp_client import UISPClient
from app.utils.network_utils import ping_device

logger = logging.getLogger(__name__)
router = APIRouter()


async def get_uisp_client() -> UISPClient:
    """Obtener cliente UISP configurado"""
    return UISPClient(
        base_url=settings.UISP_BASE_URL,
        token=settings.UISP_TOKEN
    )


async def verify_and_enable_frequencies(
    ssh_client: UbiquitiSSHClient,
    device_ip: str,
    device_model: str,
    ssh_username: str,
    ssh_password: str
) -> Dict[str, Any]:
    """
    Paso 1: Verificar y habilitar frecuencias si es necesario
    """
    logger.info(f"📡 Paso 1: Verificando frecuencias para {device_model}")
    
    try:
        result = await ssh_client.enable_all_litebeam_frequencies(
            host=device_ip,
            device_model=device_model,
            username=ssh_username,
            password=ssh_password
        )
        
        return {
            "success": result.get("success", False),
            "action": result.get("action", "unknown"),
            "message": result.get("message", ""),
            "frequencies_configured": result.get("frequencies_after", 0)
        }
    except Exception as e:
        logger.error(f"Error verificando frecuencias: {str(e)}")
        return {
            "success": False,
            "action": "error",
            "message": str(e),
            "frequencies_configured": 0
        }


async def perform_site_survey_and_filter(
    ssh_client: UbiquitiSSHClient,
    uisp_client: UISPClient,
    device_ip: str,
    ssh_username: str,
    ssh_password: str
) -> Dict[str, Any]:
    """
    Paso 2: Site survey y filtrar mejores APs por SSID de UISP
    """
    logger.info(f"🔍 Paso 2: Site survey y filtrado de APs")
    
    try:
        # Ejecutar site survey
        survey_result = await ssh_client.scan_nearby_aps_detailed(
            host=device_ip,
            interface="ath0",
            username=ssh_username,
            password=ssh_password
        )
        
        if not survey_result.get("success"):
            return {
                "success": False,
                "message": "Site survey falló",
                "aps_found": 0,
                "best_ap": None,
                "second_best_ap": None
            }
        
        all_aps = survey_result.get("aps", [])
        logger.info(f"Site survey encontró {len(all_aps)} APs")
        
        # Obtener solo APs de UISP (no todos los dispositivos)
        uisp_aps = await uisp_client.get_all_aps()
        
        # Crear diccionario de MACs de nuestros APs
        our_ap_macs = {}
        for ap in uisp_aps:
            mac = ap.get("identification", {}).get("mac", "").upper().replace(":", "")
            ap_name = ap.get("identification", {}).get("name")
            if mac:
                our_ap_macs[mac] = {
                    "name": ap_name,
                    "device_data": ap
                }
        
        logger.info(f"APs de UISP encontrados: {len(our_ap_macs)}")
        
        # Filtrar APs del site survey que sean nuestros (por BSSID/MAC)
        our_aps = []
        for ap in all_aps:
            bssid = ap.get("bssid", "").upper().replace(":", "")
            if bssid in our_ap_macs:
                # Es nuestro AP, agregar información adicional
                ap["ap_name"] = our_ap_macs[bssid]["name"]
                
                # Obtener cantidad de clientes conectados
                ap_device = our_ap_macs[bssid]["device_data"]
                overview = ap_device.get("overview", {})
                
                client_count = (
                    overview.get("stationsCount") or
                    overview.get("linkStationsCount") or
                    overview.get("linkActiveStationsCount") or
                    overview.get("connectedStations") or
                    0
                )
                
                ap["clients_connected"] = client_count
                our_aps.append(ap)
        
        logger.info(f"APs filtrados (nuestros): {len(our_aps)}")
        
        # Ordenar por señal (mejor primero)
        our_aps.sort(key=lambda x: x.get("signal_dbm", -100), reverse=True)
        
        # Obtener mejores APs
        best_ap = our_aps[0] if len(our_aps) > 0 else None
        second_best_ap = our_aps[1] if len(our_aps) > 1 else None
        
        return {
            "success": True,
            "aps_found": len(all_aps),
            "aps_filtered": len(our_aps),
            "best_ap": best_ap,
            "second_best_ap": second_best_ap
        }
        
    except Exception as e:
        logger.error(f"Error en site survey: {str(e)}")
        return {
            "success": False,
            "message": str(e),
            "aps_found": 0,
            "best_ap": None,
            "second_best_ap": None
        }


async def get_device_metrics(
    uisp_client: UISPClient,
    device_data: Dict[str, Any],
    interfaces: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Paso 3: Obtener métricas completas del dispositivo
    """
    logger.info(f"📊 Paso 3: Obteniendo métricas del dispositivo")
    
    overview = device_data.get("overview", {})
    device_id = device_data.get("identification", {}).get("id")
    
    # Extraer EIRP y estadísticas de interfaces
    transmit_eirp = None
    rx_bytes = None
    tx_bytes = None
    current_speed = None
    plugged = False
    
    for iface in interfaces:
        iface_name = iface.get("identification", {}).get("name")
        iface_type = iface.get("identification", {}).get("type")
        
        # EIRP de interfaz wireless
        if iface_type == "wireless":
            wireless_data = iface.get("wireless", {})
            transmit_eirp = wireless_data.get("transmitEirp")
        
        # RX/TX de interfaz "main"
        if iface_name == "main":
            stats = iface.get("statistics", {})
            rx_bytes = stats.get("rxbytes")
            tx_bytes = stats.get("txbytes")
        
        # Ethernet info
        if iface_type == "ethernet":
            status_data = iface.get("status", {})
            current_speed = status_data.get("currentSpeed")
            plugged = status_data.get("plugged", False)
    
    # Convertir bytes a GB
    rx_gb = round(rx_bytes / (1024**3), 2) if rx_bytes else 0
    tx_gb = round(tx_bytes / (1024**3), 2) if tx_bytes else 0
    
    # Capacidades
    uplink_capacity_bps = overview.get("uplinkCapacity") or 0
    downlink_capacity_bps = overview.get("downlinkCapacity") or 0
    uplink_mbps = round(uplink_capacity_bps / 1000000, 1) if uplink_capacity_bps else 0
    downlink_mbps = round(downlink_capacity_bps / 1000000, 1) if downlink_capacity_bps else 0
    
    # Uptime
    uptime = overview.get("uptime", 0)
    uptime_days = uptime // 86400
    uptime_hours = (uptime % 86400) // 3600
    uptime_minutes = (uptime % 3600) // 60
    
    # Ethernet speed desde overview.mainInterfaceSpeed (más confiable)
    ethernet_speed = overview.get("mainInterfaceSpeed", {}).get("availableSpeed", "auto")
    ethernet_connected = plugged and current_speed is not None
    
    return {
        "device_name": device_data.get("identification", {}).get("name"),
        "device_model": device_data.get("identification", {}).get("model"),
        "signal": {
            "current": overview.get("signal"),
            "max": overview.get("signalMax"),
            "remote_max": overview.get("remoteSignalMax")
        },
        "cpu": overview.get("cpu"),
        "ram": overview.get("ram"),
        "uptime": {
            "seconds": uptime,
            "days": uptime_days,
            "hours": uptime_hours,
            "minutes": uptime_minutes,
            "formatted": f"{uptime_days} días, {uptime_hours} horas, {uptime_minutes} minutos"
        },
        "ethernet": {
            "speed": ethernet_speed,
            "plugged": plugged,
            "connected": ethernet_connected
        },
        "wireless": {
            "frequency": overview.get("frequency"),
            "channel_width": overview.get("channelWidth"),
            "transmit_power": overview.get("transmitPower"),
            "antenna_gain": overview.get("antenna", {}).get("gain"),
            "eirp": transmit_eirp,
            "uplink_mbps": uplink_mbps,
            "downlink_mbps": downlink_mbps
        },
        "traffic": {
            "rx_gb": rx_gb,
            "tx_gb": tx_gb
        },
        "link_quality": {
            "score": overview.get("linkScore", {}).get("score"),
            "uplink_score": overview.get("linkScore", {}).get("uplinkScore"),
            "downlink_score": overview.get("linkScore", {}).get("downlinkScore"),
            "airtime": overview.get("linkScore", {}).get("airTime")
        },
        "current_ap": {
            "name": device_data.get("identification", {}).get("name"),
            "clients": overview.get("stationsCount", 0)
        }
    }


async def generate_llm_analysis(
    metrics: Dict[str, Any],
    frequency_check: Dict[str, Any],
    survey_result: Dict[str, Any],
    ping_result: Dict[str, Any]
) -> str:
    """
    Paso 4: Generar análisis LLM con formato natural
    """
    logger.info(f"🤖 Paso 4: Generando análisis con LLM")
    
    # Construir prompt con todos los datos
    device_name = metrics["device_name"]
    device_model = metrics["device_model"]
    cpu = metrics["cpu"]
    ram = metrics["ram"]
    uptime_str = metrics["uptime"]["formatted"]
    uptime_days = metrics["uptime"]["days"]
    
    # Datos de ping
    ping_reachable = ping_result.get("reachable", False)
    ping_latency = ping_result.get("avg_latency_ms")
    ping_loss = ping_result.get("packet_loss", 0)
    
    signal = metrics["signal"]["current"]
    frequency = metrics["wireless"]["frequency"]
    channel_width = metrics["wireless"]["channel_width"]
    tx_power = metrics["wireless"]["transmit_power"]
    antenna_gain = metrics["wireless"]["antenna_gain"]
    
    uplink = metrics["wireless"]["uplink_mbps"]
    downlink = metrics["wireless"]["downlink_mbps"]
    
    ethernet = metrics["ethernet"]["speed"]
    ethernet_connected = "conectada" if metrics["ethernet"]["connected"] else "desconectada"
    
    rx_gb = metrics["traffic"]["rx_gb"]
    tx_gb = metrics["traffic"]["tx_gb"]
    
    link_score = metrics["link_quality"]["score"]
    uplink_score = metrics["link_quality"]["uplink_score"]
    downlink_score = metrics["link_quality"]["downlink_score"]
    
    current_ap_clients = metrics["current_ap"]["clients"]
    
    # Información de frecuencias
    freq_info = ""
    if frequency_check["success"]:
        if frequency_check["action"] == "configured":
            freq_info = f"\n✅ Frecuencias configuradas: {frequency_check['frequencies_configured']} canales habilitados"
        elif frequency_check["action"] == "skipped":
            freq_info = f"\n✅ Frecuencias ya configuradas: {frequency_check['frequencies_configured']} canales disponibles"
    
    # Detectar problemas específicos
    problems = []
    
    # 1. Uptime bajo (menos de 1 día)
    if uptime_days < 1:
        problems.append(f"⚠️ Uptime bajo: {uptime_str} (reinicio reciente)")
    
    # 2. LAN en 10 Mbps (problema)
    if "10 Mbps" in ethernet:
        problems.append(f"🔴 LAN limitada a 10 Mbps (debería ser 100 Mbps o más)")
    elif not ethernet_connected:
        problems.append(f"⚠️ Ethernet desconectada")
    
    # 3. Capacidad baja (< 30 Mbps downlink o < 15 Mbps uplink)
    if downlink < 30 or uplink < 15:
        problems.append(f"🔴 Capacidad baja: {downlink}/{uplink} Mbps (mínimo recomendado: 30/15 Mbps)")
    
    # 4. Link quality bajo (< 0.7)
    if link_score and link_score < 0.7:
        problems.append(f"⚠️ Link Score bajo: {link_score} (debería ser > 0.7)")
    
    # 5. Consumo alto de datos (> 50 GB RX o > 20 GB TX)
    if rx_gb > 50 or tx_gb > 20:
        problems.append(f"📊 Alto consumo: {rx_gb}/{tx_gb} GB (RX/TX)")
    
    # Información de APs disponibles
    ap_info = ""
    best_ap = survey_result.get("best_ap")
    second_best = survey_result.get("second_best_ap")
    
    if best_ap:
        best_signal = best_ap.get("signal_dbm")
        best_ssid = best_ap.get("ssid")
        best_clients = best_ap.get("clients_connected", 0)
        signal_diff = best_signal - signal if signal else 0
        
        # Determinar si recomendar cambio
        recommend_change = False
        reason = ""
        
        if signal_diff >= 5 and best_clients < current_ap_clients:
            recommend_change = True
            reason = f"Señal {signal_diff:+d} dBm mejor y MENOS clientes ({best_clients} vs {current_ap_clients})"
        elif signal_diff >= 10:
            recommend_change = True
            reason = f"Señal {signal_diff:+d} dBm mejor"
        elif signal_diff >= 5 and best_clients <= current_ap_clients + 3:
            recommend_change = True
            reason = f"Señal {signal_diff:+d} dBm mejor y carga similar ({best_clients} vs {current_ap_clients} clientes)"
        
        if recommend_change:
            ap_info = f"\n🔄 CAMBIO DE AP RECOMENDADO:\n- Cambiar a: {best_ssid}\n- Razón: {reason}\n- Señal: {best_signal} dBm @ {best_ap.get('frequency_mhz')} MHz"
            
            if second_best:
                second_signal = second_best.get("signal_dbm")
                second_ssid = second_best.get("ssid")
                second_clients = second_best.get("clients_connected", 0)
                ap_info += f"\n- Alternativa: {second_ssid} ({second_signal} dBm, {second_clients} clientes)"
        else:
            ap_info = f"\n✅ AP ACTUAL ÓPTIMO:\n- Mejor AP disponible: {best_ssid} ({best_signal} dBm, {best_clients} clientes)\n- Diferencia: {signal_diff:+d} dBm\n- No se recomienda cambio (carga o señal no justifican el cambio)"
    
    problems_text = "\n".join(problems) if problems else "✅ Sin problemas detectados"

    prompt = f"""
    Actúa como operador NOC de primer nivel de un ISP.

    Analiza el siguiente dispositivo y responde de forma SIMPLE, DIRECTA y OPERATIVA.
    Evita explicaciones largas o teóricas.

    DISPOSITIVO:
    - Nombre: {device_name}
    - Modelo: {device_model}
    - Uptime: {uptime_str}

    PING:
    - Latencia promedio: {ping_latency} ms
    - Pérdida de paquetes: {ping_loss}%

    LAN:
    - Ethernet: {ethernet}

    WIRELESS / AP:
    - Señal: {signal} dBm
    - Frecuencia: {frequency} MHz
    - Capacidad: {downlink}/{uplink} Mbps
    - Clientes conectados: {current_ap_clients}
    - Link Score: {link_score}

    TRÁFICO:
    - RX/TX: {rx_gb}/{tx_gb} GB

    PROBLEMAS DETECTADOS:
    {problems_text}

    INFO ADICIONAL:
    {ap_info}

    FORMATO DE RESPUESTA (OBLIGATORIO):

    1️⃣ CONECTIVIDAD (PING):
    - Latencia: {ping_latency} ms → Buena / Aceptable / Alta
    - Pérdida: {ping_loss}% → OK / Problema

    2️⃣ ESTADO GENERAL:
    - Uptime: {uptime_str}
    - Estado: OK / DEGRADADO / CRÍTICO + motivo principal

    3️⃣ LAN:
    - Velocidad: {ethernet}
    - ¿Es un problema? (Sí / No)

    4️⃣ WIRELESS / AP:
    - Señal: {signal} dBm → Buena / Regular / Mala
    - Capacidad: {downlink}/{uplink} Mbps vs {current_ap_clients} clientes → Suficiente / Justa / Saturada
    - AP actual adecuado: Sí / No

    5️⃣ APS ALTERNATIVOS:
    {ap_info}
    - Si hay mejor AP: menciona SSID, mejora de señal, y comparación de clientes
    - Recomienda cambio solo si mejora señal Y tiene menos/similar clientes

    6️⃣ RECOMENDACIÓN NOC (CLARA Y DIRECTA):
    - Cambiar a AP [nombre] (mejor señal y menos clientes)
    - Mantener AP actual (óptimo)
    - Revisar cable LAN (velocidad limitada)
    - Escalar a técnico de campo
    - Solo monitorear

    Sé específico con nombres de APs y razones claras.
    """

    try:
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        
        response = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": "Eres técnico de NOC. Resumen MUY BREVE (2-3 párrafos). Enfócate en problemas detectados y da recomendación clara y directa."},
                {"role": "user", "content": prompt}
            ],
            max_completion_tokens=500
        )
        
        if response.choices and len(response.choices) > 0:
            summary = response.choices[0].message.content.strip()
            logger.info(f"✅ Análisis LLM generado: {len(summary)} caracteres")
            return summary
        else:
            logger.warning("⚠️ LLM no generó respuesta")
            return "No se pudo generar el análisis"
            
    except Exception as e:
        logger.error(f"Error generando análisis LLM: {str(e)}")
        return f"Error generando análisis: {str(e)}"


@router.post("/analyze-device-complete")
async def analyze_device_complete(
    ip_address: str = Query(..., description="IP del dispositivo a analizar"),
    ssh_username: Optional[str] = Query(None, description="Usuario SSH (opcional, usa default del config)"),
    ssh_password: Optional[str] = Query(None, description="Password SSH (opcional, usa default del config)")
):
    """
    Análisis completo de dispositivo con flujo optimizado:
    
    1. Verificar/habilitar frecuencias vía SSH
    2. Site survey y filtrar mejores APs por SSID de UISP
    3. Obtener métricas completas del dispositivo
    4. Análisis LLM con formato natural
    
    Returns:
        Análisis completo con resumen LLM y datos estructurados
    """
    logger.info(f"🚀 Iniciando análisis completo para dispositivo {ip_address}")
    
    # Usar credenciales por defecto si no se proporcionan
    ssh_user = ssh_username or settings.UBIQUITI_SSH_USERNAME
    ssh_pass = ssh_password or settings.UBIQUITI_SSH_PASSWORD
    
    try:
        # Inicializar clientes
        uisp_client = await get_uisp_client()
        ssh_client = UbiquitiSSHClient()
        
        # Buscar dispositivo en UISP
        logger.info(f"🔍 Buscando dispositivo {ip_address} en UISP")
        devices = await uisp_client.get_devices()
        device_data = None
        
        for device in devices:
            if device.get("ipAddress") == ip_address:
                device_data = device
                break
        
        if not device_data:
            raise HTTPException(status_code=404, detail=f"Dispositivo {ip_address} no encontrado en UISP")
        
        device_id = device_data.get("identification", {}).get("id")
        device_model = device_data.get("identification", {}).get("model")
        device_name = device_data.get("identification", {}).get("name")
        
        logger.info(f"✅ Dispositivo encontrado: {device_name} ({device_model})")
        
        # Obtener interfaces
        interfaces = await uisp_client.get_device_interfaces(device_id)
        
        # PASO 0: Ping al dispositivo
        logger.info(f"🏓 Paso 0: Ping al dispositivo")
        ping_result = await ping_device(ip_address, count=5)
        
        # PASO 1: Verificar/habilitar frecuencias
        frequency_check = await verify_and_enable_frequencies(
            ssh_client=ssh_client,
            device_ip=ip_address,
            device_model=device_model,
            ssh_username=ssh_user,
            ssh_password=ssh_pass
        )
        
        # Si se configuraron frecuencias, esperar a que el softrestart aplique los cambios
        if frequency_check.get("action") == "configured":
            logger.info(f"⏳ Esperando 15 segundos para que el dispositivo aplique las nuevas frecuencias...")
            await asyncio.sleep(15)
            logger.info(f"✅ Continuando con site survey")
        
        # PASO 2: Site survey y filtrar APs
        survey_result = await perform_site_survey_and_filter(
            ssh_client=ssh_client,
            uisp_client=uisp_client,
            device_ip=ip_address,
            ssh_username=ssh_user,
            ssh_password=ssh_pass
        )
        
        # PASO 3: Obtener métricas del dispositivo
        metrics = await get_device_metrics(
            uisp_client=uisp_client,
            device_data=device_data,
            interfaces=interfaces
        )
        
        # PASO 4: Generar análisis LLM
        llm_analysis = await generate_llm_analysis(
            metrics=metrics,
            frequency_check=frequency_check,
            survey_result=survey_result,
            ping_result=ping_result
        )
        
        # Construir respuesta completa
        return {
            "success": True,
            "device": {
                "name": device_name,
                "model": device_model,
                "ip": ip_address
            },
            "analysis": {
                "llm_summary": llm_analysis,
                "ping": ping_result,
                "metrics": metrics,
                "frequency_check": frequency_check,
                "site_survey": {
                    "success": survey_result.get("success"),
                    "aps_found": survey_result.get("aps_found", 0),
                    "aps_filtered": survey_result.get("aps_filtered", 0),
                    "best_ap": survey_result.get("best_ap"),
                    "second_best_ap": survey_result.get("second_best_ap")
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error en análisis completo: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error en análisis: {str(e)}")
