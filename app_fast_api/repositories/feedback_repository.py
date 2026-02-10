"""
Repository for DeviceAnalysisFeedback operations
"""

from typing import List, Optional
from sqlalchemy.orm import Session

from app_fast_api.models.ubiquiti_monitoring.feedback import DeviceAnalysisFeedback
from app_fast_api.utils.database import SessionLocal
from app_fast_api.utils.logger import get_logger

logger = get_logger(__name__)


class FeedbackRepository:
    """Repository for managing device analysis feedback."""

    def __init__(self):
        """Initialize feedback repository."""
        pass

    def create_feedback(self, feedback_data: dict) -> DeviceAnalysisFeedback:
        """
        Create a new feedback record.

        Args:
            feedback_data: Dictionary with feedback data

        Returns:
            Created feedback object
        """
        db = SessionLocal()
        try:
            feedback = DeviceAnalysisFeedback(**feedback_data)
            db.add(feedback)
            db.commit()
            db.refresh(feedback)
            logger.info(f"Created feedback {feedback.id} for device {feedback.device_ip}")
            return feedback
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating feedback: {e}")
            raise
        finally:
            db.close()

    def get_feedback_by_id(self, feedback_id: int) -> Optional[DeviceAnalysisFeedback]:
        """
        Get feedback by ID.

        Args:
            feedback_id: Feedback ID

        Returns:
            Feedback object or None
        """
        db = SessionLocal()
        try:
            return db.query(DeviceAnalysisFeedback).filter_by(id=feedback_id).first()
        finally:
            db.close()

    def get_all_feedback(self, limit: int = 100, offset: int = 0) -> List[DeviceAnalysisFeedback]:
        """
        Get all feedback with pagination.

        Args:
            limit: Maximum number of records
            offset: Number of records to skip

        Returns:
            List of feedback objects
        """
        db = SessionLocal()
        try:
            return db.query(DeviceAnalysisFeedback)\
                .order_by(DeviceAnalysisFeedback.created_at.desc())\
                .limit(limit)\
                .offset(offset)\
                .all()
        finally:
            db.close()

    def get_feedback_by_analysis(self, analysis_id: int) -> List[DeviceAnalysisFeedback]:
        """
        Get all feedback for a specific analysis.

        Args:
            analysis_id: Analysis ID

        Returns:
            List of feedback objects
        """
        db = SessionLocal()
        try:
            return db.query(DeviceAnalysisFeedback)\
                .filter_by(analysis_id=analysis_id)\
                .order_by(DeviceAnalysisFeedback.created_at.desc())\
                .all()
        finally:
            db.close()

    def get_feedback_by_device(self, device_ip: str, limit: int = 50) -> List[DeviceAnalysisFeedback]:
        """
        Get all feedback for a specific device.

        Args:
            device_ip: Device IP address
            limit: Maximum number of records

        Returns:
            List of feedback objects
        """
        db = SessionLocal()
        try:
            return db.query(DeviceAnalysisFeedback)\
                .filter_by(device_ip=device_ip)\
                .order_by(DeviceAnalysisFeedback.created_at.desc())\
                .limit(limit)\
                .all()
        finally:
            db.close()

    def get_feedback_by_type(self, feedback_type: str, limit: int = 100) -> List[DeviceAnalysisFeedback]:
        """
        Get feedback by type (positivo, negativo, parcial).

        Args:
            feedback_type: Type of feedback
            limit: Maximum number of records

        Returns:
            List of feedback objects
        """
        db = SessionLocal()
        try:
            return db.query(DeviceAnalysisFeedback)\
                .filter_by(feedback_type=feedback_type)\
                .order_by(DeviceAnalysisFeedback.created_at.desc())\
                .limit(limit)\
                .all()
        finally:
            db.close()

    def get_feedback_stats(self) -> dict:
        """
        Get feedback statistics.

        Returns:
            Dictionary with stats (total, by type, avg rating)
        """
        db = SessionLocal()
        try:
            from sqlalchemy import func

            total = db.query(func.count(DeviceAnalysisFeedback.id)).scalar()
            
            positivo = db.query(func.count(DeviceAnalysisFeedback.id))\
                .filter_by(feedback_type='positivo').scalar()
            
            negativo = db.query(func.count(DeviceAnalysisFeedback.id))\
                .filter_by(feedback_type='negativo').scalar()
            
            parcial = db.query(func.count(DeviceAnalysisFeedback.id))\
                .filter_by(feedback_type='parcial').scalar()
            
            avg_rating = db.query(func.avg(DeviceAnalysisFeedback.rating)).scalar()

            return {
                'total': total or 0,
                'positivo': positivo or 0,
                'negativo': negativo or 0,
                'parcial': parcial or 0,
                'avg_rating': round(float(avg_rating), 2) if avg_rating else 0.0
            }
        finally:
            db.close()

    def delete_feedback(self, feedback_id: int) -> bool:
        """
        Delete feedback by ID.

        Args:
            feedback_id: Feedback ID

        Returns:
            True if deleted, False if not found
        """
        db = SessionLocal()
        try:
            feedback = db.query(DeviceAnalysisFeedback).filter_by(id=feedback_id).first()
            if feedback:
                db.delete(feedback)
                db.commit()
                logger.info(f"Deleted feedback {feedback_id}")
                return True
            return False
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting feedback: {e}")
            raise
        finally:
            db.close()
