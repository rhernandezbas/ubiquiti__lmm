"""Models for feedback data."""

from sqlalchemy import Column, BigInteger, String, Integer, Text, DateTime, Boolean
from sqlalchemy.orm import relationship
from app_fast_api.utils.database import Base


class Feedback(Base):
    """Model for feedback data."""
    __tablename__ = 'feedback'

    id = Column(BigInteger, primary_key=True)
    analysis_id = Column(BigInteger, nullable=True)  # FK a device_analysis
    device_ip = Column(String(45), nullable=False, index=True)
    feedback_type = Column(String(20), nullable=False)  # positivo|negativo|parcial
    rating = Column(Integer, nullable=False)  # 1-5
    comments = Column(Text, nullable=True)
    user_name = Column(String(200), nullable=True)
    timestamp = Column(DateTime, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f'<Feedback {self.feedback_type} - {self.device_ip}>'
