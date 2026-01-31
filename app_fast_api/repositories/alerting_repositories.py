"""Repositories for alerting data."""

from typing import List, Optional
from datetime import datetime
from sqlalchemy import and_, desc, or_

from app_fast_api.utils.database import SessionLocal
from app_fast_api.models.ubiquiti_monitoring.alerting import SiteMonitoring, AlertEvent, AlertStatus, AlertSeverity, EventType
from app_fast_api.interfaces.alerting_interfaces import ISiteMonitoringRepository, IAlertEventRepository
from app_fast_api.utils.logger import get_logger

logger = get_logger(__name__)


class SiteMonitoringRepository(ISiteMonitoringRepository):
    """Site monitoring repository."""

    def create_or_update_site(self, site_data: dict) -> SiteMonitoring:
        """Create or update a site monitoring record."""
        db = SessionLocal()
        try:
            site_id = site_data.get('site_id')

            # Check if site exists
            site = db.query(SiteMonitoring).filter_by(site_id=site_id).first()

            if site:
                # Update existing site
                for key, value in site_data.items():
                    if hasattr(site, key):
                        setattr(site, key, value)
                logger.info(f"Updated site: {site.site_name}")
            else:
                # Create new site
                site = SiteMonitoring(**site_data)
                db.add(site)
                logger.info(f"Created new site: {site_data.get('site_name')}")

            db.commit()
            db.refresh(site)
            return site
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating/updating site: {str(e)}")
            raise RuntimeError(f"Database error: {str(e)}") from e
        finally:
            db.close()

    def get_site_by_id(self, site_id: str) -> Optional[SiteMonitoring]:
        """Get site by UNMS site ID."""
        db = SessionLocal()
        try:
            return db.query(SiteMonitoring).filter_by(site_id=site_id).first()
        finally:
            db.close()

    def get_all_sites(self) -> List[SiteMonitoring]:
        """Get all monitored sites."""
        db = SessionLocal()
        try:
            return db.query(SiteMonitoring).order_by(desc(SiteMonitoring.last_checked)).all()
        finally:
            db.close()

    def get_sites_with_outages(self) -> List[SiteMonitoring]:
        """Get sites that are currently down or degraded."""
        db = SessionLocal()
        try:
            return db.query(SiteMonitoring).filter(
                or_(
                    SiteMonitoring.is_site_down == True,
                    SiteMonitoring.outage_percentage >= 50.0
                )
            ).order_by(desc(SiteMonitoring.outage_percentage)).all()
        finally:
            db.close()

    def delete_site(self, site_id: str) -> None:
        """Delete a site monitoring record."""
        db = SessionLocal()
        try:
            site = db.query(SiteMonitoring).filter_by(site_id=site_id).first()
            if site:
                db.delete(site)
                db.commit()
                logger.info(f"Deleted site: {site.site_name}")
            else:
                raise ValueError(f"Site with id {site_id} not found")
        finally:
            db.close()


class AlertEventRepository(IAlertEventRepository):
    """Alert event repository."""

    def create_event(self, event_data: dict) -> AlertEvent:
        """Create a new alert event."""
        db = SessionLocal()
        try:
            event = AlertEvent(**event_data)
            db.add(event)
            db.commit()
            db.refresh(event)
            logger.info(f"Created event: {event.title} (severity: {event.severity.value})")
            return event
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating event: {str(e)}")
            raise RuntimeError(f"Database error: {str(e)}") from e
        finally:
            db.close()

    def get_event_by_id(self, event_id: int) -> Optional[AlertEvent]:
        """Get event by ID."""
        db = SessionLocal()
        try:
            return db.query(AlertEvent).filter_by(id=event_id).first()
        finally:
            db.close()

    def get_all_events(self,
                       status: Optional[AlertStatus] = None,
                       severity: Optional[AlertSeverity] = None,
                       event_type: Optional[EventType] = None,
                       limit: int = 100) -> List[AlertEvent]:
        """Get all events with optional filters."""
        db = SessionLocal()
        try:
            query = db.query(AlertEvent)

            if status:
                query = query.filter(AlertEvent.status == status)
            if severity:
                query = query.filter(AlertEvent.severity == severity)
            if event_type:
                query = query.filter(AlertEvent.event_type == event_type)

            return query.order_by(desc(AlertEvent.created_at)).limit(limit).all()
        finally:
            db.close()

    def get_active_events(self) -> List[AlertEvent]:
        """Get all active events."""
        db = SessionLocal()
        try:
            return db.query(AlertEvent).filter(
                AlertEvent.status == AlertStatus.ACTIVE
            ).order_by(desc(AlertEvent.created_at)).all()
        finally:
            db.close()

    def get_events_by_site(self, site_id: int) -> List[AlertEvent]:
        """Get all events for a specific site."""
        db = SessionLocal()
        try:
            return db.query(AlertEvent).filter_by(site_id=site_id).order_by(desc(AlertEvent.created_at)).all()
        finally:
            db.close()

    def update_event_status(self, event_id: int, status: AlertStatus) -> Optional[AlertEvent]:
        """Update event status."""
        db = SessionLocal()
        try:
            event = db.query(AlertEvent).filter_by(id=event_id).first()
            if not event:
                raise ValueError(f"Event with id {event_id} not found")

            event.status = status
            event.updated_at = datetime.now()

            db.commit()
            db.refresh(event)
            logger.info(f"Updated event {event_id} status to {status.value}")
            return event
        finally:
            db.close()

    def acknowledge_event(self, event_id: int, acknowledged_by: str, note: Optional[str] = None) -> Optional[AlertEvent]:
        """Acknowledge an event."""
        db = SessionLocal()
        try:
            event = db.query(AlertEvent).filter_by(id=event_id).first()
            if not event:
                raise ValueError(f"Event with id {event_id} not found")

            event.status = AlertStatus.ACKNOWLEDGED
            event.acknowledged_by = acknowledged_by
            event.acknowledged_at = datetime.now()
            event.acknowledged_note = note
            event.updated_at = datetime.now()

            db.commit()
            db.refresh(event)
            logger.info(f"Event {event_id} acknowledged by {acknowledged_by}")
            return event
        finally:
            db.close()

    def resolve_event(self, event_id: int, resolved_by: str, note: Optional[str] = None, auto_resolved: bool = False) -> Optional[AlertEvent]:
        """Resolve an event."""
        db = SessionLocal()
        try:
            event = db.query(AlertEvent).filter_by(id=event_id).first()
            if not event:
                raise ValueError(f"Event with id {event_id} not found")

            event.status = AlertStatus.RESOLVED
            event.resolved_by = resolved_by
            event.resolved_at = datetime.now()
            event.resolved_note = note
            event.auto_resolved = auto_resolved
            event.updated_at = datetime.now()

            db.commit()
            db.refresh(event)
            logger.info(f"Event {event_id} resolved by {resolved_by} (auto: {auto_resolved})")
            return event
        finally:
            db.close()

    def delete_event(self, event_id: int) -> None:
        """Delete an event."""
        db = SessionLocal()
        try:
            event = db.query(AlertEvent).filter_by(id=event_id).first()
            if event:
                db.delete(event)
                db.commit()
                logger.info(f"Deleted event {event_id}")
            else:
                raise ValueError(f"Event with id {event_id} not found")
        finally:
            db.close()

    def get_events_by_date_range(self, start_date: datetime, end_date: datetime) -> List[AlertEvent]:
        """Get events within a date range."""
        db = SessionLocal()
        try:
            return db.query(AlertEvent).filter(
                and_(
                    AlertEvent.created_at >= start_date,
                    AlertEvent.created_at <= end_date
                )
            ).order_by(desc(AlertEvent.created_at)).all()
        finally:
            db.close()
