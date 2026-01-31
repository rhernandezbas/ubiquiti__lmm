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
from app_fast_api.repositories.alerting_repositories import SiteMonitoringRepository, AlertEventRepository
from app_fast_api.models.ubiquiti_monitoring.alerting import AlertSeverity, AlertStatus, EventType
from app_fast_api.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/alerting", tags=["alerting"])

# Initialize services (singleton pattern)
UISP_BASE_URL = os.getenv("UISP_BASE_URL", "")
UISP_TOKEN = os.getenv("UISP_TOKEN", "")

site_repo = SiteMonitoringRepository()
event_repo = AlertEventRepository()

unms_service = UNMSAlertingService(
    base_url=UISP_BASE_URL,
    token=UISP_TOKEN,
    site_repo=site_repo,
    event_repo=event_repo,
    outage_threshold=95.0  # Default 95%
)

event_service = AlertEventService(event_repo=event_repo)


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
                "last_checked": site.last_checked.isoformat() if site.last_checked else None,
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
                "contact_name": site.contact_name,
                "contact_phone": site.contact_phone,
                "last_checked": site.last_checked.isoformat() if site.last_checked else None
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
            "note": site.note,
            "last_checked": site.last_checked.isoformat() if site.last_checked else None
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
                "acknowledged_at": event.acknowledged_at.isoformat() if event.acknowledged_at else None,
                "resolved_by": event.resolved_by,
                "resolved_at": event.resolved_at.isoformat() if event.resolved_at else None,
                "auto_resolved": event.auto_resolved,
                "created_at": event.created_at.isoformat() if event.created_at else None
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
                "created_at": event.created_at.isoformat() if event.created_at else None
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
            "acknowledged_at": event.acknowledged_at.isoformat() if event.acknowledged_at else None,
            "acknowledged_note": event.acknowledged_note,
            "resolved_by": event.resolved_by,
            "resolved_at": event.resolved_at.isoformat() if event.resolved_at else None,
            "resolved_note": event.resolved_note,
            "auto_resolved": event.auto_resolved,
            "created_at": event.created_at.isoformat() if event.created_at else None,
            "updated_at": event.updated_at.isoformat() if event.updated_at else None
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


# ============== Health Check ==============

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for alerting service.
    """
    return {
        "status": "healthy",
        "service": "alerting",
        "unms_configured": bool(UISP_BASE_URL and UISP_TOKEN)
    }
