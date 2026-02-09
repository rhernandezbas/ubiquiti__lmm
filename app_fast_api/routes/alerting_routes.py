"""
Routes for alerting and site monitoring
"""

import os
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

from app_fast_api.services.alerting_services import UNMSAlertingService, AlertEventService
from app_fast_api.services.whatsapp_service import WhatsAppService
from app_fast_api.services.post_mortem_service import PostMortemService
from app_fast_api.services.polling_service import initialize_polling_service, get_polling_service
from app_fast_api.repositories.alerting_repositories import (
    SiteMonitoringRepository,
    AlertEventRepository,
    PostMortemRepository,
    AlertNotificationRepository
)
from app_fast_api.models.ubiquiti_monitoring.alerting import AlertSeverity, AlertStatus, EventType
from app_fast_api.utils.logger import get_logger
from app_fast_api.utils.timezone import (
    format_argentina_datetime,
    format_argentina_time,
    now_argentina,
    to_argentina_isoformat
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/alerting", tags=["alerting"])

# Initialize services (singleton pattern)
UISP_BASE_URL = os.getenv("UISP_BASE_URL", "")
UISP_TOKEN = os.getenv("UISP_TOKEN", "")

site_repo = SiteMonitoringRepository()
event_repo = AlertEventRepository()
pm_repo = PostMortemRepository()

# Outage threshold - configurable via environment variable
OUTAGE_THRESHOLD = float(os.getenv("ALERT_OUTAGE_THRESHOLD_PERCENT", "95.0"))

unms_service = UNMSAlertingService(
    base_url=UISP_BASE_URL,
    token=UISP_TOKEN,
    site_repo=site_repo,
    event_repo=event_repo,
    pm_repo=pm_repo,
    outage_threshold=OUTAGE_THRESHOLD  # From env var or default 95%
)

event_service = AlertEventService(event_repo=event_repo)

whatsapp_service = WhatsAppService()

# Initialize post-mortem service
pm_service = PostMortemService(pm_repo=pm_repo, event_repo=event_repo)

# Initialize notification repository
notification_repo = AlertNotificationRepository()

# Initialize polling service (will auto-start if POLLING_ENABLED=true)
polling_service = initialize_polling_service(
    alerting_service=unms_service,
    whatsapp_service=whatsapp_service
)


# ============== Pydantic Models ==============

class SeverityEnum(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class StatusEnum(str, Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"
    IGNORED = "ignored"


class EventTypeEnum(str, Enum):
    SITE_OUTAGE = "site_outage"
    SITE_DEGRADED = "site_degraded"
    SITE_RECOVERED = "site_recovered"
    DEVICE_OUTAGE = "device_outage"
    DEVICE_RECOVERED = "device_recovered"
    CUSTOM = "custom"


class CreateEventRequest(BaseModel):
    """Model for creating a custom event"""
    event_type: EventTypeEnum = Field(..., description="Type of event")
    severity: SeverityEnum = Field(default=SeverityEnum.MEDIUM, description="Severity level")
    title: str = Field(..., description="Event title", min_length=5, max_length=500)
    description: Optional[str] = Field(None, description="Event description")
    custom_data: Optional[Dict[str, Any]] = Field(None, description="Additional custom data")


class AcknowledgeEventRequest(BaseModel):
    """Model for acknowledging an event"""
    acknowledged_by: str = Field(..., description="User who acknowledges", min_length=2)
    note: Optional[str] = Field(None, description="Acknowledgment note")


class ResolveEventRequest(BaseModel):
    """Model for resolving an event"""
    resolved_by: str = Field(..., description="User who resolves", min_length=2)
    note: Optional[str] = Field(None, description="Resolution note")


class ScanSitesResponse(BaseModel):
    """Response for site scan"""
    success: bool
    message: str
    summary: Dict[str, Any]


class EventResponse(BaseModel):
    """Response for event operations"""
    success: bool
    message: str
    event_id: Optional[int] = None


class TestNotificationRequest(BaseModel):
    """Request for testing WhatsApp notifications"""
    type: str = Field(..., description="Notification type: 'complete', 'summary', or 'recovery'")
    site_id: Optional[str] = Field(None, description="Optional site ID for testing")


class ScanSitesWithAlertsResponse(BaseModel):
    """Response for scan with WhatsApp alerts"""
    success: bool
    message: str
    summary: Dict[str, Any]
    notifications_sent: Dict[str, Any]


class CreatePostMortemRequest(BaseModel):
    """Request for creating a post-mortem"""
    alert_event_id: int = Field(..., description="Alert event ID")
    title: Optional[str] = Field(None, description="Post-mortem title")
    summary: Optional[str] = Field(None, description="Incident summary")
    root_cause: Optional[str] = Field(None, description="Root cause analysis")
    impact_description: Optional[str] = Field(None, description="Impact description")
    author: Optional[str] = Field(None, description="Author name")
    timeline_events: Optional[List[Dict[str, Any]]] = Field(None, description="Timeline events")
    preventive_actions: Optional[List[Dict[str, Any]]] = Field(None, description="Preventive actions")
    action_items: Optional[List[Dict[str, Any]]] = Field(None, description="Action items")


class UpdatePostMortemRequest(BaseModel):
    """Request for updating a post-mortem"""
    title: Optional[str] = None
    summary: Optional[str] = None
    root_cause: Optional[str] = None
    trigger: Optional[str] = None
    impact_description: Optional[str] = None
    resolution_description: Optional[str] = None
    lessons_learned: Optional[str] = None
    timeline_events: Optional[List[Dict[str, Any]]] = None
    response_actions: Optional[List[Dict[str, Any]]] = None
    preventive_actions: Optional[List[Dict[str, Any]]] = None
    action_items: Optional[List[Dict[str, Any]]] = None


# ============== Site Monitoring Endpoints ==============

@router.post("/scan-sites", response_model=ScanSitesResponse)
async def scan_all_sites() -> ScanSitesResponse:
    """
    Scan all sites from UNMS and create alerts for outages.
    This will check all sites and automatically create events for sites that are down or degraded.
    """
    try:
        logger.info("Starting site scan from UNMS")
        summary = await unms_service.scan_all_sites()

        return ScanSitesResponse(
            success=True,
            message=f"Scan completed: {summary['total_sites']} sites checked",
            summary=summary
        )

    except Exception as e:
        logger.error(f"Error scanning sites: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error scanning sites: {str(e)}")


@router.post("/scan-sites-with-alerts", response_model=ScanSitesWithAlertsResponse)
async def scan_sites_with_whatsapp_alerts() -> ScanSitesWithAlertsResponse:
    """
    Scan all sites and send WhatsApp notifications for outages and recoveries.

    This endpoint:
    1. Checks if UISP is available (prevents false alerts)
    2. Scans all sites from UNMS
    3. Detects outages (>95% devices down)
    4. Detects recoveries
    5. Sends WhatsApp alerts (complete + summary messages)
    6. Returns summary of notifications sent

    **Important**: Will NOT send alerts if UISP is unavailable to prevent false positives.
    """
    try:
        logger.info("Starting site scan with WhatsApp alerts")

        result = await unms_service.scan_and_alert_sites_with_whatsapp(whatsapp_service)

        if not result.get('success'):
            error_msg = result.get('error', 'Unknown error')
            logger.error(f"Scan with alerts failed: {error_msg}")
            raise HTTPException(status_code=503, detail=error_msg)

        summary = result.get('summary', {})
        notifications = result.get('notifications', {})

        return ScanSitesWithAlertsResponse(
            success=True,
            message=f"Scan completed: {summary.get('total_sites', 0)} sites checked, "
                    f"{notifications.get('outage_alerts_sent', 0)} outage alerts sent, "
                    f"{notifications.get('recovery_alerts_sent', 0)} recovery alerts sent",
            summary=summary,
            notifications_sent=notifications
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scanning sites with alerts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error scanning sites with alerts: {str(e)}")


@router.post("/test-notification")
async def test_whatsapp_notification(request: TestNotificationRequest) -> Dict[str, Any]:
    """
    Test WhatsApp notification sending.

    Args:
        type: Notification type - 'complete', 'summary', or 'recovery'
        site_id: Optional site ID for testing with real site data

    Examples:
        ```bash
        # Test complete message
        curl -X POST http://localhost:7657/api/v1/alerting/test-notification \\
          -H "Content-Type: application/json" \\
          -d '{"type": "complete"}'

        # Test summary message
        curl -X POST http://localhost:7657/api/v1/alerting/test-notification \\
          -H "Content-Type: application/json" \\
          -d '{"type": "summary", "site_id": "test-site-123"}'
        ```
    """
    try:
        logger.info(f"Testing WhatsApp notification: type={request.type}")

        # Create mock data for testing
        mock_site_data = {
            "identification": {
                "name": "[TEST] Test Site" if not request.site_id else f"[TEST] {request.site_id}",
                "id": request.site_id or "test-site-123"
            },
            "description": {
                "deviceCount": 69,
                "deviceOutageCount": 65,
                "contact": {
                    "name": "Test Contact",
                    "phone": "2324500057",
                    "email": "test@example.com"
                },
                "note": """Tipo de acceso: Ingreso libre
Tiene baterías: Si
Duración estimada: 4 Horas
Nombre: Eden Nis 1697321-01
Teléfono: 0800-999-3336 (24h)
Nodo vecino para recuperación: Arzobispado
AP que se puede utilizar: Hornet_Arzo_Nissan
Se manda guardia solo si: Corte de fibra para grupo
Horarios permitidos: 24h / 365 días"""
            }
        }

        mock_event_data = {
            "detected_at": now_argentina().strftime('%Y-%m-%d %H:%M:%S'),
            "recovered_at": now_argentina().strftime('%H:%M:%S'),
            "downtime_minutes": 155
        }

        # Send appropriate message based on type
        result = {}

        if request.type == "complete":
            complete_msg = whatsapp_service.format_complete_message(mock_site_data, mock_event_data)
            if whatsapp_service.phone_complete:
                result["complete"] = await whatsapp_service.send_message(
                    whatsapp_service.phone_complete,
                    f"🧪 TEST MESSAGE\n\n{complete_msg}"
                )
            else:
                result["complete"] = {"error": "No phone number configured for complete messages"}

        elif request.type == "summary":
            summary_msg = whatsapp_service.format_summary_message(mock_site_data, mock_event_data)
            if whatsapp_service.phone_summary:
                result["summary"] = await whatsapp_service.send_message(
                    whatsapp_service.phone_summary,
                    f"🧪 TEST MESSAGE\n\n{summary_msg}"
                )
            else:
                result["summary"] = {"error": "No phone number configured for summary messages"}

        elif request.type == "recovery":
            recovery_msg = whatsapp_service.format_recovery_message(mock_site_data, mock_event_data)
            results_complete = None
            results_summary = None

            if whatsapp_service.phone_complete:
                results_complete = await whatsapp_service.send_message(
                    whatsapp_service.phone_complete,
                    f"🧪 TEST MESSAGE\n\n{recovery_msg}"
                )

            if whatsapp_service.phone_summary:
                results_summary = await whatsapp_service.send_message(
                    whatsapp_service.phone_summary,
                    f"🧪 TEST MESSAGE\n\n{recovery_msg}"
                )

            result = {
                "complete": results_complete,
                "summary": results_summary
            }

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid type: {request.type}. Must be 'complete', 'summary', or 'recovery'"
            )

        return {
            "success": True,
            "message": f"Test {request.type} notification sent",
            "type": request.type,
            "results": result,
            "whatsapp_enabled": whatsapp_service.enabled,
            "phones_configured": {
                "complete": bool(whatsapp_service.phone_complete),
                "summary": bool(whatsapp_service.phone_summary)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing notification: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error testing notification: {str(e)}")


@router.get("/sites", response_model=List[Dict[str, Any]])
async def get_all_monitored_sites() -> List[Dict[str, Any]]:
    """
    Get all monitored sites from database.
    """
    try:
        sites = site_repo.get_all_sites()

        return [
            {
                "id": site.id,
                "site_id": site.site_id,
                "site_name": site.site_name,
                "site_status": site.site_status,
                "device_count": site.device_count,
                "device_outage_count": site.device_outage_count,
                "outage_percentage": round(site.outage_percentage, 2),
                "is_site_down": site.is_site_down,
                "contact_name": site.contact_name,
                "contact_phone": site.contact_phone,
                "last_checked": to_argentina_isoformat(site.last_checked) if site.last_checked else None,
                "latitude": site.latitude,
                "longitude": site.longitude
            }
            for site in sites
        ]

    except Exception as e:
        logger.error(f"Error getting sites: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting sites: {str(e)}")


@router.get("/sites/outages", response_model=List[Dict[str, Any]])
async def get_sites_with_outages() -> List[Dict[str, Any]]:
    """
    Get only sites that are currently down or degraded.
    """
    try:
        sites = site_repo.get_sites_with_outages()

        return [
            {
                "id": site.id,
                "site_id": site.site_id,
                "site_name": site.site_name,
                "device_count": site.device_count,
                "device_outage_count": site.device_outage_count,
                "outage_percentage": round(site.outage_percentage, 2),
                "is_site_down": site.is_site_down,
                "outage_start": to_argentina_isoformat(site.outage_start) if site.outage_start else None,
                "contact_name": site.contact_name,
                "contact_phone": site.contact_phone,
                "last_checked": to_argentina_isoformat(site.last_checked) if site.last_checked else None
            }
            for site in sites
        ]

    except Exception as e:
        logger.error(f"Error getting sites with outages: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting sites with outages: {str(e)}")


@router.get("/sites/{site_id}", response_model=Dict[str, Any])
async def get_site_details(site_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific site.
    """
    try:
        site = site_repo.get_site_by_id(site_id)

        if not site:
            raise HTTPException(status_code=404, detail=f"Site {site_id} not found")

        return {
            "id": site.id,
            "site_id": site.site_id,
            "site_name": site.site_name,
            "site_status": site.site_status,
            "site_type": site.site_type,
            "address": site.address,
            "latitude": site.latitude,
            "longitude": site.longitude,
            "height": site.height,
            "contact_name": site.contact_name,
            "contact_phone": site.contact_phone,
            "contact_email": site.contact_email,
            "device_count": site.device_count,
            "device_outage_count": site.device_outage_count,
            "outage_percentage": round(site.outage_percentage, 2),
            "is_site_down": site.is_site_down,
            "outage_start": to_argentina_isoformat(site.outage_start) if site.outage_start else None,
            "note": site.note,
            "last_checked": to_argentina_isoformat(site.last_checked) if site.last_checked else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting site details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting site details: {str(e)}")


# ============== Event Management Endpoints ==============

@router.post("/events", response_model=EventResponse)
async def create_custom_event(event: CreateEventRequest) -> EventResponse:
    """
    Create a custom alert event manually.
    """
    try:
        event_data = {
            'event_type': EventType[event.event_type.value.upper()],
            'severity': AlertSeverity[event.severity.value.upper()],
            'status': AlertStatus.ACTIVE,
            'title': event.title,
            'description': event.description,
            'custom_data': str(event.custom_data) if event.custom_data else None
        }

        created_event = event_service.create_custom_event(event_data)

        return EventResponse(
            success=True,
            message="Event created successfully",
            event_id=created_event.id
        )

    except Exception as e:
        logger.error(f"Error creating event: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating event: {str(e)}")


@router.get("/events", response_model=List[Dict[str, Any]])
async def list_events(
        status: Optional[StatusEnum] = Query(None, description="Filter by status"),
        severity: Optional[SeverityEnum] = Query(None, description="Filter by severity"),
        event_type: Optional[EventTypeEnum] = Query(None, description="Filter by event type"),
        limit: int = Query(100, ge=1, le=1000, description="Maximum number of events to return")
) -> List[Dict[str, Any]]:
    """
    List alert events with optional filters.
    """
    try:
        events = event_service.list_events(
            status=status.value if status else None,
            severity=severity.value if severity else None,
            event_type=event_type.value if event_type else None,
            limit=limit
        )

        return [
            {
                "id": event.id,
                "event_type": event.event_type.value,
                "severity": event.severity.value,
                "status": event.status.value,
                "title": event.title,
                "description": event.description,
                "site_id": event.site_id,
                "device_count": event.device_count,
                "outage_count": event.outage_count,
                "outage_percentage": round(event.outage_percentage, 2) if event.outage_percentage else None,
                "acknowledged_by": event.acknowledged_by,
                "acknowledged_at": to_argentina_isoformat(event.acknowledged_at) if event.acknowledged_at else None,
                "resolved_by": event.resolved_by,
                "resolved_at": to_argentina_isoformat(event.resolved_at) if event.resolved_at else None,
                "auto_resolved": event.auto_resolved,
                "created_at": to_argentina_isoformat(event.created_at) if event.created_at else None
            }
            for event in events
        ]

    except Exception as e:
        logger.error(f"Error listing events: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing events: {str(e)}")


@router.get("/events/active", response_model=List[Dict[str, Any]])
async def get_active_events() -> List[Dict[str, Any]]:
    """
    Get all active (unresolved) events.
    """
    try:
        events = event_service.get_active_events()

        return [
            {
                "id": event.id,
                "event_type": event.event_type.value,
                "severity": event.severity.value,
                "title": event.title,
                "description": event.description,
                "site_id": event.site_id,
                "outage_percentage": round(event.outage_percentage, 2) if event.outage_percentage else None,
                "created_at": to_argentina_isoformat(event.created_at) if event.created_at else None
            }
            for event in events
        ]

    except Exception as e:
        logger.error(f"Error getting active events: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting active events: {str(e)}")


@router.get("/events/{event_id}", response_model=Dict[str, Any])
async def get_event_details(event_id: int) -> Dict[str, Any]:
    """
    Get detailed information about a specific event.
    """
    try:
        event = event_service.get_event(event_id)

        if not event:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found")

        return {
            "id": event.id,
            "event_type": event.event_type.value,
            "severity": event.severity.value,
            "status": event.status.value,
            "title": event.title,
            "description": event.description,
            "site_id": event.site_id,
            "device_count": event.device_count,
            "outage_count": event.outage_count,
            "outage_percentage": round(event.outage_percentage, 2) if event.outage_percentage else None,
            "custom_data": event.custom_data,
            "acknowledged_by": event.acknowledged_by,
            "acknowledged_at": to_argentina_isoformat(event.acknowledged_at) if event.acknowledged_at else None,
            "acknowledged_note": event.acknowledged_note,
            "resolved_by": event.resolved_by,
            "resolved_at": to_argentina_isoformat(event.resolved_at) if event.resolved_at else None,
            "resolved_note": event.resolved_note,
            "auto_resolved": event.auto_resolved,
            "created_at": to_argentina_isoformat(event.created_at) if event.created_at else None,
            "updated_at": to_argentina_isoformat(event.updated_at) if event.updated_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting event details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting event details: {str(e)}")


@router.post("/events/{event_id}/acknowledge", response_model=EventResponse)
async def acknowledge_event(event_id: int, request: AcknowledgeEventRequest) -> EventResponse:
    """
    Acknowledge an event (mark that someone is aware of it).
    """
    try:
        event = event_service.acknowledge_event(
            event_id=event_id,
            acknowledged_by=request.acknowledged_by,
            note=request.note
        )

        if not event:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found")

        return EventResponse(
            success=True,
            message=f"Event acknowledged by {request.acknowledged_by}",
            event_id=event.id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error acknowledging event: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error acknowledging event: {str(e)}")


@router.post("/events/{event_id}/resolve", response_model=EventResponse)
async def resolve_event(event_id: int, request: ResolveEventRequest) -> EventResponse:
    """
    Resolve an event (mark as fixed/completed).
    """
    try:
        event = event_service.resolve_event(
            event_id=event_id,
            resolved_by=request.resolved_by,
            note=request.note
        )

        if not event:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found")

        return EventResponse(
            success=True,
            message=f"Event resolved by {request.resolved_by}",
            event_id=event.id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving event: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error resolving event: {str(e)}")


@router.delete("/events/{event_id}", response_model=EventResponse)
async def delete_event(event_id: int) -> EventResponse:
    """
    Delete an event permanently.
    """
    try:
        event_service.delete_event(event_id)

        return EventResponse(
            success=True,
            message=f"Event {event_id} deleted successfully",
            event_id=event_id
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting event: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting event: {str(e)}")


@router.post("/events/{event_id}/notify", response_model=Dict[str, Any])
async def send_event_notification(
    event_id: int,
    message_type: Optional[str] = Query(None, description="Message type: 'complete', 'summary', 'both', or 'recovery'")
) -> Dict[str, Any]:
    """
    Send WhatsApp notification for a specific event.

    Args:
        event_id: Event ID to send notification for
        message_type: Optional - 'complete', 'summary', 'both' (default), or 'recovery' (manual)

    By default sends both messages and auto-detects outage/recovery by event status.
    Use 'recovery' to manually force a recovery message.

    Useful for:
    - Resending failed notifications
    - Manually notifying events
    - Testing notifications with real event data
    - Sending recovery notifications manually

    Examples:
        ```bash
        # Send both messages (default, auto-detect outage/recovery)
        curl -X POST http://190.7.234.37:7657/api/v1/alerting/events/5/notify

        # Send only complete message
        curl -X POST "http://190.7.234.37:7657/api/v1/alerting/events/5/notify?message_type=complete"

        # Send only summary message
        curl -X POST "http://190.7.234.37:7657/api/v1/alerting/events/5/notify?message_type=summary"

        # Force recovery message (manual)
        curl -X POST "http://190.7.234.37:7657/api/v1/alerting/events/5/notify?message_type=recovery"
        ```
    """
    try:
        # Get event
        event = event_repo.get_event_by_id(event_id)
        if not event:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found")

        # Get site data (event.site_id is the numeric DB id, not the UUID)
        from app_fast_api.utils.database import SessionLocal
        from app_fast_api.models.ubiquiti_monitoring.alerting import SiteMonitoring as SiteModel

        db = SessionLocal()
        try:
            site = db.query(SiteModel).filter_by(id=event.site_id).first() if event.site_id else None
        finally:
            db.close()

        if not site:
            raise HTTPException(status_code=404, detail=f"Site for event {event_id} not found")

        # Get full site data from UNMS for complete message
        try:
            sites_data = await unms_service.get_all_sites()
            site_data = next((s for s in sites_data if s.get('identification', {}).get('id') == site.site_id), None)

            if not site_data:
                # Fallback to basic site data
                site_data = {
                    "identification": {"name": site.site_name, "id": site.site_id},
                    "description": {
                        "deviceCount": site.device_count,
                        "deviceOutageCount": site.device_outage_count,
                        "contact": {
                            "name": site.contact_name,
                            "phone": site.contact_phone,
                            "email": site.contact_email
                        }
                    }
                }
        except Exception as e:
            logger.warning(f"Could not get full UNMS data: {e}, using basic site data")
            site_data = {
                "identification": {"name": site.site_name, "id": site.site_id},
                "description": {
                    "deviceCount": site.device_count,
                    "deviceOutageCount": site.device_outage_count,
                    "contact": {
                        "name": site.contact_name,
                        "phone": site.contact_phone,
                        "email": site.contact_email
                    }
                }
            }

        # Prepare event data (in Argentina timezone)
        event_data = {
            "detected_at": format_argentina_datetime(event.created_at if event.created_at else now_argentina())
        }

        # Normalize message_type
        if not message_type:
            message_type = "both"
        message_type = message_type.lower()

        if message_type not in ["complete", "summary", "both", "recovery"]:
            raise HTTPException(status_code=400, detail="message_type must be 'complete', 'summary', 'both', or 'recovery'")

        # Send appropriate notifications based on event type and message_type
        results = {}

        # Handle manual recovery message type
        if message_type == "recovery":
            # Force recovery message regardless of event status
            if event.resolved_at and event.created_at:
                downtime_minutes = int((event.resolved_at - event.created_at).total_seconds() / 60)
            else:
                downtime_minutes = 0

            recovery_event_data = {
                "recovered_at": event.resolved_at if event.resolved_at else now_argentina(),
                "downtime_minutes": downtime_minutes
            }

            recovery_msg = whatsapp_service.format_recovery_message(site_data, recovery_event_data)

            # Send to both numbers
            if whatsapp_service.phone_complete:
                results["complete"] = await whatsapp_service.send_message(
                    whatsapp_service.phone_complete,
                    recovery_msg
                )
            if whatsapp_service.phone_summary:
                results["summary"] = await whatsapp_service.send_message(
                    whatsapp_service.phone_summary,
                    recovery_msg
                )

        elif event.status == AlertStatus.RESOLVED:
            # Send recovery notification
            if event.resolved_at and event.created_at:
                downtime_minutes = int((event.resolved_at - event.created_at).total_seconds() / 60)
            else:
                downtime_minutes = 0

            recovery_event_data = {
                "recovered_at": event.resolved_at if event.resolved_at else now_argentina(),  # Pass datetime, will be formatted in WhatsApp service
                "downtime_minutes": downtime_minutes
            }

            # Format recovery message
            recovery_msg = whatsapp_service.format_recovery_message(site_data, recovery_event_data)

            # Send based on message_type (mutually exclusive)
            if message_type == "complete":
                # Send ONLY complete message
                if whatsapp_service.phone_complete:
                    results["complete"] = await whatsapp_service.send_message(
                        whatsapp_service.phone_complete,
                        recovery_msg
                    )
            elif message_type == "summary":
                # Send ONLY summary message
                if whatsapp_service.phone_summary:
                    results["summary"] = await whatsapp_service.send_message(
                        whatsapp_service.phone_summary,
                        recovery_msg
                    )
            elif message_type == "both":
                # Send both messages
                if whatsapp_service.phone_complete:
                    results["complete"] = await whatsapp_service.send_message(
                        whatsapp_service.phone_complete,
                        recovery_msg
                    )
                if whatsapp_service.phone_summary:
                    results["summary"] = await whatsapp_service.send_message(
                        whatsapp_service.phone_summary,
                        recovery_msg
                    )

        else:
            # Send outage notification
            # Send based on message_type (mutually exclusive)
            if message_type == "complete":
                # Send ONLY complete message
                if whatsapp_service.phone_complete:
                    complete_msg = whatsapp_service.format_complete_message(site_data, event_data)
                    results["complete"] = await whatsapp_service.send_message(
                        whatsapp_service.phone_complete,
                        complete_msg
                    )
            elif message_type == "summary":
                # Send ONLY summary message
                if whatsapp_service.phone_summary:
                    summary_msg = whatsapp_service.format_summary_message(site_data, event_data)
                    results["summary"] = await whatsapp_service.send_message(
                        whatsapp_service.phone_summary,
                        summary_msg
                    )
            elif message_type == "both":
                # Send both messages
                complete_msg = whatsapp_service.format_complete_message(site_data, event_data)
                summary_msg = whatsapp_service.format_summary_message(site_data, event_data)

                if whatsapp_service.phone_complete:
                    results["complete"] = await whatsapp_service.send_message(
                        whatsapp_service.phone_complete,
                        complete_msg
                    )
                if whatsapp_service.phone_summary:
                    results["summary"] = await whatsapp_service.send_message(
                        whatsapp_service.phone_summary,
                        summary_msg
                    )

        # Count successes
        notifications_sent = 0
        if results.get('complete', {}).get('success'):
            notifications_sent += 1
        if results.get('summary', {}).get('success'):
            notifications_sent += 1

        return {
            "success": True,
            "message": f"Notifications sent for event {event_id}",
            "event_id": event_id,
            "event_title": event.title,
            "event_status": event.status.value,
            "notifications_sent": notifications_sent,
            "results": results
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending notification for event {event_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error sending notification: {str(e)}")


# ============== Post-Mortem Endpoints ==============

@router.post("/post-mortems")
async def create_post_mortem(request: CreatePostMortemRequest) -> Dict[str, Any]:
    """
    Create a new post-mortem for an incident.
    """
    try:
        post_mortem = pm_service.create_post_mortem(
            alert_event_id=request.alert_event_id,
            data=request.dict(exclude_none=True)
        )

        return {
            "success": True,
            "message": "Post-mortem created successfully",
            "post_mortem": post_mortem
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating post-mortem: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating post-mortem: {str(e)}")


@router.get("/post-mortems")
async def list_post_mortems(
        status: Optional[str] = Query(None, description="Filter by status (draft, in_progress, completed, reviewed)"),
        limit: int = Query(100, ge=1, le=1000)
) -> List[Dict[str, Any]]:
    """
    List all post-mortems with optional filters.
    """
    try:
        post_mortems = pm_service.list_post_mortems(status=status, limit=limit)

        return post_mortems

    except Exception as e:
        logger.error(f"Error listing post-mortems: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing post-mortems: {str(e)}")


@router.get("/post-mortems/{pm_id}")
async def get_post_mortem(pm_id: int) -> Dict[str, Any]:
    """
    Get detailed post-mortem by ID.
    """
    try:
        post_mortem = pm_service.get_post_mortem(pm_id)

        if not post_mortem:
            raise HTTPException(status_code=404, detail=f"Post-mortem {pm_id} not found")

        return post_mortem

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting post-mortem: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting post-mortem: {str(e)}")


@router.put("/post-mortems/{pm_id}")
async def update_post_mortem(pm_id: int, request: UpdatePostMortemRequest) -> Dict[str, Any]:
    """
    Update post-mortem data.
    """
    try:
        post_mortem = pm_service.update_post_mortem(
            pm_id=pm_id,
            data=request.dict(exclude_none=True)
        )

        return {
            "success": True,
            "message": "Post-mortem updated successfully",
            "post_mortem": post_mortem
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating post-mortem: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating post-mortem: {str(e)}")


@router.post("/post-mortems/{pm_id}/complete")
async def complete_post_mortem(pm_id: int) -> Dict[str, Any]:
    """
    Mark post-mortem as completed.
    """
    try:
        post_mortem = pm_service.complete_post_mortem(pm_id)

        return {
            "success": True,
            "message": "Post-mortem marked as completed",
            "post_mortem": post_mortem
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error completing post-mortem: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error completing post-mortem: {str(e)}")


@router.post("/post-mortems/{pm_id}/review")
async def review_post_mortem(pm_id: int) -> Dict[str, Any]:
    """
    Mark post-mortem as reviewed.
    """
    try:
        post_mortem = pm_service.review_post_mortem(pm_id)

        return {
            "success": True,
            "message": "Post-mortem marked as reviewed",
            "post_mortem": post_mortem
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error reviewing post-mortem: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error reviewing post-mortem: {str(e)}")


@router.get("/post-mortems/{pm_id}/report")
async def get_post_mortem_report(pm_id: int) -> Dict[str, Any]:
    """
    Generate comprehensive post-mortem report with metrics.
    """
    try:
        report = pm_service.generate_report(pm_id)

        return report

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")


@router.delete("/post-mortems/{pm_id}")
async def delete_post_mortem(pm_id: int) -> Dict[str, Any]:
    """
    Delete a post-mortem permanently.
    """
    try:
        pm_service.delete_post_mortem(pm_id)

        return {
            "success": True,
            "message": f"Post-mortem {pm_id} deleted successfully"
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting post-mortem: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting post-mortem: {str(e)}")


# ============== Polling Control Endpoints ==============

@router.post("/polling/start")
async def start_polling() -> Dict[str, Any]:
    """
    Start automatic site scanning with WhatsApp alerts.
    """
    try:
        if not polling_service:
            raise HTTPException(status_code=503, detail="Polling service not initialized")

        result = await polling_service.start_polling()

        return result

    except Exception as e:
        logger.error(f"Error starting polling: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error starting polling: {str(e)}")


@router.post("/polling/stop")
async def stop_polling() -> Dict[str, Any]:
    """
    Stop automatic site scanning.
    """
    try:
        if not polling_service:
            raise HTTPException(status_code=503, detail="Polling service not initialized")

        result = await polling_service.stop_polling()

        return result

    except Exception as e:
        logger.error(f"Error stopping polling: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error stopping polling: {str(e)}")


@router.get("/polling/status")
async def get_polling_status() -> Dict[str, Any]:
    """
    Get current polling status and last scan results.
    """
    try:
        if not polling_service:
            return {
                "is_running": False,
                "enabled": False,
                "error": "Polling service not initialized"
            }

        return polling_service.get_status()

    except Exception as e:
        logger.error(f"Error getting polling status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting polling status: {str(e)}")


# ============== Health Check ==============

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for alerting service.
    """
    return {
        "status": "healthy",
        "service": "alerting",
        "unms_configured": bool(UISP_BASE_URL and UISP_TOKEN),
        "whatsapp_enabled": whatsapp_service.enabled,
        "polling_running": polling_service.is_running if polling_service else False
    }
