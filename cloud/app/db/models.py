"""
Database models for cloud service using SQLModel
"""

from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from enum import Enum


class SensorType(str, Enum):
    """Sensor types"""
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    WIND = "wind"


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EventType(str, Enum):
    """Event types"""
    TELEMETRY_RECEIVED = "telemetry_received"
    SECURITY_VIOLATION = "security_violation"
    SENSOR_OFFLINE = "sensor_offline"
    SENSOR_ONLINE = "sensor_online"
    THRESHOLD_EXCEEDED = "threshold_exceeded"
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"


# Database Models

class Sensor(SQLModel, table=True):
    """Sensor configuration and metadata"""
    __tablename__ = "sensors"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    sensor_id: str = Field(unique=True, index=True)
    sensor_type: SensorType
    name: str
    location: Optional[str] = None
    is_active: bool = Field(default=True)
    last_seen: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    readings: List["TelemetryReading"] = Relationship(back_populates="sensor")
    alerts: List["Alert"] = Relationship(back_populates="sensor")


class TelemetryReading(SQLModel, table=True):
    """Telemetry readings from sensors"""
    __tablename__ = "telemetry_readings"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    sensor_id: str = Field(foreign_key="sensors.sensor_id", index=True)
    timestamp: datetime = Field(index=True)
    sensor_type: SensorType
    value: float
    unit: str
    fog_processed_at: datetime
    security_validated: bool = Field(default=False)
    received_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    sensor: Optional[Sensor] = Relationship(back_populates="readings")


class Alert(SQLModel, table=True):
    """Alerts generated from telemetry analysis"""
    __tablename__ = "alerts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    sensor_id: str = Field(foreign_key="sensors.sensor_id", index=True)
    alert_type: str
    severity: AlertSeverity
    title: str
    message: str
    value: Optional[float] = None
    threshold: Optional[float] = None
    is_acknowledged: bool = Field(default=False)
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    
    # Relationships
    sensor: Optional[Sensor] = Relationship(back_populates="alerts")


class Event(SQLModel, table=True):
    """System events and audit log"""
    __tablename__ = "events"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    event_type: EventType
    sensor_id: Optional[str] = None
    severity: str = Field(default="info")
    title: str
    message: str
    details: Optional[str] = None  # JSON string for additional details
    source: str = Field(default="cloud")  # fog, cloud, sensor, etc.
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class SecurityEvent(SQLModel, table=True):
    """Security-related events"""
    __tablename__ = "security_events"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    event_type: str
    sensor_id: Optional[str] = None
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    threat_level: str = Field(default="low")
    blocked: bool = Field(default=False)
    message: str
    details: Optional[str] = None  # JSON string
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class SystemMetrics(SQLModel, table=True):
    """System performance metrics"""
    __tablename__ = "system_metrics"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    metric_name: str
    metric_value: float
    unit: str
    source: str = Field(default="cloud")
    details: Optional[str] = None


# DTOs and Response Models

class TelemetryIngestDTO(SQLModel):
    """DTO for ingesting telemetry data"""
    sensor_id: str
    timestamp: str  # ISO format
    sensor_type: str
    value: float
    unit: str
    fog_processed_at: str  # ISO format
    security_validated: bool


class TelemetryReadingResponse(SQLModel):
    """Response model for telemetry readings"""
    id: int
    sensor_id: str
    timestamp: datetime
    sensor_type: str
    value: float
    unit: str
    fog_processed_at: datetime
    security_validated: bool
    received_at: datetime


class AlertResponse(SQLModel):
    """Response model for alerts"""
    id: int
    sensor_id: str
    alert_type: str
    severity: str
    title: str
    message: str
    value: Optional[float]
    threshold: Optional[float]
    is_acknowledged: bool
    acknowledged_by: Optional[str]
    acknowledged_at: Optional[datetime]
    created_at: datetime
    resolved_at: Optional[datetime]


class EventResponse(SQLModel):
    """Response model for events"""
    id: int
    event_type: str
    sensor_id: Optional[str]
    severity: str
    title: str
    message: str
    source: str
    created_at: datetime


class SensorResponse(SQLModel):
    """Response model for sensors"""
    id: int
    sensor_id: str
    sensor_type: str
    name: str
    location: Optional[str]
    is_active: bool
    last_seen: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class DashboardStats(SQLModel):
    """Dashboard statistics"""
    total_sensors: int
    active_sensors: int
    total_readings: int
    total_alerts: int
    unacknowledged_alerts: int
    security_events_today: int
    avg_readings_per_hour: float
    system_uptime_hours: float


class AlertSummary(SQLModel):
    """Alert summary for dashboard"""
    total_alerts: int
    critical_alerts: int
    high_alerts: int
    medium_alerts: int
    low_alerts: int
    recent_alerts: List[AlertResponse]


class SensorSummary(SQLModel):
    """Sensor summary for dashboard"""
    sensor_id: str
    sensor_type: str
    name: str
    is_active: bool
    last_reading_time: Optional[datetime]
    last_reading_value: Optional[float]
    reading_count_24h: int
    alert_count_24h: int