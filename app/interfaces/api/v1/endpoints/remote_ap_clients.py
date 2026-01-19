"""
Endpoint para obtener clientes de un AP remoto usando UISP
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, Optional
from app.infrastructure.api.uisp_client import UISPClient
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["remote-ap"])


async def get_uisp_client() -> UISPClient:
    """Obtener cliente UISP configurado"""
    return UISPClient(
        base_url=settings.UISP_BASE_URL,
        token=settings.UISP_TOKEN
    )


@router.get("/list-all-aps")
async def list_all_aps() -> Dict[str, Any]:
    """
    Lista todos los APs encontrados en UISP para debug
    
    Returns:
        Lista de todos los APs con su información
    """
    try:
        uisp_client = await get_uisp_client()
        
        # Obtener todos los dispositivos
        devices = await uisp_client.get_devices()
        
        # Filtrar solo APs
        ap_devices = []
        for device in devices:
            device_type = device.get("identification", {}).get("type")
            if device_type and device_type.lower() == "ap":
                ap_devices.append({
                    "device_id": device.get("identification", {}).get("id"),
                    "name": device.get("identification", {}).get("name"),
                    "ip_address": device.get("ipAddress"),
                    "mac_address": device.get("identification", {}).get("mac"),
                    "model": device.get("identification", {}).get("model"),
                    "status": device.get("status"),
                    "stations_count": device.get("overview", {}).get("stationsCount", 0)
                })
        
        return {
            "success": True,
            "total_devices": len(devices),
            "total_aps": len(ap_devices),
            "aps": ap_devices
        }
        
    except Exception as e:
        logger.error(f"Error listando APs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/get-ap-clients-by-bssid")
async def get_ap_clients_by_bssid(
    bssid: str = Query(..., description="BSSID del AP (ej: 802AA8249E26)"),
    ssid: Optional[str] = Query(None, description="SSID del AP (opcional, ayuda a buscar)")
) -> Dict[str, Any]:
    """
    Obtiene los clientes de un AP usando su BSSID desde UISP
    
    Args:
        bssid: BSSID del AP (sin dos puntos)
        ssid: SSID del AP (opcional, para mejor búsqueda)
        
    Returns:
        Información del AP y sus clientes conectados
    """
    try:
        uisp_client = await get_uisp_client()
        
        # Obtener todos los dispositivos
        devices = await uisp_client.get_devices()
        
        # Buscar el AP por BSSID con múltiples formatos
        target_ap = None
        formatted_bssid = bssid.upper().replace(":", "")
        
        # Intentar diferentes formatos de BSSID
        bssid_formats = [
            formatted_bssid,  # 802AA8249E26
            ":".join([formatted_bssid[i:i+2] for i in range(0, len(formatted_bssid), 2)]),  # 80:2A:A8:24:9E:26
            "-".join([formatted_bssid[i:i+2] for i in range(0, len(formatted_bssid), 2)])   # 80-2A-A8-24-9E-26
        ]
        
        for device in devices:
            device_mac = device.get("identification", {}).get("mac", "")
            if device_mac:
                device_mac_clean = device_mac.upper().replace(":", "").replace("-", "")
                if device_mac_clean == formatted_bssid:
                    target_ap = device
                    break
        
        # Si no encuentra por BSSID, buscar por SSID si se proporcionó
        if not target_ap and ssid:
            for device in devices:
                device_name = device.get("identification", {}).get("name", "")
                if device_name == ssid:
                    target_ap = device
                    break
        
        # Si todavía no encuentra, buscar por nombre que contenga el SSID
        if not target_ap and ssid:
            for device in devices:
                device_name = device.get("identification", {}).get("name", "")
                if ssid.lower() in device_name.lower():
                    target_ap = device
                    break
        
        # Debug: mostrar dispositivos encontrados
        if not target_ap:
            logger.warning(f"AP no encontrado. BSSID buscado: {formatted_bssid}")
            logger.warning(f"BSSID formats probados: {bssid_formats}")
            if ssid:
                logger.warning(f"SSID buscado: {ssid}")
            
            # Mostrar algunos dispositivos para debug
            ap_devices = [d for d in devices if d.get("identification", {}).get("type") == "ap"]
            logger.warning(f"APs encontrados en UISP: {len(ap_devices)}")
            for ap in ap_devices[:5]:  # Primeros 5 para debug
                ap_name = ap.get("identification", {}).get("name", "Unknown")
                ap_mac = ap.get("identification", {}).get("mac", "Unknown")
                logger.warning(f"  - {ap_name} (MAC: {ap_mac})")
            
            raise HTTPException(
                status_code=404, 
                detail=f"AP con BSSID {bssid} no encontrado en UISP. Se buscaron {len(devices)} dispositivos."
            )
        
        # Obtener información del AP
        ap_info = {
            "device_id": target_ap.get("identification", {}).get("id"),
            "name": target_ap.get("identification", {}).get("name"),
            "ip_address": target_ap.get("ipAddress"),
            "mac_address": target_ap.get("identification", {}).get("mac"),
            "model": target_ap.get("identification", {}).get("model"),
            "status": target_ap.get("status"),
            "overview": target_ap.get("overview", {})
        }
        
        # Obtener clientes desde overview
        overview = target_ap.get("overview", {})
        clients_count = overview.get("stationsCount", 0)
        
        # Obtener interfaces para más información
        device_id = target_ap.get("identification", {}).get("id")
        interfaces = await uisp_client.get_device_interfaces(device_id) if device_id else []
        
        # Buscar interfaz wireless para más detalles
        wireless_info = {}
        for iface in interfaces:
            if iface.get("identification", {}).get("type") == "wireless":
                wireless_data = iface.get("wireless", {})
                wireless_info = {
                    "frequency": wireless_data.get("frequency"),
                    "channel_width": wireless_data.get("channelWidth"),
                    "transmit_power": wireless_data.get("transmitPower"),
                    "mode": wireless_data.get("mode")
                }
                break
        
        return {
            "success": True,
            "ap_info": ap_info,
            "clients_count": clients_count,
            "wireless_info": wireless_info,
            "source": "UISP API"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo clientes del AP {bssid}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo clientes: {str(e)}")


@router.get("/get-ap-clients-from-survey")
async def get_ap_clients_from_survey(
    station_ip: str = Query(..., description="IP de la estación que hizo el site survey")
) -> Dict[str, Any]:
    """
    Obtiene los clientes del mejor AP encontrado en el site survey de una estación
    
    Args:
        station_ip: IP de la estación
        
    Returns:
        Información del mejor AP y sus clientes
    """
    try:
        # Importar aquí para evitar import circular
        from app.interfaces.api.v1.endpoints.device_analysis_complete import perform_site_survey_and_filter
        from app.infrastructure.ssh.ubiquiti_ssh_client import UbiquitiSSHClient
        from app.config.settings import settings
        
        # Realizar site survey para encontrar el mejor AP
        ssh_client = UbiquitiSSHClient()
        uisp_client = await get_uisp_client()
        
        survey_result = await perform_site_survey_and_filter(
            ssh_client=ssh_client,
            uisp_client=uisp_client,
            device_ip=station_ip,
            ssh_username=settings.SSH_USERNAME,
            ssh_password=settings.SSH_PASSWORD
        )
        
        if not survey_result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=f"No se pudo realizar site survey: {survey_result.get('message', 'Error desconocido')}"
            )
        
        best_ap = survey_result.get("best_ap")
        if not best_ap:
            raise HTTPException(
                status_code=404,
                detail="No se encontró mejor AP en el site survey"
            )
        
        # Obtener clientes del mejor AP usando su BSSID
        bssid = best_ap.get("bssid")
        ssid = best_ap.get("ssid")
        
        if not bssid:
            raise HTTPException(
                status_code=400,
                detail="El mejor AP no tiene BSSID"
            )
        
        # Llamar al endpoint anterior
        return await get_ap_clients_by_bssid(bssid=bssid, ssid=ssid)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo clientes desde survey: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
