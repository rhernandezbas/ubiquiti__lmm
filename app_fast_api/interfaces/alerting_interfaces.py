"""Interfaces for alerting repositories."""

from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

from app_fast_api.models.ubiquiti_monitoring.alerting import SiteMonitoring, AlertEvent, AlertStatus, AlertSeverity, EventType


class ISiteMonitoringRepository(ABC):
    """Interface for the SiteMonitoring repository."""

    @abstractmethod
    def create_or_update_site(self, site_data: dict) -> SiteMonitoring:
        """Create or update a site monitoring record."""
        pass  # pragma: no cover

    @abstractmethod
    def get_site_by_id(self, site_id: str) -> Optional[SiteMonitoring]:
        """Get site by UNMS site ID."""
        pass  # pragma: no cover

    @abstractmethod
    def get_all_sites(self) -> List[SiteMonitoring]:
        """Get all monitored sites."""
        pass  # pragma: no cover

    @abstractmethod
    def get_sites_with_outages(self) -> List[SiteMonitoring]:
        """Get sites that are currently down or degraded."""
        pass  # pragma: no cover

    @abstractmethod
    def delete_site(self, site_id: str) -> None:
        """Delete a site monitoring record."""
        pass  # pragma: no cover


class IAlertEventRepository(ABC):
    """Interface for the AlertEvent repository."""

    @abstractmethod
    def create_event(self, event_data: dict) -> AlertEvent:
        """Create a new alert event."""
        pass  # pragma: no cover

    @abstractmethod
    def get_event_by_id(self, event_id: int) -> Optional[AlertEvent]:
        """Get event by ID."""
        pass  # pragma: no cover

    @abstractmethod
    def get_all_events(self,
                       status: Optional[AlertStatus] = None,
                       severity: Optional[AlertSeverity] = None,
                       event_type: Optional[EventType] = None,
                       limit: int = 100) -> List[AlertEvent]:
        """Get all events with optional filters."""
        pass  # pragma: no cover

    @abstractmethod
    def get_active_events(self) -> List[AlertEvent]:
        """Get all active events."""
        pass  # pragma: no cover

    @abstractmethod
    def get_events_by_site(self, site_id: int) -> List[AlertEvent]:
        """Get all events for a specific site."""
        pass  # pragma: no cover

    @abstractmethod
    def update_event_status(self, event_id: int, status: AlertStatus) -> Optional[AlertEvent]:
        """Update event status."""
        pass  # pragma: no cover

    @abstractmethod
    def acknowledge_event(self, event_id: int, acknowledged_by: str, note: Optional[str] = None) -> Optional[AlertEvent]:
        """Acknowledge an event."""
        pass  # pragma: no cover

    @abstractmethod
    def resolve_event(self, event_id: int, resolved_by: str, note: Optional[str] = None, auto_resolved: bool = False) -> Optional[AlertEvent]:
        """Resolve an event."""
        pass  # pragma: no cover

    @abstractmethod
    def delete_event(self, event_id: int) -> None:
        """Delete an event."""
        pass  # pragma: no cover

    @abstractmethod
    def get_events_by_date_range(self, start_date: datetime, end_date: datetime) -> List[AlertEvent]:
        """Get events within a date range."""
        pass  # pragma: no cover
