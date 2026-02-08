"""UISP Services"""

import httpx
from typing import Dict, Any, Optional
from app_fast_api.utils.logger import get_logger

logger = get_logger(__name__)

class UISPService:
    """UISP Service"""
    def __init__(self, base_url: str, token: str) -> None:
        """Initialize UISP service"""
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

    async def get_all_uisp_devices(self) -> Optional[Dict[str, Any]]:
        """Get all devices from UISP"""
        try:
            response = await self.session.get('/v2.1/devices')
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            logger.error(f'[get_all_uisp_devices]:Error getting devices from UISP: {e}')
            raise Exception(f"[get_all_uisp_devices]:Error al obtener dispositivos de UISP: {e}")

        except Exception as e:
            logger.error(f'[get_all_uisp_devices]:Error getting devices from UISP: {e}')
            raise Exception(f"[get_all_uisp_devices]:Error al obtener dispositivos de UISP: {e}")

    async def get_device_ssids(self) -> Optional[Dict[str, Any]]:
        """"""
        try:
            response = await self.session.get('/v2.1/devices/ssids')
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            logger.error(f'[get_device_ssids]:Error getting devices from UISP: {e}')
            raise Exception(f"[get_device_ssids]:Error al obtener dispositivos de UISP: {e}")

        except Exception as e:
            logger.error(f'[get_device_ssids]:Error getting devices from UISP: {e}')
            raise Exception(f"[get_device_ssids]:Error al obtener dispositivos de UISP: {e}")

    async def get_device_statistics(self, device_id: str, interval: str = 'fourhours') -> Optional[Dict[str, Any]]:
        """
        Get device statistics from UISP.

        Args:
            device_id: UISP device UUID
            interval: Time interval - 'hour', 'fourhours', 'day', 'week', 'month'

        Returns:
            Dictionary with timeseries data
        """
        try:
            response = await self.session.get(f'/v2.1/devices/{device_id}/statistics?interval={interval}')
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            logger.error(f'[get_device_statistics]: Error getting statistics for device {device_id}: {e}')
            return None
        except Exception as e:
            logger.error(f'[get_device_statistics]: Unexpected error: {e}')
            return None
