"""
Post-Mortem Service for incident analysis and documentation.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from app_fast_api.repositories.alerting_repositories import PostMortemRepository, AlertEventRepository
from app_fast_api.models.ubiquiti_monitoring.post_mortem import PostMortemStatus
from app_fast_api.utils.logger import get_logger

logger = get_logger(__name__)


class PostMortemService:
    """Service for managing post-mortem incident analysis."""

    def __init__(self, pm_repo: PostMortemRepository, event_repo: AlertEventRepository):
        """
        Initialize post-mortem service.

        Args:
            pm_repo: Post-mortem repository
            event_repo: Alert event repository
        """
        self.pm_repo = pm_repo
        self.event_repo = event_repo

    def create_post_mortem(self, alert_event_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new post-mortem for an alert event.

        Args:
            alert_event_id: ID of the alert event
            data: Post-mortem data

        Returns:
            Created post-mortem data
        """
        # Verify event exists
        event = self.event_repo.get_event_by_id(alert_event_id)
        if not event:
            raise ValueError(f"Alert event {alert_event_id} not found")

        # Check if post-mortem already exists for this event
        existing = self.pm_repo.get_post_mortem_by_event(alert_event_id)
        if existing:
            raise ValueError(f"Post-mortem already exists for event {alert_event_id}")

        # Prepare data
        pm_data = {
            'alert_event_id': alert_event_id,
            'title': data.get('title', f"Post-Mortem: {event.title}"),
            'status': PostMortemStatus.DRAFT,
            'incident_start': data.get('incident_start') or event.created_at,
            'incident_end': data.get('incident_end') or event.resolved_at,
            'summary': data.get('summary', ''),
            'root_cause': data.get('root_cause'),
            'trigger': data.get('trigger'),
            'impact_description': data.get('impact_description'),
            'affected_users': data.get('affected_users'),
            'affected_devices': data.get('affected_devices'),
            'severity': data.get('severity', event.severity.value if event.severity else 'medium'),
            'customer_impact': data.get('customer_impact'),
            'timeline_events': json.dumps(data.get('timeline_events', [])),
            'response_actions': json.dumps(data.get('response_actions', [])),
            'resolution_description': data.get('resolution_description'),
            'preventive_actions': json.dumps(data.get('preventive_actions', [])),
            'lessons_learned': data.get('lessons_learned'),
            'action_items': json.dumps(data.get('action_items', [])),
            'author': data.get('author'),
            'reviewers': json.dumps(data.get('reviewers', [])),
            'contributors': json.dumps(data.get('contributors', [])),
            'tags': json.dumps(data.get('tags', [])),
            'related_incidents': json.dumps(data.get('related_incidents', [])),
            'external_links': json.dumps(data.get('external_links', [])),
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }

        # Calculate times if available
        if pm_data['incident_start'] and event.created_at:
            detection_delta = event.created_at - pm_data['incident_start']
            pm_data['detection_time'] = int(detection_delta.total_seconds() / 60)

        if event.acknowledged_at and event.created_at:
            response_delta = event.acknowledged_at - event.created_at
            pm_data['response_time'] = int(response_delta.total_seconds() / 60)

        if pm_data['incident_end'] and pm_data['incident_start']:
            resolution_delta = pm_data['incident_end'] - pm_data['incident_start']
            pm_data['resolution_time'] = int(resolution_delta.total_seconds() / 60)
            pm_data['downtime_minutes'] = int(resolution_delta.total_seconds() / 60)

        post_mortem = self.pm_repo.create_post_mortem(pm_data)

        logger.info(f"Created post-mortem {post_mortem.id} for event {alert_event_id}")

        return self._serialize_post_mortem(post_mortem)

    def get_post_mortem(self, pm_id: int) -> Optional[Dict[str, Any]]:
        """
        Get post-mortem by ID.

        Args:
            pm_id: Post-mortem ID

        Returns:
            Post-mortem data or None
        """
        post_mortem = self.pm_repo.get_post_mortem_by_id(pm_id)
        if not post_mortem:
            return None

        return self._serialize_post_mortem(post_mortem)

    def list_post_mortems(self, status: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        List post-mortems with optional filters.

        Args:
            status: Filter by status
            limit: Maximum number of results

        Returns:
            List of post-mortem data
        """
        status_enum = PostMortemStatus[status.upper()] if status else None
        post_mortems = self.pm_repo.get_all_post_mortems(status=status_enum, limit=limit)

        return [self._serialize_post_mortem(pm) for pm in post_mortems]

    def update_post_mortem(self, pm_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update post-mortem data.

        Args:
            pm_id: Post-mortem ID
            data: Updated data

        Returns:
            Updated post-mortem data
        """
        post_mortem = self.pm_repo.get_post_mortem_by_id(pm_id)
        if not post_mortem:
            raise ValueError(f"Post-mortem {pm_id} not found")

        # Prepare update data
        update_data = {}

        # Simple fields
        simple_fields = [
            'title', 'summary', 'root_cause', 'trigger', 'impact_description',
            'affected_users', 'affected_devices', 'severity', 'customer_impact',
            'resolution_description', 'lessons_learned', 'author',
            'incident_start', 'incident_end'
        ]

        for field in simple_fields:
            if field in data:
                update_data[field] = data[field]

        # JSON fields
        json_fields = [
            'timeline_events', 'response_actions', 'preventive_actions',
            'action_items', 'reviewers', 'contributors', 'tags',
            'related_incidents', 'external_links'
        ]

        for field in json_fields:
            if field in data:
                update_data[field] = json.dumps(data[field])

        # Recalculate times if dates changed
        if 'incident_start' in data or 'incident_end' in data:
            incident_start = data.get('incident_start') or post_mortem.incident_start
            incident_end = data.get('incident_end') or post_mortem.incident_end

            if incident_end and incident_start:
                resolution_delta = incident_end - incident_start
                update_data['resolution_time'] = int(resolution_delta.total_seconds() / 60)
                update_data['downtime_minutes'] = int(resolution_delta.total_seconds() / 60)

        updated_pm = self.pm_repo.update_post_mortem(pm_id, update_data)

        logger.info(f"Updated post-mortem {pm_id}")

        return self._serialize_post_mortem(updated_pm)

    def complete_post_mortem(self, pm_id: int) -> Dict[str, Any]:
        """
        Mark post-mortem as completed.

        Args:
            pm_id: Post-mortem ID

        Returns:
            Updated post-mortem data
        """
        post_mortem = self.pm_repo.update_status(pm_id, PostMortemStatus.COMPLETED)
        if not post_mortem:
            raise ValueError(f"Post-mortem {pm_id} not found")

        logger.info(f"Marked post-mortem {pm_id} as completed")

        return self._serialize_post_mortem(post_mortem)

    def review_post_mortem(self, pm_id: int) -> Dict[str, Any]:
        """
        Mark post-mortem as reviewed.

        Args:
            pm_id: Post-mortem ID

        Returns:
            Updated post-mortem data
        """
        post_mortem = self.pm_repo.update_status(pm_id, PostMortemStatus.REVIEWED)
        if not post_mortem:
            raise ValueError(f"Post-mortem {pm_id} not found")

        logger.info(f"Marked post-mortem {pm_id} as reviewed")

        return self._serialize_post_mortem(post_mortem)

    def delete_post_mortem(self, pm_id: int) -> None:
        """
        Delete post-mortem.

        Args:
            pm_id: Post-mortem ID
        """
        self.pm_repo.delete_post_mortem(pm_id)
        logger.info(f"Deleted post-mortem {pm_id}")

    def calculate_mttr(self, pm_id: int) -> Optional[int]:
        """
        Calculate Mean Time To Recovery for a post-mortem.

        Args:
            pm_id: Post-mortem ID

        Returns:
            MTTR in minutes or None
        """
        post_mortem = self.pm_repo.get_post_mortem_by_id(pm_id)
        if not post_mortem:
            return None

        return post_mortem.downtime_minutes

    def generate_report(self, pm_id: int) -> Dict[str, Any]:
        """
        Generate a comprehensive report for a post-mortem.

        Args:
            pm_id: Post-mortem ID

        Returns:
            Report data
        """
        post_mortem = self.pm_repo.get_post_mortem_by_id(pm_id)
        if not post_mortem:
            raise ValueError(f"Post-mortem {pm_id} not found")

        pm_data = self._serialize_post_mortem(post_mortem)

        # Calculate additional metrics
        metrics = {
            'mttr_minutes': post_mortem.downtime_minutes,
            'mttr_hours': round(post_mortem.downtime_minutes / 60, 2) if post_mortem.downtime_minutes else None,
            'detection_time_minutes': post_mortem.detection_time,
            'response_time_minutes': post_mortem.response_time,
            'resolution_time_minutes': post_mortem.resolution_time
        }

        return {
            'post_mortem': pm_data,
            'metrics': metrics,
            'generated_at': datetime.now().isoformat()
        }

    def _serialize_post_mortem(self, pm) -> Dict[str, Any]:
        """Serialize post-mortem to dict."""
        return {
            'id': pm.id,
            'alert_event_id': pm.alert_event_id,
            'title': pm.title,
            'status': pm.status.value if pm.status else None,
            'incident_start': pm.incident_start.isoformat() if pm.incident_start else None,
            'incident_end': pm.incident_end.isoformat() if pm.incident_end else None,
            'detection_time': pm.detection_time.isoformat() if pm.detection_time else None,
            'response_time': pm.response_time.isoformat() if pm.response_time else None,
            'resolution_time': pm.resolution_time.isoformat() if pm.resolution_time else None,
            'summary': pm.summary,
            'impact_description': pm.impact_description,
            'root_cause': pm.root_cause,
            'trigger': pm.trigger,
            'affected_users': pm.affected_users,
            'affected_devices': pm.affected_devices,
            'downtime_minutes': pm.downtime_minutes,
            'severity': pm.severity,
            'customer_impact': pm.customer_impact,
            'timeline_events': pm.timeline_events if pm.timeline_events else [],
            'response_actions': pm.response_actions if pm.response_actions else [],
            'resolution_description': pm.resolution_description,
            'preventive_actions': pm.preventive_actions if pm.preventive_actions else [],
            'lessons_learned': pm.lessons_learned,
            'action_items': pm.action_items if pm.action_items else [],
            'author': pm.author,
            'reviewers': pm.reviewers if pm.reviewers else [],
            'contributors': pm.contributors if pm.contributors else [],
            'tags': pm.tags if pm.tags else [],
            'related_incidents': pm.related_incidents if pm.related_incidents else [],
            'external_links': pm.external_links if pm.external_links else [],
            'created_at': pm.created_at.isoformat() if pm.created_at else None,
            'updated_at': pm.updated_at.isoformat() if pm.updated_at else None,
            'completed_at': pm.completed_at.isoformat() if pm.completed_at else None,
            'reviewed_at': pm.reviewed_at.isoformat() if pm.reviewed_at else None
        }
