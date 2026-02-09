"""
Post-Mortem and Notification Models for Alert System
"""

from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Text, ForeignKey, Boolean, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app_fast_api.utils.database import Base
from app_fast_api.utils.timezone import now_argentina


class NotificationStatus(str, enum.Enum):
    """Status of notification delivery"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    RETRY = "retry"


class NotificationChannel(str, enum.Enum):
    """Notification delivery channels"""
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    WEBHOOK = "webhook"
    SMS = "sms"


class PostMortemStatus(str, enum.Enum):
    """Post-mortem completion status"""
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REVIEWED = "reviewed"


class AlertNotification(Base):
    """
    Registro de notificaciones enviadas por alertas.
    Permite tracking completo de todas las notificaciones.
    """
    __tablename__ = 'alert_notifications'

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Relación con el evento
    alert_event_id = Column(BigInteger, ForeignKey('alert_events.id', ondelete='CASCADE'), nullable=False, index=True)
    alert_event = relationship("AlertEvent", back_populates="notifications")

    # Información de la notificación
    channel = Column(SQLEnum(NotificationChannel), nullable=False, index=True)
    recipient = Column(String(255), nullable=False)  # Número de teléfono, email, etc.
    status = Column(SQLEnum(NotificationStatus), default=NotificationStatus.PENDING, nullable=False, index=True)

    # Contenido
    message_type = Column(String(50), nullable=False)  # "full", "summary", "recovery"
    message_content = Column(Text)  # Contenido del mensaje enviado

    # Metadata de envío
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    retry_count = Column(Integer, default=0)

    # Error tracking
    error_message = Column(Text, nullable=True)
    provider_message_id = Column(String(255), nullable=True)  # ID del proveedor (WhatsApp, etc.)

    # Metadata adicional (renamed from 'metadata' to avoid SQLAlchemy reserved word)
    notification_metadata = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=now_argentina, nullable=False, index=True)
    updated_at = Column(DateTime, default=now_argentina, onupdate=now_argentina)

    def __repr__(self):
        return f"<AlertNotification(id={self.id}, channel={self.channel}, status={self.status}, recipient={self.recipient})>"


class PostMortem(Base):
    """
    Análisis Post-Mortem de incidentes.
    Documenta la causa raíz, impacto, acciones correctivas y lecciones aprendidas.
    """
    __tablename__ = 'post_mortems'

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Relación con el evento
    alert_event_id = Column(BigInteger, ForeignKey('alert_events.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)
    alert_event = relationship("AlertEvent", back_populates="post_mortem")

    # Información del incidente
    title = Column(String(255), nullable=False)
    status = Column(SQLEnum(PostMortemStatus), default=PostMortemStatus.DRAFT, nullable=False, index=True)

    # Timeline del incidente
    incident_start = Column(DateTime, nullable=False)
    incident_end = Column(DateTime, nullable=True)
    detection_time = Column(DateTime, nullable=False)  # Cuándo se detectó
    response_time = Column(DateTime, nullable=True)  # Cuándo se comenzó a responder
    resolution_time = Column(DateTime, nullable=True)  # Cuándo se resolvió

    # Análisis
    summary = Column(Text, nullable=False)  # Resumen ejecutivo
    impact_description = Column(Text)  # Descripción del impacto
    root_cause = Column(Text)  # Causa raíz identificada
    trigger = Column(Text)  # Qué desencadenó el incidente

    # Métricas de impacto
    affected_users = Column(Integer, default=0)
    affected_devices = Column(Integer, default=0)
    downtime_minutes = Column(Integer, default=0)
    estimated_cost = Column(String(100), nullable=True)

    # Severidad y prioridad
    severity = Column(String(50), nullable=True)  # "critical", "high", "medium", "low"
    customer_impact = Column(String(50), nullable=True)  # "total", "partial", "minimal"

    # Timeline detallado (JSON con eventos)
    timeline_events = Column(JSON, default=list)
    # Ejemplo: [
    #   {"time": "2024-01-01T10:00:00", "event": "Site down detected", "actor": "System"},
    #   {"time": "2024-01-01T10:05:00", "event": "NOC notified", "actor": "Alert System"},
    #   {"time": "2024-01-01T10:15:00", "event": "Technician dispatched", "actor": "Juan Perez"}
    # ]

    # Respuesta y resolución
    response_actions = Column(JSON, default=list)  # Acciones tomadas durante el incidente
    resolution_description = Column(Text)  # Cómo se resolvió

    # Prevención futura
    preventive_actions = Column(JSON, default=list)  # Acciones para prevenir recurrencia
    lessons_learned = Column(Text)  # Lecciones aprendidas
    action_items = Column(JSON, default=list)  # TODOs resultantes
    # Ejemplo: [
    #   {"action": "Instalar UPS de respaldo", "owner": "Juan", "due_date": "2024-02-01", "status": "pending"}
    # ]

    # Colaboración
    author = Column(String(255), nullable=True)  # Quién escribe el post-mortem
    reviewers = Column(JSON, default=list)  # Quiénes revisan
    contributors = Column(JSON, default=list)  # Otros contribuyentes

    # Metadata
    tags = Column(JSON, default=list)  # Tags para categorización
    related_incidents = Column(JSON, default=list)  # IDs de incidentes relacionados
    external_links = Column(JSON, default=list)  # Links a docs, tickets, etc.

    # Timestamps
    created_at = Column(DateTime, default=now_argentina, nullable=False, index=True)
    updated_at = Column(DateTime, default=now_argentina, onupdate=now_argentina)
    completed_at = Column(DateTime, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<PostMortem(id={self.id}, title={self.title}, status={self.status})>"

    def calculate_mttr(self) -> int:
        """Calculate Mean Time To Recovery in minutes"""
        if self.incident_start and self.resolution_time:
            delta = self.resolution_time - self.incident_start
            return int(delta.total_seconds() / 60)
        return 0

    def calculate_detection_delay(self) -> int:
        """Calculate delay between incident start and detection in minutes"""
        if self.incident_start and self.detection_time:
            delta = self.detection_time - self.incident_start
            return int(delta.total_seconds() / 60)
        return 0
