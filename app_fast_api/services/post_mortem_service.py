"""
Post-Mortem Service for incident analysis and documentation.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from app_fast_api.repositories.alerting_repositories import PostMortemRepository, AlertEventRepository
from app_fast_api.models.ubiquiti_monitoring.post_mortem import PostMortemStatus
from app_fast_api.utils.logger import get_logger
from app_fast_api.utils.timezone import to_argentina_isoformat, now_argentina

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

    def create_post_mortem(self, alert_event_id: Optional[int] = None, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create a new post-mortem, optionally linked to an alert event.

        Args:
            alert_event_id: ID of the alert event (optional)
            data: Post-mortem data

        Returns:
            Created post-mortem data
        """
        event = None

        # If alert_event_id is provided, try to get event data and check for duplicates
        if alert_event_id is not None:
            # Try to get event data if it exists (for populating defaults)
            # Note: event might be None if it was deleted, that's OK
            event = self.event_repo.get_event_by_id(alert_event_id)

            # Always check for duplicate post-mortem (even if event doesn't exist anymore)
            existing = self.pm_repo.get_post_mortem_by_event(alert_event_id)
            if existing:
                raise ValueError(f"Ya existe un post-mortem para el evento #{alert_event_id}")

        # Prepare data with defaults
        # Use event data if available, otherwise use provided data or defaults
        default_title = f"Post-Mortem: {event.title}" if event else data.get('title', 'Post-Mortem Sin Título')
        default_incident_start = event.created_at if event else data.get('incident_start', now_argentina())
        default_incident_end = event.resolved_at if event else data.get('incident_end')
        default_severity = event.severity.value if (event and event.severity) else data.get('severity', 'medium')

        pm_data = {
            'alert_event_id': alert_event_id,
            'title': data.get('title', default_title),
            'status': PostMortemStatus.DRAFT,
            'incident_start': data.get('incident_start') or default_incident_start,
            'incident_end': data.get('incident_end') or default_incident_end,
            'summary': data.get('summary', ''),
            'root_cause': data.get('root_cause'),
            'trigger': data.get('trigger'),
            'impact_description': data.get('impact_description'),
            'affected_users': data.get('affected_users'),
            'affected_devices': data.get('affected_devices'),
            'severity': data.get('severity', default_severity),
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
            'created_at': now_argentina(),
            'updated_at': now_argentina()
        }

        # Set timestamps (not durations)
        # detection_time: When the incident was detected (required field)
        if event:
            pm_data['detection_time'] = event.created_at or now_argentina()
            # response_time: When response started (acknowledged timestamp)
            pm_data['response_time'] = event.acknowledged_at  # Can be None
        else:
            # For standalone post-mortems, use provided times or defaults
            pm_data['detection_time'] = data.get('detection_time', pm_data['incident_start'])
            pm_data['response_time'] = data.get('response_time')  # Can be None

        # resolution_time: When incident was resolved (end timestamp)
        pm_data['resolution_time'] = pm_data['incident_end']  # Can be None

        # Calculate downtime in minutes if both start and end are available
        if pm_data['incident_end'] and pm_data['incident_start']:
            resolution_delta = pm_data['incident_end'] - pm_data['incident_start']
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

        # Recalculate downtime if dates changed
        if 'incident_start' in data or 'incident_end' in data:
            incident_start = data.get('incident_start') or post_mortem.incident_start
            incident_end = data.get('incident_end') or post_mortem.incident_end

            if incident_end and incident_start:
                resolution_delta = incident_end - incident_start
                # Only update downtime_minutes (resolution_time is a timestamp, not a duration)
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
        # Calculate durations from timestamps
        detection_delay_minutes = None
        if post_mortem.incident_start and post_mortem.detection_time:
            detection_delay_minutes = int((post_mortem.detection_time - post_mortem.incident_start).total_seconds() / 60)

        response_delay_minutes = None
        if post_mortem.detection_time and post_mortem.response_time:
            response_delay_minutes = int((post_mortem.response_time - post_mortem.detection_time).total_seconds() / 60)

        total_resolution_minutes = None
        if post_mortem.incident_start and post_mortem.resolution_time:
            total_resolution_minutes = int((post_mortem.resolution_time - post_mortem.incident_start).total_seconds() / 60)

        metrics = {
            'mttr_minutes': post_mortem.downtime_minutes,
            'mttr_hours': round(post_mortem.downtime_minutes / 60, 2) if post_mortem.downtime_minutes else None,
            'detection_delay_minutes': detection_delay_minutes,  # Time from start to detection
            'response_delay_minutes': response_delay_minutes,  # Time from detection to response
            'total_resolution_minutes': total_resolution_minutes  # Total time from start to resolution
        }

        return {
            'post_mortem': pm_data,
            'metrics': metrics,
            'generated_at': now_argentina().isoformat()
        }

    def link_related_incidents(self, parent_id: int, child_id: int,
                              relationship_type: str = 'related_root_cause',
                              description: str = None,
                              linked_by: str = None) -> Dict[str, Any]:
        """Vincular un incidente secundario a uno principal."""
        try:
            relationship = self.pm_repo.link_post_mortems(
                parent_id, child_id, relationship_type, description, linked_by
            )

            return {
                'success': True,
                'message': f'Post-mortem {child_id} vinculado como secundario de {parent_id}',
                'relationship': {
                    'id': relationship.id,
                    'parent_id': relationship.parent_post_mortem_id,
                    'child_id': relationship.child_post_mortem_id,
                    'type': relationship.relationship_type,
                    'description': relationship.description,
                    'linked_by': relationship.linked_by,
                    'created_at': to_argentina_isoformat(relationship.created_at)
                }
            }
        except ValueError as e:
            raise ValueError(str(e))

    def unlink_related_incidents(self, parent_id: int, child_id: int) -> Dict[str, Any]:
        """Desvincular un incidente secundario."""
        try:
            self.pm_repo.unlink_post_mortems(parent_id, child_id)
            return {
                'success': True,
                'message': f'Post-mortem {child_id} desvinculado de {parent_id}'
            }
        except ValueError as e:
            raise ValueError(str(e))

    def get_related_incidents(self, pm_id: int) -> Dict[str, Any]:
        """Obtener todos los incidentes relacionados con un PM."""
        try:
            related = self.pm_repo.get_related_post_mortems(pm_id)

            return {
                'post_mortem_id': pm_id,
                'parent': self._serialize_post_mortem(related['parent']) if related['parent'] else None,
                'children': [self._serialize_post_mortem(c) for c in related['children']],
                'is_primary': related['is_primary'],
                'is_secondary': related['is_secondary'],
                'total_related': (1 if related['parent'] else 0) + len(related['children'])
            }
        except ValueError as e:
            raise ValueError(str(e))

    def list_primary_post_mortems(self, status: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Listar solo post-mortems primarios (para NOC Dashboard)."""
        status_enum = None
        if status:
            try:
                status_enum = PostMortemStatus[status.upper()]
            except KeyError:
                raise ValueError(f"Invalid status: {status}")

        post_mortems = self.pm_repo.get_all_primary_post_mortems(status_enum, limit)

        # Agregar count de secundarios
        result = []
        for pm in post_mortems:
            serialized = self._serialize_post_mortem(pm)
            serialized['child_count'] = len(pm.child_relationships)
            result.append(serialized)

        return result

    def _serialize_post_mortem(self, pm) -> Dict[str, Any]:
        """Serialize post-mortem to dict."""
        return {
            'id': pm.id,
            'alert_event_id': pm.alert_event_id,
            'title': pm.title,
            'status': pm.status.value if pm.status else None,
            'incident_start': to_argentina_isoformat(pm.incident_start) if pm.incident_start else None,
            'incident_end': to_argentina_isoformat(pm.incident_end) if pm.incident_end else None,
            'detection_time': to_argentina_isoformat(pm.detection_time) if pm.detection_time else None,
            'response_time': to_argentina_isoformat(pm.response_time) if pm.response_time else None,
            'resolution_time': to_argentina_isoformat(pm.resolution_time) if pm.resolution_time else None,
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
            'created_at': to_argentina_isoformat(pm.created_at) if pm.created_at else None,
            'updated_at': to_argentina_isoformat(pm.updated_at) if pm.updated_at else None,
            'completed_at': to_argentina_isoformat(pm.completed_at) if pm.completed_at else None,
            'reviewed_at': to_argentina_isoformat(pm.reviewed_at) if pm.reviewed_at else None
        }
