from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

class DeviceStatus(str, Enum):
    ACTIVE = "active"
    ONLINE = "online"
    OFFLINE = "offline"
    UNKNOWN = "unknown"
    DEGRADED = "degraded"
    INACTIVE = "inactive"
    DISABLED = "disabled"

class DiagnosticStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Device:
    id: str
    name: str
    ip_address: str
    mac_address: str
    model: str
    status: DeviceStatus
    last_seen: datetime
    firmware_version: Optional[str] = None
    uptime: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DiagnosticPattern:
    name: str
    description: str
    conditions: Dict[str, Any]
    severity: str
    recommendation: str

@dataclass
class DiagnosticResult:
    device_id: str
    timestamp: datetime
    status: DiagnosticStatus
    issues: List[str]
    recommendations: List[str]
    confidence: float
    patterns_matched: List[str] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
