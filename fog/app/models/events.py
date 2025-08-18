"""
Event models for fog service
"""

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from enum import Enum


class EventType(str, Enum):
    """Types of events"""
    SECURITY_VIOLATION = "security_violation"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    INVALID_SIGNATURE = "invalid_signature"
    INVALID_TIMESTAMP = "invalid_timestamp"
    REPLAY_ATTACK = "replay_attack"
    TELEMETRY_PROCESSED = "telemetry_processed"
    CLOUD_SEND_SUCCESS = "cloud_send_success"
    CLOUD_SEND_FAILURE = "cloud_send_failure"
    COAP_REQUEST = "coap_request"
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"


class EventSeverity(str, Enum):
    """Event severity levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SecurityEvent(BaseModel):
    """Security-related event"""
    event_id: str
    event_type: EventType
    severity: EventSeverity
    timestamp: datetime
    sensor_id: Optional[str] = None
    message: str
    details: Dict[str, Any] = {}
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TelemetryEvent(BaseModel):
    """Telemetry processing event"""
    event_id: str
    timestamp: datetime
    sensor_id: str
    event_type: EventType
    processing_time_ms: float
    success: bool
    details: Dict[str, Any] = {}
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CloudEvent(BaseModel):
    """Cloud communication event"""
    event_id: str
    timestamp: datetime
    event_type: EventType
    endpoint: str
    status_code: Optional[int] = None
    response_time_ms: float
    success: bool
    error_message: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }