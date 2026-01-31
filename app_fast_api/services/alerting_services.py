"""Alerting Services for site monitoring and event management."""

import httpx
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

from app_fast_api.models.ubiquiti_monitoring.alerting import (
    SiteMonitoring, AlertEvent, AlertSeverity, AlertStatus, EventType
)
from app_fast_api.repositories.alerting_repositories import (
    SiteMonitoringRepository, AlertEventRepository
)
from app_fast_api.utils.logger import get_logger

logger = get_logger(__name__)


class UNMSAlertingService:
    """Service for monitoring UNMS sites and managing alerts."""

    def __init__(self, base_url: str, token: str,
                 site_repo: SiteMonitoringRepository,
                 event_repo: AlertEventRepository,
                 outage_threshold: float = 95.0):
        """
        Initialize UNMS alerting service.

        Args:
            base_url: UNMS base URL
            token: UNMS authentication token
            site_repo: Site monitoring repository
            event_repo: Alert event repository
            outage_threshold: Percentage threshold to consider site as down (default: 95%)
        """
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.site_repo = site_repo
        self.event_repo = event_repo
        self.outage_threshold = outage_threshold

        self.session = httpx.AsyncClient(
            base_url=base_url,
            headers={
                'X-Auth-Token': token,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            timeout=httpx.Timeout(60.0, connect=10.0),
            verify=False
        )

    async def get_all_sites(self) -> Optional[List[Dict[str, Any]]]:
        """Get all sites from UNMS API."""
        try:
            response = await self.session.get('/nms/api/v2.1/sites')
            response.raise_for_status()
            sites = response.json()
            logger.info(f"Retrieved {len(sites)} sites from UNMS")
            return sites
        except httpx.RequestError as e:
            logger.error(f'Error getting sites from UNMS: {e}')
            raise Exception(f"Error al obtener sites de UNMS: {e}")
        except Exception as e:
            logger.error(f'Unexpected error getting sites from UNMS: {e}')
            raise Exception(f"Error inesperado al obtener sites de UNMS: {e}")

    def calculate_outage_percentage(self, device_count: int, outage_count: int) -> float:
        """Calculate outage percentage."""
        if device_count == 0:
            return 0.0
        return (outage_count / device_count) * 100.0

    def is_site_down(self, outage_percentage: float) -> bool:
        """Determine if site is down based on outage threshold."""
        return outage_percentage >= self.outage_threshold

    async def process_site_data(self, site_data: dict) -> SiteMonitoring:
        """
        Process a site from UNMS and save to database.

        Args:
            site_data: Site data from UNMS API

        Returns:
            SiteMonitoring object
        """
        try:
            identification = site_data.get('identification', {})
            description = site_data.get('description', {})
            contact = description.get('contact', {})
            location = description.get('location', {})

            device_count = description.get('deviceCount', 0)
            outage_count = description.get('deviceOutageCount', 0)
            outage_percentage = self.calculate_outage_percentage(device_count, outage_count)
            is_down = self.is_site_down(outage_percentage)

            site_monitoring_data = {
                'site_id': identification.get('id'),
                'site_name': identification.get('name', 'Unknown'),
                'site_status': identification.get('status'),
                'site_type': identification.get('type'),
                'address': description.get('address'),
                'latitude': location.get('latitude'),
                'longitude': location.get('longitude'),
                'height': description.get('height'),
                'contact_name': contact.get('name'),
                'contact_phone': contact.get('phone'),
                'contact_email': contact.get('email'),
                'device_count': device_count,
                'device_outage_count': outage_count,
                'device_list_status': description.get('deviceListStatus'),
                'outage_percentage': outage_percentage,
                'is_site_down': is_down,
                'note': description.get('note'),
                'ip_addresses': json.dumps(description.get('ipAddresses', [])),
                'regulatory_domain': description.get('regulatoryDomain'),
                'suspended': identification.get('suspended', False),
                'last_checked': datetime.now(),
                'last_updated': datetime.fromisoformat(identification.get('updated').replace('Z', '+00:00')) if identification.get('updated') else datetime.now(),
                'created_at': datetime.now()
            }

            site = self.site_repo.create_or_update_site(site_monitoring_data)

            if is_down:
                logger.warning(f"Site {site.site_name} is DOWN: {outage_count}/{device_count} devices ({outage_percentage:.1f}%)")

            return site

        except Exception as e:
            logger.error(f"Error processing site data: {str(e)}")
            raise

    async def check_and_create_outage_event(self, site: SiteMonitoring) -> Optional[AlertEvent]:
        """
        Check if site requires an outage alert and create event if needed.

        Args:
            site: SiteMonitoring object

        Returns:
            AlertEvent if created, None otherwise
        """
        try:
            # Check if there's already an active event for this site
            existing_events = self.event_repo.get_events_by_site(site.id)
            active_outage_events = [
                e for e in existing_events
                if e.status == AlertStatus.ACTIVE and e.event_type in [EventType.SITE_OUTAGE, EventType.SITE_DEGRADED]
            ]

            if site.is_site_down:
                # Site is down (>= threshold)
                if not active_outage_events:
                    # Create new critical event
                    event_data = {
                        'event_type': EventType.SITE_OUTAGE,
                        'severity': AlertSeverity.CRITICAL,
                        'status': AlertStatus.ACTIVE,
                        'title': f'Sitio Caído: {site.site_name}',
                        'description': f'El sitio {site.site_name} tiene {site.device_outage_count} de {site.device_count} dispositivos caídos ({site.outage_percentage:.1f}% fuera de servicio). Umbral: {self.outage_threshold}%.',
                        'site_id': site.id,
                        'device_count': site.device_count,
                        'outage_count': site.device_outage_count,
                        'outage_percentage': site.outage_percentage,
                        'created_at': datetime.now(),
                        'updated_at': datetime.now()
                    }
                    event = self.event_repo.create_event(event_data)
                    logger.critical(f"CRITICAL ALERT: {event.title}")
                    return event

            elif site.outage_percentage >= 50.0:
                # Site is degraded (50-95%)
                if not active_outage_events:
                    event_data = {
                        'event_type': EventType.SITE_DEGRADED,
                        'severity': AlertSeverity.HIGH,
                        'status': AlertStatus.ACTIVE,
                        'title': f'Sitio Degradado: {site.site_name}',
                        'description': f'El sitio {site.site_name} tiene {site.device_outage_count} de {site.device_count} dispositivos caídos ({site.outage_percentage:.1f}% fuera de servicio).',
                        'site_id': site.id,
                        'device_count': site.device_count,
                        'outage_count': site.device_outage_count,
                        'outage_percentage': site.outage_percentage,
                        'created_at': datetime.now(),
                        'updated_at': datetime.now()
                    }
                    event = self.event_repo.create_event(event_data)
                    logger.warning(f"HIGH ALERT: {event.title}")
                    return event
            else:
                # Site is healthy - auto-resolve any active events
                if active_outage_events:
                    for event in active_outage_events:
                        self.event_repo.resolve_event(
                            event.id,
                            resolved_by='system',
                            note=f'Sitio recuperado. Dispositivos activos: {site.device_count - site.device_outage_count}/{site.device_count}',
                            auto_resolved=True
                        )
                        logger.info(f"Auto-resolved event {event.id} for site {site.site_name}")

            return None

        except Exception as e:
            logger.error(f"Error checking/creating outage event: {str(e)}")
            raise

    async def scan_all_sites(self) -> Dict[str, Any]:
        """
        Scan all sites from UNMS and create alerts as needed.

        Returns:
            Summary of scan results
        """
        try:
            sites_data = await self.get_all_sites()

            if not sites_data:
                logger.warning("No sites retrieved from UNMS")
                return {
                    'total_sites': 0,
                    'sites_down': 0,
                    'sites_degraded': 0,
                    'new_events_created': 0
                }

            total_sites = len(sites_data)
            sites_down = 0
            sites_degraded = 0
            new_events = 0

            for site_data in sites_data:
                try:
                    site = await self.process_site_data(site_data)
                    event = await self.check_and_create_outage_event(site)

                    if site.is_site_down:
                        sites_down += 1
                    elif site.outage_percentage >= 50.0:
                        sites_degraded += 1

                    if event:
                        new_events += 1

                except Exception as e:
                    logger.error(f"Error processing site {site_data.get('identification', {}).get('name', 'unknown')}: {str(e)}")
                    continue

            summary = {
                'total_sites': total_sites,
                'sites_down': sites_down,
                'sites_degraded': sites_degraded,
                'sites_healthy': total_sites - sites_down - sites_degraded,
                'new_events_created': new_events,
                'scan_timestamp': datetime.now().isoformat()
            }

            logger.info(f"Site scan completed: {summary}")
            return summary

        except Exception as e:
            logger.error(f"Error scanning sites: {str(e)}")
            raise


class AlertEventService:
    """Service for managing alert events."""

    def __init__(self, event_repo: AlertEventRepository):
        """Initialize alert event service."""
        self.event_repo = event_repo

    def create_custom_event(self, event_data: dict) -> AlertEvent:
        """Create a custom alert event."""
        event_data['created_at'] = datetime.now()
        event_data['updated_at'] = datetime.now()
        return self.event_repo.create_event(event_data)

    def get_event(self, event_id: int) -> Optional[AlertEvent]:
        """Get event by ID."""
        return self.event_repo.get_event_by_id(event_id)

    def list_events(self, status: Optional[str] = None,
                    severity: Optional[str] = None,
                    event_type: Optional[str] = None,
                    limit: int = 100) -> List[AlertEvent]:
        """List events with filters."""
        status_enum = AlertStatus[status.upper()] if status else None
        severity_enum = AlertSeverity[severity.upper()] if severity else None
        event_type_enum = EventType[event_type.upper()] if event_type else None

        return self.event_repo.get_all_events(status_enum, severity_enum, event_type_enum, limit)

    def acknowledge_event(self, event_id: int, acknowledged_by: str, note: Optional[str] = None) -> AlertEvent:
        """Acknowledge an event."""
        return self.event_repo.acknowledge_event(event_id, acknowledged_by, note)

    def resolve_event(self, event_id: int, resolved_by: str, note: Optional[str] = None) -> AlertEvent:
        """Resolve an event."""
        return self.event_repo.resolve_event(event_id, resolved_by, note, auto_resolved=False)

    def delete_event(self, event_id: int) -> None:
        """Delete an event."""
        self.event_repo.delete_event(event_id)

    def get_active_events(self) -> List[AlertEvent]:
        """Get all active events."""
        return self.event_repo.get_active_events()
