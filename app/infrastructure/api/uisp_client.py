import logging
from typing import Dict, Any, Optional, List
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)

class UISPClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.session = httpx.AsyncClient(
            base_url=base_url,
            headers={
                'X-Auth-Token': token,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            timeout=httpx.Timeout(60.0, connect=10.0),  # 60s total, 10s para conectar
            verify=False
        )

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        url = f"{endpoint.lstrip('/')}"
        try:
            logger.debug(f"UISP API Request: {method} {url}")
            response = await self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"UISP API error: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.ConnectTimeout:
            logger.error(f"Connection timeout to UISP at {self.base_url}. Verify UISP is accessible.")
            raise ConnectionError(f"No se pudo conectar a UISP en {self.base_url}. Verifica que UISP esté accesible y la URL sea correcta.")
        except httpx.ConnectError as e:
            logger.error(f"Connection error to UISP: {str(e)}")
            raise ConnectionError(f"Error de conexión a UISP: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error calling UISP API: {str(e)}")
            raise

    async def get_devices(self) -> List[Dict[str, Any]]:
        return await self._request('GET', '/nms/api/v2.1/devices')

    async def get_device(self, device_id: str) -> Dict[str, Any]:
        return await self._request('GET', f'/nms/api/v2.1/devices/{device_id}')

    async def get_device_statistics(self, device_id: str, interval: str = "hour") -> Dict[str, Any]:
        return await self._request('GET', f'/nms/api/v2.1/devices/{device_id}/statistics', params={'interval': interval})

    async def get_device_interfaces(self, device_id: str) -> List[Dict[str, Any]]:
        return await self._request('GET', f'/nms/api/v2.1/devices/{device_id}/interfaces')

    async def get_device_outages(self, device_id: str) -> List[Dict[str, Any]]:
        return await self._request('GET', f'/nms/api/v2.1/devices/{device_id}/outages')

    async def get_device_logs(self, device_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        return await self._request('GET', f'/nms/api/v2.1/devices/{device_id}/logs', params={'limit': limit})

    async def get_device_site_survey(self, device_id: str) -> List[Dict[str, Any]]:
        """
        Get site survey (nearby APs scan) for a device
        NOTA: El endpoint /spectrum-scan no está disponible en UISP v2.1
        """
        raise NotImplementedError(
            "El endpoint de site survey no está disponible en tu versión de UISP. "
            "Usa SSH para ejecutar: wlanconfig ath0 list scan"
        )

    async def trigger_site_survey(self, device_id: str) -> Dict[str, Any]:
        """
        Trigger a new site survey scan on the device
        NOTA: El endpoint /spectrum-scan no está disponible en UISP v2.1
        """
        raise NotImplementedError(
            "El endpoint de site survey no está disponible en tu versión de UISP. "
            "Usa SSH para ejecutar: wlanconfig ath0 list scan"
        )

    async def get_device_wireless_config(self, device_id: str) -> Dict[str, Any]:
        """
        Get device wireless configuration from device overview
        NOTA: El endpoint /wireless no está disponible en todas las versiones de UISP
        """
        device = await self._request('GET', f'/nms/api/v2.1/devices/{device_id}')
        overview = device.get("overview", {})
        
        # Extraer información wireless del overview
        return {
            "frequency": overview.get("frequency"),
            "channelWidth": overview.get("channelWidth"),
            "transmitPower": overview.get("transmitPower"),
            "signal": overview.get("signal"),
            # UISP no expone availableFrequencies en la API v2.1
            # Esta información solo está disponible en la UI web
            "note": "Tu versión de UISP no expone endpoints de configuración wireless en la API"
        }

    async def update_device_wireless_config(self, device_id: str, wireless_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        NOTA: Tu versión de UISP no soporta actualización de configuración wireless vía API
        Los cambios deben hacerse manualmente desde la interfaz web de UISP
        """
        raise NotImplementedError(
            "Tu versión de UISP no soporta actualización de configuración wireless vía API. "
            "Debes cambiar la frecuencia manualmente desde la interfaz web de UISP: "
            "Devices → Selecciona el dispositivo → Configuration → Wireless"
        )

    async def get_all_aps(self) -> List[Dict[str, Any]]:
        """Get all APs in UISP (to check if detected APs are ours or competition)"""
        devices = await self.get_devices()
        # Filter only APs (role = 'ap')
        return [d for d in devices if d.get("identification", {}).get("role") == "ap"]

    async def close(self):
        await self.session.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
