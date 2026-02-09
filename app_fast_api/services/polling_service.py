"""
Site Monitoring Polling Service for automatic scanning.
"""

import asyncio
import os
from typing import Dict, Any, Optional
from datetime import datetime

from app_fast_api.services.alerting_services import UNMSAlertingService
from app_fast_api.services.whatsapp_service import WhatsAppService
from app_fast_api.utils.logger import get_logger
from app_fast_api.utils.timezone import now_argentina

logger = get_logger(__name__)


class SiteMonitoringPollingService:
    """Service for automatic polling of site monitoring."""

    def __init__(self,
                 alerting_service: UNMSAlertingService,
                 whatsapp_service: WhatsAppService,
                 interval_seconds: int = 300,
                 enabled: bool = False):
        """
        Initialize polling service.

        Args:
            alerting_service: UNMS alerting service
            whatsapp_service: WhatsApp notification service
            interval_seconds: Polling interval in seconds (default: 300 = 5 minutes)
            enabled: Whether polling is enabled
        """
        self.alerting_service = alerting_service
        self.whatsapp_service = whatsapp_service
        self.interval_seconds = interval_seconds
        self.enabled = enabled
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
        self.last_scan_time: Optional[datetime] = None
        self.last_scan_result: Optional[Dict[str, Any]] = None

        logger.info(f"Polling service initialized: enabled={enabled}, interval={interval_seconds}s")

    async def start_polling(self) -> Dict[str, Any]:
        """
        Start the polling loop.

        Returns:
            Status information
        """
        if self.is_running:
            logger.warning("Polling is already running")
            return {
                'success': False,
                'message': 'Polling is already running',
                'is_running': True
            }

        self.enabled = True
        self.is_running = True
        self.task = asyncio.create_task(self._polling_loop())

        logger.info("🔄 Polling started")

        return {
            'success': True,
            'message': 'Polling started successfully',
            'is_running': True,
            'interval_seconds': self.interval_seconds
        }

    async def stop_polling(self) -> Dict[str, Any]:
        """
        Stop the polling loop.

        Returns:
            Status information
        """
        if not self.is_running:
            logger.warning("Polling is not running")
            return {
                'success': False,
                'message': 'Polling is not running',
                'is_running': False
            }

        self.enabled = False
        self.is_running = False

        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                logger.info("⏸️  Polling task cancelled")

        logger.info("⏹️  Polling stopped")

        return {
            'success': True,
            'message': 'Polling stopped successfully',
            'is_running': False
        }

    def get_status(self) -> Dict[str, Any]:
        """
        Get polling status.

        Returns:
            Status information
        """
        return {
            'is_running': self.is_running,
            'enabled': self.enabled,
            'interval_seconds': self.interval_seconds,
            'last_scan_time': self.last_scan_time.isoformat() if self.last_scan_time else None,
            'last_scan_result': self.last_scan_result
        }

    async def _polling_loop(self):
        """
        Main polling loop that runs continuously.
        """
        logger.info(f"🔄 Starting polling loop (interval: {self.interval_seconds}s)")

        while self.enabled and self.is_running:
            try:
                logger.info("🔍 Starting scheduled site scan with alerts...")

                # Run scan with WhatsApp alerts
                result = await self.alerting_service.scan_and_alert_sites_with_whatsapp(
                    self.whatsapp_service
                )

                self.last_scan_time = now_argentina()
                self.last_scan_result = result

                if result.get('success'):
                    summary = result.get('summary', {})
                    notifications = result.get('notifications', {})

                    logger.info(
                        f"✅ Scan completed: "
                        f"{summary.get('total_sites', 0)} sites, "
                        f"{notifications.get('outage_alerts_sent', 0)} outage alerts, "
                        f"{notifications.get('recovery_alerts_sent', 0)} recovery alerts"
                    )
                else:
                    logger.error(f"❌ Scan failed: {result.get('error', 'Unknown error')}")

            except Exception as e:
                logger.error(f"❌ Error in polling loop: {str(e)}")
                self.last_scan_result = {
                    'success': False,
                    'error': str(e)
                }

            # Wait for next interval
            logger.info(f"⏳ Waiting {self.interval_seconds}s until next scan...")
            await asyncio.sleep(self.interval_seconds)

        logger.info("🛑 Polling loop ended")

    async def trigger_manual_scan(self) -> Dict[str, Any]:
        """
        Trigger a manual scan outside the normal polling schedule.

        Returns:
            Scan result
        """
        logger.info("🔍 Manual scan triggered")

        try:
            result = await self.alerting_service.scan_and_alert_sites_with_whatsapp(
                self.whatsapp_service
            )

            self.last_scan_time = now_argentina()
            self.last_scan_result = result

            return result

        except Exception as e:
            logger.error(f"❌ Error in manual scan: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }


# Global polling service instance (singleton)
_polling_service: Optional[SiteMonitoringPollingService] = None


def get_polling_service() -> Optional[SiteMonitoringPollingService]:
    """
    Get the global polling service instance.

    Returns:
        Polling service or None if not initialized
    """
    return _polling_service


def initialize_polling_service(
        alerting_service: UNMSAlertingService,
        whatsapp_service: WhatsAppService
) -> SiteMonitoringPollingService:
    """
    Initialize the global polling service.

    Args:
        alerting_service: UNMS alerting service
        whatsapp_service: WhatsApp notification service

    Returns:
        Initialized polling service
    """
    global _polling_service

    # Get configuration from environment
    interval = int(os.getenv('POLLING_INTERVAL_SECONDS', '300'))
    enabled = os.getenv('POLLING_ENABLED', 'false').lower() == 'true'

    _polling_service = SiteMonitoringPollingService(
        alerting_service=alerting_service,
        whatsapp_service=whatsapp_service,
        interval_seconds=interval,
        enabled=enabled
    )

    logger.info(f"Polling service initialized globally: enabled={enabled}, interval={interval}s")

    return _polling_service
