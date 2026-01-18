from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from typing import Dict, Any, List, Optional
import asyncio
import logging
from datetime import datetime
from app.utils.dependencies import get_uisp_client, get_llm_service
from app.infrastructure.api.uisp_client import UISPClient
from app.infrastructure.llm.llm_service import LLMService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ap-optimization", tags=["ap-optimization"])


async def wait_for_device_reconnection(uisp_client: UISPClient, device_id: str, max_wait_seconds: int = 180) -> bool:
    """Espera a que el dispositivo se reconecte después de un cambio de configuración"""
    start_time = datetime.now()
    
    while (datetime.now() - start_time).total_seconds() < max_wait_seconds:
        try:
            device_data = await uisp_client.get_device(device_id)
            status = device_data.get("overview", {}).get("status")
            
            if status == "active":
                logger.info(f"Device {device_id} reconnected successfully")
                return True
                
        except Exception as e:
            logger.debug(f"Device not yet reconnected: {str(e)}")
        
        await asyncio.sleep(10)  # Esperar 10 segundos entre intentos
    
    return False


async def analyze_aps_with_ai(
    llm_service: LLMService,
    aps_data: List[Dict[str, Any]],
    current_ap_info: Dict[str, Any],
    our_aps: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Analiza los APs detectados con IA para recomendar el mejor"""
    
    # Identificar cuáles son nuestros APs
    our_bssids = {ap.get("identification", {}).get("mac") for ap in our_aps}
    
    for ap in aps_data:
        ap["es_nuestro"] = ap.get("bssid") in our_bssids
        ap["es_competencia"] = not ap["es_nuestro"]
    
    prompt = f"""Analiza estos APs detectados y recomienda el mejor para conectarse.

AP ACTUAL:
- SSID: {current_ap_info.get('ssid')}
- Señal: {current_ap_info.get('signal_dbm')} dBm
- Frecuencia: {current_ap_info.get('frequency_mhz')} MHz
- Link Score: {current_ap_info.get('link_score')}

APs DETECTADOS:
{aps_data}

CRITERIOS DE EVALUACIÓN:
1. Señal más fuerte (> -70 dBm es bueno, > -60 dBm es excelente)
2. Menos interferencia (diferencia señal-ruido)
3. Canal menos saturado
4. Priorizar APs nuestros (es_nuestro=True) sobre competencia
5. Frecuencia compatible

RESPONDE EN ESPAÑOL con este formato JSON:
{{
    "recomendacion": "Descripción clara de qué hacer",
    "mejor_ap": {{
        "ssid": "nombre",
        "bssid": "MAC",
        "razon": "Por qué es mejor",
        "es_nuestro": true/false
    }},
    "cambiar_ap": true/false,
    "mejora_estimada_dbm": 5,
    "advertencias": ["Lista de advertencias si las hay"]
}}"""

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=llm_service.api_key)
        
        response = await client.chat.completions.create(
            model=llm_service.model,
            messages=[
                {"role": "system", "content": "Eres un experto en optimización de enlaces wireless Ubiquiti."},
                {"role": "user", "content": prompt}
            ],
            max_completion_tokens=600
        )
        
        import json
        analysis = json.loads(response.choices[0].message.content)
        return analysis
        
    except Exception as e:
        logger.error(f"Error analyzing APs with AI: {str(e)}")
        return {
            "recomendacion": "No se pudo analizar con IA",
            "cambiar_ap": False,
            "advertencias": [str(e)]
        }


@router.post("/change-frequency-test/by-ip")
async def change_frequency_test_by_ip(
    ip_address: str = Query(..., description="IP del dispositivo station"),
    frequency_mhz: int = Query(..., description="Frecuencia en MHz (ej: 5840)"),
    rollback_seconds: int = Query(300, description="Segundos antes de revertir automáticamente (default: 300 = 5 min)"),
    interface: str = Query("ath0", description="Interfaz wireless (default: ath0)"),
    ssh_username: Optional[str] = Query(None, description="Usuario SSH"),
    ssh_password: Optional[str] = Query(None, description="Contraseña SSH")
):
    """
    Cambia la frecuencia en TEST MODE con rollback automático.
    
    Si no confirmas los cambios en el tiempo especificado, se revertirán automáticamente.
    Esto previene que pierdas acceso al dispositivo por un cambio incorrecto.
    """
    from app.config.settings import settings
    from app.infrastructure.ssh import UbiquitiSSHClient
    
    uisp_client = get_uisp_client()
    
    try:
        # Buscar dispositivo
        devices_data = await uisp_client.get_devices()
        device_data = None
        
        for device in devices_data:
            if device.get("ipAddress") == ip_address:
                device_data = device
                break
        
        if not device_data:
            raise HTTPException(status_code=404, detail=f"No se encontró dispositivo con IP {ip_address}")
        
        device_name = device_data.get("identification", {}).get("name")
        device_model = device_data.get("identification", {}).get("model", "Unknown")
        
        # Verificar frecuencia válida
        from app.config.device_frequencies import get_frequencies_for_model
        available_frequencies = get_frequencies_for_model(device_model)
        
        if frequency_mhz not in available_frequencies:
            raise HTTPException(
                status_code=400,
                detail=f"Frecuencia {frequency_mhz} MHz no válida para {device_model}"
            )
        
        # Cambiar frecuencia en Test Mode
        ssh_client = UbiquitiSSHClient(
            default_username=ssh_username or settings.UBIQUITI_SSH_USERNAME,
            default_password=ssh_password or settings.UBIQUITI_SSH_PASSWORD
        )
        
        result = await ssh_client.change_frequency_test_mode(
            host=ip_address,
            frequency_mhz=frequency_mhz,
            rollback_seconds=rollback_seconds,
            interface=interface,
            username=ssh_username,
            password=ssh_password
        )
        
        if result.get("success"):
            return {
                **result,
                "device_name": device_name,
                "device_model": device_model
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("message"))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en Test Mode: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/confirm-test-mode/by-ip")
async def confirm_test_mode_by_ip(
    ip_address: str = Query(..., description="IP del dispositivo"),
    ssh_username: Optional[str] = Query(None, description="Usuario SSH"),
    ssh_password: Optional[str] = Query(None, description="Contraseña SSH")
):
    """
    Confirma los cambios realizados en Test Mode.
    Desactiva el rollback automático y mantiene los cambios permanentemente.
    """
    from app.config.settings import settings
    from app.infrastructure.ssh import UbiquitiSSHClient
    
    try:
        ssh_client = UbiquitiSSHClient(
            default_username=ssh_username or settings.UBIQUITI_SSH_USERNAME,
            default_password=ssh_password or settings.UBIQUITI_SSH_PASSWORD
        )
        
        result = await ssh_client.confirm_test_mode(
            host=ip_address,
            username=ssh_username,
            password=ssh_password
        )
        
        if result.get("success"):
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get("message"))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error confirmando Test Mode: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cancel-test-mode/by-ip")
async def cancel_test_mode_by_ip(
    ip_address: str = Query(..., description="IP del dispositivo"),
    ssh_username: Optional[str] = Query(None, description="Usuario SSH"),
    ssh_password: Optional[str] = Query(None, description="Contraseña SSH")
):
    """
    Cancela Test Mode y revierte los cambios inmediatamente.
    El dispositivo se reiniciará con la configuración anterior.
    """
    from app.config.settings import settings
    from app.infrastructure.ssh import UbiquitiSSHClient
    
    try:
        ssh_client = UbiquitiSSHClient(
            default_username=ssh_username or settings.UBIQUITI_SSH_USERNAME,
            default_password=ssh_password or settings.UBIQUITI_SSH_PASSWORD
        )
        
        result = await ssh_client.cancel_test_mode(
            host=ip_address,
            username=ssh_username,
            password=ssh_password
        )
        
        if result.get("success"):
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get("message"))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelando Test Mode: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/enable-litebeam-frequencies/by-ip")
async def enable_litebeam_frequencies_by_ip(
    ip_address: str = Query(..., description="IP del dispositivo"),
    ssh_username: Optional[str] = Query(None, description="Usuario SSH"),
    ssh_password: Optional[str] = Query(None, description="Contraseña SSH")
):
    """
    Habilita todas las frecuencias disponibles para LiteBeam AC.
    Solo aplica cambios si:
    1. El dispositivo es LiteBeam AC
    2. No tiene todas las frecuencias configuradas
    
    Si ya tiene todas las frecuencias, no hace nada.
    """
    from app.config.settings import settings
    from app.infrastructure.ssh import UbiquitiSSHClient
    
    uisp_client = get_uisp_client()
    
    try:
        # Buscar dispositivo por IP
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
        device_model = device_data.get("identification", {}).get("model", "Unknown")
        
        # Habilitar frecuencias vía SSH
        ssh_client = UbiquitiSSHClient(
            default_username=ssh_username or settings.UBIQUITI_SSH_USERNAME,
            default_password=ssh_password or settings.UBIQUITI_SSH_PASSWORD
        )
        
        result = await ssh_client.enable_all_litebeam_frequencies(
            host=ip_address,
            device_model=device_model,
            username=ssh_username,
            password=ssh_password
        )
        
        # Agregar información del dispositivo a la respuesta
        result["device_id"] = device_id
        result["device_name"] = device_name
        result["ip_address"] = ip_address
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error habilitando frecuencias: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/debug-frequency-fields/by-ip")
async def debug_frequency_fields_by_ip(
    ip_address: str = Query(..., description="IP del dispositivo"),
    ssh_username: Optional[str] = Query(None, description="Usuario SSH"),
    ssh_password: Optional[str] = Query(None, description="Contraseña SSH")
):
    """
    Endpoint temporal para ver todos los campos relacionados con frecuencias en /tmp/system.cfg
    """
    from app.config.settings import settings
    from app.infrastructure.ssh import UbiquitiSSHClient
    
    try:
        ssh_client = UbiquitiSSHClient(
            default_username=ssh_username or settings.UBIQUITI_SSH_USERNAME,
            default_password=ssh_password or settings.UBIQUITI_SSH_PASSWORD
        )
        
        conn = await ssh_client.connect(ip_address, ssh_username, ssh_password)
        
        # Ver todos los campos relacionados con frecuencias
        result = await ssh_client.execute_command(conn, "grep -E 'freq|scan' /tmp/system.cfg")
        
        conn.close()
        await conn.wait_closed()
        
        return {
            "success": True,
            "ip_address": ip_address,
            "all_frequency_fields": result["stdout"],
            "fields_list": result["stdout"].split("\n") if result["stdout"] else []
        }
        
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/change-frequency/by-ip")
async def change_frequency_by_ip(
    ip_address: str = Query(..., description="IP del dispositivo station"),
    frequency_mhz: int = Query(..., description="Frecuencia en MHz (ej: 5840)"),
    interface: str = Query("ath0", description="Interfaz wireless (default: ath0)"),
    ssh_username: Optional[str] = Query(None, description="Usuario SSH"),
    ssh_password: Optional[str] = Query(None, description="Contraseña SSH")
):
    """
    Cambia la frecuencia del dispositivo usando iwconfig vía SSH.
    
    Ejemplo: frequency_mhz=5840 para 5.840 GHz
    """
    from app.config.settings import settings
    from app.infrastructure.ssh import UbiquitiSSHClient
    
    uisp_client = get_uisp_client()
    
    try:
        # 1. Buscar dispositivo por IP
        logger.info(f"Buscando dispositivo con IP {ip_address}")
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
        device_model = device_data.get("identification", {}).get("model", "Unknown")
        
        # 2. Verificar que la frecuencia sea válida para el modelo
        from app.config.device_frequencies import get_frequencies_for_model
        available_frequencies = get_frequencies_for_model(device_model)
        
        if frequency_mhz not in available_frequencies:
            return {
                "success": False,
                "message": f"Frecuencia {frequency_mhz} MHz no es válida para {device_model}",
                "device_model": device_model,
                "frecuencia_solicitada": frequency_mhz,
                "frecuencias_validas": available_frequencies,
                "sugerencia": f"Usa una frecuencia entre {min(available_frequencies)} y {max(available_frequencies)} MHz"
            }
        
        # 3. Cambiar frecuencia vía SSH
        logger.info(f"Cambiando frecuencia de {device_name} a {frequency_mhz} MHz vía SSH")
        
        ssh_client = UbiquitiSSHClient(
            default_username=ssh_username or settings.UBIQUITI_SSH_USERNAME,
            default_password=ssh_password or settings.UBIQUITI_SSH_PASSWORD
        )
        
        result = await ssh_client.change_frequency(
            host=ip_address,
            frequency_mhz=frequency_mhz,
            interface=interface,
            username=ssh_username,
            password=ssh_password
        )
        
        if result.get("success"):
            return {
                "success": True,
                "message": result.get("message"),
                "device_id": device_id,
                "device_name": device_name,
                "device_model": device_model,
                "ip_address": ip_address,
                "frecuencia_anterior": "Ver en UISP",
                "frecuencia_nueva_mhz": frequency_mhz,
                "frecuencia_nueva_ghz": frequency_mhz / 1000.0,
                "interface": interface,
                "ssh_commands": result.get("commands_executed", [])
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("message", "Error cambiando frecuencia"))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cambiando frecuencia: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/enable-all-frequencies/by-ip")
async def enable_all_frequencies_by_ip(
    ip_address: str = Query(..., description="IP del dispositivo station"),
    use_ssh: bool = Query(True, description="Usar SSH para configurar directamente el dispositivo"),
    wait_for_reconnection: bool = Query(True, description="Esperar a que el dispositivo se reconecte"),
    ssh_username: Optional[str] = Query(None, description="Usuario SSH (usa default si no se especifica)"),
    ssh_password: Optional[str] = Query(None, description="Contraseña SSH (usa default si no se especifica)")
):
    """
    Habilita todas las frecuencias disponibles en un station para escaneo completo.
    
    Métodos:
    1. SSH (recomendado): Conecta directamente al dispositivo y configura todas las frecuencias
    2. Manual: Proporciona instrucciones para hacerlo desde UISP web
    """
    from app.config.settings import settings
    from app.infrastructure.ssh import UbiquitiSSHClient
    
    uisp_client = get_uisp_client()
    
    try:
        # 1. Buscar dispositivo por IP
        logger.info(f"Buscando dispositivo con IP {ip_address}")
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
        device_model = device_data.get("identification", {}).get("model", "Unknown")
        role = device_data.get("identification", {}).get("role")
        
        if not device_id:
            raise HTTPException(status_code=400, detail="Dispositivo sin ID válido")
        
        if role != "station":
            raise HTTPException(status_code=400, detail=f"El dispositivo debe ser un station, no {role}")
        
        # 2. Obtener configuración wireless actual
        logger.info(f"Obteniendo configuración wireless de {device_name} (modelo: {device_model})")
        wireless_config = await uisp_client.get_device_wireless_config(device_id)
        current_frequency = wireless_config.get("frequency")
        channel_width = wireless_config.get("channelWidth")
        signal = wireless_config.get("signal")
        
        banda_actual = "5 GHz" if current_frequency and current_frequency >= 5000 else "2.4 GHz"
        
        # Obtener frecuencias disponibles para este modelo
        from app.config.device_frequencies import get_frequencies_for_model, get_frequency_range_string
        available_frequencies = get_frequencies_for_model(device_model)
        freq_range = get_frequency_range_string(available_frequencies)
        
        logger.info(f"Modelo {device_model} soporta {len(available_frequencies)} frecuencias: {freq_range}")
        
        # 3. Intentar configurar vía SSH si está habilitado
        if use_ssh:
            logger.info(f"Intentando configurar frecuencias vía SSH en {ip_address}")
            
            ssh_client = UbiquitiSSHClient(
                default_username=ssh_username or settings.UBIQUITI_SSH_USERNAME,
                default_password=ssh_password or settings.UBIQUITI_SSH_PASSWORD
            )
            
            try:
                # Habilitar todas las frecuencias vía SSH según el modelo
                result = await ssh_client.enable_all_frequencies(
                    host=ip_address,
                    device_model=device_model,
                    username=ssh_username,
                    password=ssh_password
                )
                
                if result.get("success"):
                    response = {
                        "message": f"Dispositivo {device_name} verificado vía SSH",
                        "device_id": device_id,
                        "device_name": device_name,
                        "device_model": device_model,
                        "ip_address": ip_address,
                        "metodo": "SSH directo",
                        "configuracion_actual": {
                            "frecuencia_mhz": current_frequency,
                            "banda": banda_actual,
                            "ancho_canal_mhz": channel_width
                        },
                        "frecuencias_disponibles": {
                            "total": len(available_frequencies),
                            "rango": freq_range,
                            "lista_completa": available_frequencies,
                            "minima_mhz": min(available_frequencies) if available_frequencies else None,
                            "maxima_mhz": max(available_frequencies) if available_frequencies else None
                        },
                        "verificacion_realizada": True,
                        "requires_reboot": False,
                        "ssh_output": result.get("commands_executed", []),
                        "nota": result.get("nota", "Dispositivo listo para site survey")
                    }
                    
                    return response
                else:
                    logger.warning(f"SSH falló: {result.get('error')}. Retornando instrucciones manuales.")
                    use_ssh = False  # Fallback a instrucciones manuales
                    
            except Exception as e:
                logger.error(f"Error usando SSH: {str(e)}. Retornando instrucciones manuales.")
                use_ssh = False  # Fallback a instrucciones manuales
        
        # 4. Si SSH no está habilitado o falló, retornar instrucciones manuales
        return {
            "message": "Configuración manual requerida" if not use_ssh else "SSH no disponible, configuración manual requerida",
            "device_id": device_id,
            "device_name": device_name,
            "device_model": device_model,
            "ip_address": ip_address,
            "metodo": "Manual",
            "configuracion_actual": {
                "frecuencia_mhz": current_frequency,
                "banda": banda_actual,
                "ancho_canal_mhz": channel_width,
                "señal_dbm": signal
            },
            "frecuencias_disponibles": {
                "total": len(available_frequencies),
                "rango": freq_range,
                "lista_completa": available_frequencies,
                "minima_mhz": min(available_frequencies) if available_frequencies else None,
                "maxima_mhz": max(available_frequencies) if available_frequencies else None,
                "nota": f"El modelo {device_model} soporta {len(available_frequencies)} frecuencias diferentes"
            },
            "cambio_realizado": False,
            "razon": "SSH no disponible o deshabilitado",
            "instrucciones_manuales": {
                "opcion_1_ssh": f"ssh {settings.UBIQUITI_SSH_USERNAME}@{ip_address} y ejecutar: mca-config set wireless.1.scan.channels {freq_range}",
                "opcion_2_web": {
                    "paso_1": f"Accede a UISP web: {uisp_client.base_url}",
                    "paso_2": f"Ve a Devices → {device_name}",
                    "paso_3": "Click en Configuration → Wireless",
                    "paso_4": f"Habilita todas las frecuencias disponibles ({freq_range})",
                    "paso_5": "Guarda y espera reconexión (1-3 min)"
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error habilitando frecuencias: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/optimize-by-ip")
async def optimize_ap_by_ip(
    ip_address: str = Query(..., description="IP del dispositivo station a optimizar"),
    auto_apply: bool = Query(False, description="Aplicar cambios automáticamente si se encuentra mejor AP"),
    background_tasks: BackgroundTasks = None
):
    """
    Flujo completo de optimización de AP:
    1. Verifica frecuencias activas del station
    2. Activa todas las frecuencias si solo hay una
    3. Espera reconexión (1-3 min)
    4. Escanea APs cercanos
    5. Analiza con IA para recomendar mejor AP
    6. Verifica si los APs son nuestros o de la competencia
    """
    
    uisp_client = get_uisp_client()
    llm_service = get_llm_service()
    
    try:
        # 1. Buscar dispositivo por IP
        logger.info(f"Buscando dispositivo con IP {ip_address}")
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
        
        if not device_id:
            raise HTTPException(status_code=400, detail="Dispositivo sin ID válido")
        
        # Verificar que sea un station
        role = device_data.get("identification", {}).get("role")
        if role != "station":
            raise HTTPException(status_code=400, detail=f"El dispositivo debe ser un station, no {role}")
        
        logger.info(f"Dispositivo encontrado: {device_name} ({device_id})")
        
        # 2. Obtener información actual del AP conectado
        overview = device_data.get("overview", {})
        current_ap_info = {
            "ssid": device_data.get("attributes", {}).get("ssid"),
            "signal_dbm": overview.get("signal"),
            "frequency_mhz": overview.get("frequency"),
            "link_score": overview.get("linkScore", {}).get("linkScore") if isinstance(overview.get("linkScore"), dict) else overview.get("linkScore")
        }
        
        # 3. Obtener todos nuestros APs para comparación
        logger.info("Obteniendo lista de APs propios")
        our_aps = await uisp_client.get_all_aps()
        
        # 4. Iniciar escaneo de APs
        logger.info(f"Iniciando escaneo de APs cercanos en {device_name}")
        
        notification = {
            "timestamp": datetime.now().isoformat(),
            "device_name": device_name,
            "device_ip": ip_address,
            "mensaje": f"Iniciando optimización de AP para {device_name}. El equipo puede desconectarse brevemente.",
            "pasos": [
                "1. Escaneando APs cercanos...",
                "2. Esperando resultados del escaneo (30-60 seg)",
                "3. Analizando con IA para encontrar mejor AP",
                "4. Verificando si APs son propios o competencia"
            ]
        }
        
        # Disparar escaneo
        try:
            await uisp_client.trigger_site_survey(device_id)
            logger.info("Escaneo de site survey iniciado")
        except Exception as e:
            logger.warning(f"No se pudo iniciar site survey: {str(e)}")
        
        # 5. Esperar a que se complete el escaneo (30-60 segundos)
        logger.info("Esperando 45 segundos para que se complete el escaneo...")
        await asyncio.sleep(45)
        
        # 6. Obtener resultados del escaneo
        logger.info("Obteniendo resultados del escaneo")
        try:
            survey_data = await uisp_client.get_device_site_survey(device_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"No se pudieron obtener resultados del escaneo: {str(e)}")
        
        # 7. Formatear APs detectados
        aps_cercanos = []
        if isinstance(survey_data, list):
            for ap in survey_data:
                ap_info = {
                    "ssid": ap.get("ssid", "Oculto"),
                    "bssid": ap.get("bssid", ""),
                    "frecuencia_mhz": ap.get("frequency"),
                    "canal": ap.get("channel"),
                    "ancho_canal_mhz": ap.get("channelWidth"),
                    "señal_dbm": ap.get("signal"),
                    "ruido_dbm": ap.get("noise"),
                    "calidad": ap.get("quality"),
                }
                aps_cercanos.append(ap_info)
        
        aps_cercanos.sort(key=lambda x: x.get("señal_dbm", -100), reverse=True)
        
        # 8. Analizar con IA
        logger.info("Analizando APs con IA...")
        ai_analysis = await analyze_aps_with_ai(llm_service, aps_cercanos, current_ap_info, our_aps)
        
        # 9. Preparar respuesta final
        result = {
            "notificacion_inicial": notification,
            "device_info": {
                "id": device_id,
                "nombre": device_name,
                "ip": ip_address,
                "ap_actual": current_ap_info
            },
            "escaneo": {
                "total_aps_detectados": len(aps_cercanos),
                "aps_nuestros": len([ap for ap in aps_cercanos if any(
                    our_ap.get("identification", {}).get("mac") == ap.get("bssid") 
                    for our_ap in our_aps
                )]),
                "aps_competencia": len(aps_cercanos) - len([ap for ap in aps_cercanos if any(
                    our_ap.get("identification", {}).get("mac") == ap.get("bssid") 
                    for our_ap in our_aps
                )]),
                "aps_detectados": aps_cercanos[:10]  # Top 10 por señal
            },
            "analisis_ia": ai_analysis,
            "tiempo_total_segundos": 45
        }
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en optimización de AP: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
