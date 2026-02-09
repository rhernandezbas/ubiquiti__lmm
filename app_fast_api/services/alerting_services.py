"""Alerting Services for site monitoring and event management."""

import httpx
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

from app_fast_api.models.ubiquiti_monitoring.alerting import (
    SiteMonitoring, AlertEvent, AlertSeverity, AlertStatus, EventType
)
from app_fast_api.models.ubiquiti_monitoring.post_mortem import PostMortemStatus
from app_fast_api.repositories.alerting_repositories import (
    SiteMonitoringRepository, AlertEventRepository, PostMortemRepository
)
from app_fast_api.utils.logger import get_logger
from app_fast_api.utils.timezone import format_argentina_datetime, now_argentina

logger = get_logger(__name__)


class UNMSAlertingService:
    """Service for monitoring UNMS sites and managing alerts."""

    def __init__(self, base_url: str, token: str,
                 site_repo: SiteMonitoringRepository,
                 event_repo: AlertEventRepository,
                 pm_repo: PostMortemRepository,
                 outage_threshold: float = 95.0):
        """
        Initialize UNMS alerting service.

        Args:
            base_url: UNMS base URL
            token: UNMS authentication token
            site_repo: Site monitoring repository
            event_repo: Alert event repository
            pm_repo: Post-mortem repository
            outage_threshold: Percentage threshold to consider site as down (default: 95%)
        """
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.site_repo = site_repo
        self.event_repo = event_repo
        self.pm_repo = pm_repo
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

    def create_post_mortem_for_event(self, event: AlertEvent, site: SiteMonitoring) -> Optional[Any]:
        """
        Auto-create a Post-Mortem when a critical site outage is detected.

        Args:
            event: The AlertEvent that triggered the incident
            site: The SiteMonitoring object with site details

        Returns:
            PostMortem object if created, None if already exists
        """
        try:
            # Check if Post-Mortem already exists for this event
            existing_pm = self.pm_repo.get_post_mortem_by_event(event.id)
            if existing_pm:
                logger.info(f"Post-Mortem already exists for event {event.id}")
                return None

            # Calculate initial timeline event
            incident_time = event.created_at or now_argentina()

            # Pre-fill Post-Mortem data
            pm_data = {
                'alert_event_id': event.id,
                'title': f'Incidente: {site.site_name}',
                'status': PostMortemStatus.IN_PROGRESS,
                'incident_start': incident_time,
                'detection_time': incident_time,
                'summary': f'Caída detectada en sitio {site.site_name}. {site.device_outage_count} de {site.device_count} dispositivos fuera de servicio ({site.outage_percentage:.1f}%).',
                'impact_description': f'Sitio completamente caído o severamente degradado. Impacto en servicios de red.',
                'affected_devices': site.device_outage_count,
                'severity': event.severity.value,
                'customer_impact': 'total' if site.is_site_down else 'partial',
                'timeline_events': [
                    {
                        'time': incident_time.isoformat(),
                        'event': f'Caída detectada: {site.device_outage_count}/{site.device_count} dispositivos down',
                        'actor': 'Sistema de Monitoreo',
                        'type': 'detection'
                    }
                ],
                'tags': [
                    'site_outage',
                    site.site_name,
                    f'severity_{event.severity.value}'
                ]
            }

            # Add contact information if available
            if site.contact_name or site.contact_phone:
                pm_data['external_links'] = []
                if site.contact_name:
                    pm_data['external_links'].append({
                        'type': 'contact',
                        'name': site.contact_name,
                        'phone': site.contact_phone,
                        'email': site.contact_email
                    })

            post_mortem = self.pm_repo.create_post_mortem(pm_data)
            logger.info(f"✅ Auto-created Post-Mortem {post_mortem.id} for event {event.id} - {site.site_name}")
            return post_mortem

        except Exception as e:
            logger.error(f"Error creating Post-Mortem for event {event.id}: {str(e)}")
            # Don't raise - Post-Mortem creation shouldn't block alerting
            return None

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

            # Get previous state to detect state changes
            site_id = identification.get('id')
            existing_site = self.site_repo.get_site_by_id(site_id)
            previous_is_down = existing_site.is_site_down if existing_site else False

            site_monitoring_data = {
                'site_id': site_id,
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
                'last_checked': now_argentina(),
                'last_updated': datetime.fromisoformat(identification.get('updated').replace('Z', '+00:00')) if identification.get('updated') else now_argentina(),
                'created_at': now_argentina()
            }

            # Handle outage_start based on state change
            if not previous_is_down and is_down:
                # Site just went down - record outage start time
                site_monitoring_data['outage_start'] = now_argentina()
                logger.warning(f"🔴 Site {site_monitoring_data['site_name']} went DOWN - recording outage_start")
            elif previous_is_down and not is_down:
                # Site recovered - clear outage start time
                site_monitoring_data['outage_start'] = None
                logger.info(f"✅ Site {site_monitoring_data['site_name']} RECOVERED - clearing outage_start")
            # If state didn't change, don't include outage_start (preserve existing value)

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
                        'created_at': now_argentina(),
                        'updated_at': now_argentina()
                    }
                    event = self.event_repo.create_event(event_data)
                    logger.critical(f"CRITICAL ALERT: {event.title}")

                    # Auto-create Post-Mortem for critical site outages
                    self.create_post_mortem_for_event(event, site)

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
                        'created_at': now_argentina(),
                        'updated_at': now_argentina()
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
                'scan_timestamp': now_argentina().isoformat()
            }

            logger.info(f"Site scan completed: {summary}")
            return summary

        except Exception as e:
            logger.error(f"Error scanning sites: {str(e)}")
            raise

    async def check_uisp_availability(self) -> bool:
        """
        Check if UISP API is available and responding.

        Returns:
            True if UISP is available, False otherwise
        """
        try:
            response = await self.session.get('/nms/api/v2.1/sites', timeout=5.0)
            response.raise_for_status()
            logger.info("✅ UISP API is available")
            return True
        except httpx.TimeoutException:
            logger.error("❌ UISP API timeout - service may be down")
            return False
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ UISP API returned error: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"❌ UISP API unavailable: {e}")
            return False

    async def scan_and_alert_sites_with_whatsapp(self, whatsapp_service) -> Dict[str, Any]:
        """
        Scan all sites and send WhatsApp alerts for outages/recoveries.
        ONLY sends alerts if UISP is available to avoid false positives.

        Args:
            whatsapp_service: WhatsAppService instance

        Returns:
            Summary of scan results including notifications sent
        """
        try:
            # CRITICAL: Check UISP availability first
            uisp_available = await self.check_uisp_availability()
            if not uisp_available:
                logger.error("⛔ UISP not available - skipping alerts to prevent false positives")
                return {
                    'success': False,
                    'error': 'UISP unavailable',
                    'uisp_available': False,
                    'notifications_sent': 0
                }

            logger.info("✅ UISP available - proceeding with scan")

            # Get all sites
            sites_data = await self.get_all_sites()
            if not sites_data:
                logger.warning("No sites retrieved from UNMS")
                return {
                    'success': False,
                    'error': 'No sites data',
                    'uisp_available': True,
                    'total_sites': 0
                }

            total_sites = len(sites_data)
            sites_down = 0
            sites_recovered = 0
            notifications_sent = 0
            notification_failures = 0

            for site_data in sites_data:
                try:
                    # Process site and save to DB
                    site = await self.process_site_data(site_data)

                    # Check if we need to create/resolve events
                    event = await self.check_and_create_outage_event(site)

                    # If new outage event created, send WhatsApp alerts
                    if event and event.status == AlertStatus.ACTIVE:
                        if event.event_type == EventType.SITE_OUTAGE:
                            logger.info(f"🚨 Sending outage alerts for {site.site_name}")

                            # Prepare event data for notification (in Argentina timezone)
                            event_data = {
                                'detected_at': format_argentina_datetime(event.created_at)
                            }

                            # Send WhatsApp notifications
                            results = await whatsapp_service.send_outage_alert(site_data, event_data)

                            # Track notification results
                            if results.get('complete', {}).get('success'):
                                notifications_sent += 1
                            else:
                                notification_failures += 1

                            if results.get('summary', {}).get('success'):
                                notifications_sent += 1
                            else:
                                notification_failures += 1

                            sites_down += 1

                    # Check for recoveries
                    if not site.is_site_down and site.outage_percentage < 50.0:
                        # Check if there were active events that got resolved
                        recently_resolved = self.event_repo.get_events_by_site(site.id)
                        for resolved_event in recently_resolved:
                            if resolved_event.status == AlertStatus.RESOLVED and resolved_event.auto_resolved:
                                # Check if it was recently resolved (within last minute)
                                if resolved_event.resolved_at:
                                    time_since_resolution = (now_argentina() - resolved_event.resolved_at).total_seconds()
                                    if time_since_resolution < 60:  # Resolved in last minute
                                        logger.info(f"✅ Sending recovery alerts for {site.site_name}")

                                        downtime_minutes = 0
                                        if resolved_event.created_at and resolved_event.resolved_at:
                                            downtime_minutes = int((resolved_event.resolved_at - resolved_event.created_at).total_seconds() / 60)

                                        recovery_event_data = {
                                            'recovered_at': resolved_event.resolved_at,  # Pass datetime, will be formatted in WhatsApp service
                                            'downtime_minutes': downtime_minutes
                                        }

                                        # Send recovery notifications
                                        recovery_results = await whatsapp_service.send_recovery_alert(site_data, recovery_event_data)

                                        if recovery_results.get('complete', {}).get('success'):
                                            notifications_sent += 1

                                        if recovery_results.get('summary', {}).get('success'):
                                            notifications_sent += 1

                                        sites_recovered += 1

                except Exception as e:
                    logger.error(f"Error processing site {site_data.get('identification', {}).get('name', 'unknown')}: {str(e)}")
                    continue

            summary = {
                'success': True,
                'uisp_available': True,
                'total_sites': total_sites,
                'sites_down': sites_down,
                'sites_recovered': sites_recovered,
                'notifications_sent': notifications_sent,
                'notification_failures': notification_failures,
                'scan_timestamp': now_argentina().isoformat()
            }

            logger.info(f"✅ Site scan with alerts completed: {summary}")
            return summary

        except Exception as e:
            logger.error(f"❌ Error scanning sites with WhatsApp alerts: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'uisp_available': uisp_available if 'uisp_available' in locals() else None
            }


class AlertEventService:
    """Service for managing alert events."""

    def __init__(self, event_repo: AlertEventRepository):
        """Initialize alert event service."""
        self.event_repo = event_repo

    def create_custom_event(self, event_data: dict) -> AlertEvent:
        """Create a custom alert event."""
        event_data['created_at'] = now_argentina()
        event_data['updated_at'] = now_argentina()
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
