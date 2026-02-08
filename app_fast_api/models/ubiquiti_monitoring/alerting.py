"""Models for alerting and site monitoring."""

from sqlalchemy import Column, BigInteger, String, Integer, Float, Boolean, Text, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app_fast_api.utils.database import Base
import enum


class AlertSeverity(enum.Enum):
    """Alert severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertStatus(enum.Enum):
    """Alert status."""
    ACTIVE = "active"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"
    IGNORED = "ignored"


class EventType(enum.Enum):
    """Event types for alerting system."""
    SITE_OUTAGE = "site_outage"
    SITE_DEGRADED = "site_degraded"
    SITE_RECOVERED = "site_recovered"
    DEVICE_OUTAGE = "device_outage"
    DEVICE_RECOVERED = "device_recovered"
    CUSTOM = "custom"


class SiteMonitoring(Base):
    """Model for site monitoring data from UNMS."""
    __tablename__ = 'site_monitoring'

    id = Column(BigInteger, primary_key=True)
    site_id = Column(String(100), nullable=False, unique=True, index=True)
    site_name = Column(String(200), nullable=False)
    site_status = Column(String(50))
    site_type = Column(String(50))

    # Location
    address = Column(String(500))
    latitude = Column(Float)
    longitude = Column(Float)
    height = Column(Float)

    # Contact info
    contact_name = Column(String(200))
    contact_phone = Column(String(50))
    contact_email = Column(String(200))

    # Device counts
    device_count = Column(Integer, default=0)
    device_outage_count = Column(Integer, default=0)
    device_list_status = Column(String(50))

    # Calculated metrics
    outage_percentage = Column(Float, default=0.0)
    is_site_down = Column(Boolean, default=False)

    # Additional info
    note = Column(Text)
    ip_addresses = Column(Text)  # JSON array as text
    regulatory_domain = Column(String(10))
    suspended = Column(Boolean, default=False)

    # Timestamps
    last_checked = Column(DateTime, nullable=False)
    last_updated = Column(DateTime)
    created_at = Column(DateTime, nullable=False)

    # Relationships
    alerts = relationship("AlertEvent", back_populates="site", cascade="all, delete-orphan")

    def __repr__(self):
        return f'<SiteMonitoring {self.site_name} ({self.device_outage_count}/{self.device_count})>'


class AlertEvent(Base):
    """Model for alert events."""
    __tablename__ = 'alert_events'

    id = Column(BigInteger, primary_key=True)

    # Event identification
    event_type = Column(Enum(EventType), nullable=False, index=True)
    severity = Column(Enum(AlertSeverity), nullable=False, default=AlertSeverity.MEDIUM)
    status = Column(Enum(AlertStatus), nullable=False, default=AlertStatus.ACTIVE, index=True)

    # Event details
    title = Column(String(500), nullable=False)
    description = Column(Text)

    # Related site (optional, for site-related alerts)
    site_id = Column(BigInteger, ForeignKey('site_monitoring.id'), nullable=True, index=True)
    site = relationship("SiteMonitoring", back_populates="alerts")

    # Relationships with notifications and post-mortem
    notifications = relationship("AlertNotification", back_populates="alert_event", cascade="all, delete-orphan")
    post_mortem = relationship("PostMortem", back_populates="alert_event", uselist=False, cascade="all, delete-orphan")

    # Additional data
    device_count = Column(Integer)
    outage_count = Column(Integer)
    outage_percentage = Column(Float)
    affected_devices = Column(Text)  # JSON array as text

    # Custom metadata
    custom_data = Column(Text)  # JSON object as text

    # Notification
    notification_sent = Column(Boolean, default=False)
    notification_sent_at = Column(DateTime)
    notification_recipients = Column(Text)  # JSON array as text

    # Acknowledgment
    acknowledged_by = Column(String(200))
    acknowledged_at = Column(DateTime)
    acknowledged_note = Column(Text)

    # Resolution
    resolved_at = Column(DateTime)
    resolved_by = Column(String(200))
    resolved_note = Column(Text)
    auto_resolved = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime)

    def __repr__(self):
        return f'<AlertEvent {self.event_type.value} - {self.severity.value} - {self.status.value}>'
