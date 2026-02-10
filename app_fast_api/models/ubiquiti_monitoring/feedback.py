"""
Feedback Model for Device Analysis
"""

from sqlalchemy import Column, BigInteger, Integer, String, DateTime, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app_fast_api.utils.database import Base
from app_fast_api.utils.timezone import now_argentina


class DeviceAnalysisFeedback(Base):
    """
    Feedback from NOC operators about device analysis quality.
    Used to improve LLM prompts and measure analysis accuracy.
    """
    __tablename__ = 'device_analysis_feedback'

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Relationship to analysis (optional - feedback can exist without analysis_id)
    analysis_id = Column(BigInteger, ForeignKey('device_analysis.id', ondelete='SET NULL'), nullable=True, index=True)
    analysis = relationship("DeviceAnalysis", backref="feedbacks")

    # Device info
    device_ip = Column(String(50), nullable=False, index=True)
    device_mac = Column(String(50), nullable=True)

    # Feedback data
    feedback_type = Column(String(20), nullable=False, index=True)  # positivo, negativo, parcial
    rating = Column(Integer, nullable=False)  # 1-5 stars
    comments = Column(Text, nullable=True)

    # User info
    user_name = Column(String(100), nullable=True)
    user_email = Column(String(100), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=now_argentina, nullable=False, index=True)
    updated_at = Column(DateTime, default=now_argentina, onupdate=now_argentina)

    def __repr__(self):
        return f"<DeviceAnalysisFeedback(id={self.id}, type={self.feedback_type}, rating={self.rating}, device={self.device_ip})>"

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'analysis_id': self.analysis_id,
            'device_ip': self.device_ip,
            'device_mac': self.device_mac,
            'feedback_type': self.feedback_type,
            'rating': self.rating,
            'comments': self.comments,
            'user_name': self.user_name,
            'user_email': self.user_email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
