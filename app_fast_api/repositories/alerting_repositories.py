"""Repositories for alerting data."""

from typing import List, Optional
from datetime import datetime
from sqlalchemy import and_, desc, or_

from app_fast_api.utils.database import SessionLocal
from app_fast_api.models.ubiquiti_monitoring.alerting import SiteMonitoring, AlertEvent, AlertStatus, AlertSeverity, EventType
from app_fast_api.models.ubiquiti_monitoring.post_mortem import AlertNotification, PostMortem, NotificationStatus, PostMortemStatus
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


class AlertNotificationRepository:
    """Alert notification repository for tracking sent notifications."""

    def create_notification(self, notification_data: dict) -> AlertNotification:
        """Create a new notification record."""
        db = SessionLocal()
        try:
            notification = AlertNotification(**notification_data)
            db.add(notification)
            db.commit()
            db.refresh(notification)
            logger.info(f"Created notification {notification.id} for channel {notification.channel.value}")
            return notification
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating notification: {str(e)}")
            raise RuntimeError(f"Database error: {str(e)}") from e
        finally:
            db.close()

    def get_notification_by_id(self, notification_id: int) -> Optional[AlertNotification]:
        """Get notification by ID."""
        db = SessionLocal()
        try:
            return db.query(AlertNotification).filter_by(id=notification_id).first()
        finally:
            db.close()

    def get_notifications_by_event(self, event_id: int) -> List[AlertNotification]:
        """Get all notifications for an event."""
        db = SessionLocal()
        try:
            return db.query(AlertNotification).filter_by(alert_event_id=event_id).order_by(
                desc(AlertNotification.created_at)
            ).all()
        finally:
            db.close()

    def get_all_notifications(self, limit: int = 100) -> List[AlertNotification]:
        """Get all notifications."""
        db = SessionLocal()
        try:
            return db.query(AlertNotification).order_by(desc(AlertNotification.created_at)).limit(limit).all()
        finally:
            db.close()

    def get_failed_notifications(self) -> List[AlertNotification]:
        """Get all failed notifications."""
        db = SessionLocal()
        try:
            return db.query(AlertNotification).filter(
                AlertNotification.status == NotificationStatus.FAILED
            ).order_by(desc(AlertNotification.created_at)).all()
        finally:
            db.close()

    def update_notification_status(self, notification_id: int, status: NotificationStatus,
                                   error_message: Optional[str] = None) -> Optional[AlertNotification]:
        """Update notification status."""
        db = SessionLocal()
        try:
            notification = db.query(AlertNotification).filter_by(id=notification_id).first()
            if not notification:
                raise ValueError(f"Notification with id {notification_id} not found")

            notification.status = status
            notification.updated_at = datetime.now()

            if status == NotificationStatus.SENT:
                notification.sent_at = datetime.now()
            elif status == NotificationStatus.FAILED:
                notification.failed_at = datetime.now()
                notification.error_message = error_message

            db.commit()
            db.refresh(notification)
            return notification
        finally:
            db.close()

    def increment_retry_count(self, notification_id: int) -> Optional[AlertNotification]:
        """Increment retry count for a notification."""
        db = SessionLocal()
        try:
            notification = db.query(AlertNotification).filter_by(id=notification_id).first()
            if not notification:
                raise ValueError(f"Notification with id {notification_id} not found")

            notification.retry_count += 1
            notification.updated_at = datetime.now()

            db.commit()
            db.refresh(notification)
            return notification
        finally:
            db.close()


class PostMortemRepository:
    """Post-mortem repository for incident analysis."""

    def create_post_mortem(self, pm_data: dict) -> PostMortem:
        """Create a new post-mortem."""
        db = SessionLocal()
        try:
            post_mortem = PostMortem(**pm_data)
            db.add(post_mortem)
            db.commit()
            db.refresh(post_mortem)
            logger.info(f"Created post-mortem {post_mortem.id} for event {post_mortem.alert_event_id}")
            return post_mortem
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating post-mortem: {str(e)}")
            raise RuntimeError(f"Database error: {str(e)}") from e
        finally:
            db.close()

    def get_post_mortem_by_id(self, pm_id: int) -> Optional[PostMortem]:
        """Get post-mortem by ID."""
        db = SessionLocal()
        try:
            return db.query(PostMortem).filter_by(id=pm_id).first()
        finally:
            db.close()

    def get_post_mortem_by_event(self, event_id: int) -> Optional[PostMortem]:
        """Get post-mortem for a specific event."""
        db = SessionLocal()
        try:
            return db.query(PostMortem).filter_by(alert_event_id=event_id).first()
        finally:
            db.close()

    def get_all_post_mortems(self, status: Optional[PostMortemStatus] = None, limit: int = 100) -> List[PostMortem]:
        """Get all post-mortems with optional status filter."""
        db = SessionLocal()
        try:
            query = db.query(PostMortem)

            if status:
                query = query.filter(PostMortem.status == status)

            return query.order_by(desc(PostMortem.created_at)).limit(limit).all()
        finally:
            db.close()

    def update_post_mortem(self, pm_id: int, update_data: dict) -> Optional[PostMortem]:
        """Update post-mortem data."""
        db = SessionLocal()
        try:
            post_mortem = db.query(PostMortem).filter_by(id=pm_id).first()
            if not post_mortem:
                raise ValueError(f"Post-mortem with id {pm_id} not found")

            for key, value in update_data.items():
                if hasattr(post_mortem, key) and value is not None:
                    setattr(post_mortem, key, value)

            post_mortem.updated_at = datetime.now()

            db.commit()
            db.refresh(post_mortem)
            logger.info(f"Updated post-mortem {pm_id}")
            return post_mortem
        finally:
            db.close()

    def update_status(self, pm_id: int, status: PostMortemStatus) -> Optional[PostMortem]:
        """Update post-mortem status."""
        db = SessionLocal()
        try:
            post_mortem = db.query(PostMortem).filter_by(id=pm_id).first()
            if not post_mortem:
                raise ValueError(f"Post-mortem with id {pm_id} not found")

            post_mortem.status = status
            post_mortem.updated_at = datetime.now()

            if status == PostMortemStatus.COMPLETED:
                post_mortem.completed_at = datetime.now()
            elif status == PostMortemStatus.REVIEWED:
                post_mortem.reviewed_at = datetime.now()

            db.commit()
            db.refresh(post_mortem)
            logger.info(f"Updated post-mortem {pm_id} status to {status.value}")
            return post_mortem
        finally:
            db.close()

    def delete_post_mortem(self, pm_id: int) -> None:
        """Delete a post-mortem."""
        db = SessionLocal()
        try:
            post_mortem = db.query(PostMortem).filter_by(id=pm_id).first()
            if post_mortem:
                db.delete(post_mortem)
                db.commit()
                logger.info(f"Deleted post-mortem {pm_id}")
            else:
                raise ValueError(f"Post-mortem with id {pm_id} not found")
        finally:
            db.close()
