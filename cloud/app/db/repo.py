"""
Database repository for cloud service
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import desc, func, and_, or_
from sqlmodel import Session, select
import json

from .models import (
    Sensor, TelemetryReading, Alert, Event, SecurityEvent, SystemMetrics,
    SensorType, AlertSeverity, EventType,
    TelemetryIngestDTO, DashboardStats, AlertSummary, SensorSummary
)


class CloudRepository:
    """Repository for cloud service database operations"""
    
    def __init__(self, session: Session):
        self.session = session
    
    # Sensor operations
    
    def get_sensor(self, sensor_id: str) -> Optional[Sensor]:
        """Get sensor by ID"""
        statement = select(Sensor).where(Sensor.sensor_id == sensor_id)
        return self.session.exec(statement).first()
    
    def get_sensors(self, active_only: bool = False) -> List[Sensor]:
        """Get all sensors"""
        statement = select(Sensor)
        if active_only:
            statement = statement.where(Sensor.is_active == True)
        return self.session.exec(statement).all()
    
    def create_sensor(self, sensor_id: str, sensor_type: SensorType, name: str, location: str = None) -> Sensor:
        """Create new sensor"""
        sensor = Sensor(
            sensor_id=sensor_id,
            sensor_type=sensor_type,
            name=name,
            location=location
        )
        self.session.add(sensor)
        self.session.commit()
        self.session.refresh(sensor)
        return sensor
    
    def update_sensor_last_seen(self, sensor_id: str, timestamp: datetime) -> bool:
        """Update sensor last seen timestamp"""
        sensor = self.get_sensor(sensor_id)
        if sensor:
            sensor.last_seen = timestamp
            sensor.updated_at = datetime.utcnow()
            self.session.add(sensor)
            self.session.commit()
            return True
        return False
    
    def deactivate_sensor(self, sensor_id: str) -> bool:
        """Deactivate sensor"""
        sensor = self.get_sensor(sensor_id)
        if sensor:
            sensor.is_active = False
            sensor.updated_at = datetime.utcnow()
            self.session.add(sensor)
            self.session.commit()
            return True
        return False
    
    # Telemetry operations
    
    def create_telemetry_reading(self, data: TelemetryIngestDTO) -> TelemetryReading:
        """Create telemetry reading"""
        # Ensure sensor exists
        sensor = self.get_sensor(data.sensor_id)
        if not sensor:
            # Auto-create sensor
            sensor_type = SensorType(data.sensor_type)
            sensor = self.create_sensor(
                sensor_id=data.sensor_id,
                sensor_type=sensor_type,
                name=f"{data.sensor_type.title()} Sensor {data.sensor_id}"
            )
        
        # Update sensor last seen
        timestamp = datetime.fromisoformat(data.timestamp.replace('Z', '+00:00'))
        self.update_sensor_last_seen(data.sensor_id, timestamp)
        
        # Create reading
        reading = TelemetryReading(
            sensor_id=data.sensor_id,
            timestamp=timestamp,
            sensor_type=SensorType(data.sensor_type),
            value=data.value,
            unit=data.unit,
            fog_processed_at=datetime.fromisoformat(data.fog_processed_at.replace('Z', '+00:00')),
            security_validated=data.security_validated
        )
        
        self.session.add(reading)
        self.session.commit()
        self.session.refresh(reading)
        
        # Check for alerts
        self._check_telemetry_alerts(reading)
        
        return reading
    
    def get_telemetry_readings(
        self,
        sensor_id: Optional[str] = None,
        sensor_type: Optional[SensorType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
        offset: int = 0
    ) -> List[TelemetryReading]:
        """Get telemetry readings with filters"""
        statement = select(TelemetryReading)
        
        conditions = []
        if sensor_id:
            conditions.append(TelemetryReading.sensor_id == sensor_id)
        if sensor_type:
            conditions.append(TelemetryReading.sensor_type == sensor_type)
        if start_time:
            conditions.append(TelemetryReading.timestamp >= start_time)
        if end_time:
            conditions.append(TelemetryReading.timestamp <= end_time)
        
        if conditions:
            statement = statement.where(and_(*conditions))
        
        statement = statement.order_by(desc(TelemetryReading.timestamp))
        statement = statement.offset(offset).limit(limit)
        
        return self.session.exec(statement).all()
    
    def get_latest_reading(self, sensor_id: str) -> Optional[TelemetryReading]:
        """Get latest reading for sensor"""
        statement = select(TelemetryReading).where(
            TelemetryReading.sensor_id == sensor_id
        ).order_by(desc(TelemetryReading.timestamp)).limit(1)
        
        return self.session.exec(statement).first()
    
    def get_readings_count(
        self,
        sensor_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> int:
        """Get count of telemetry readings"""
        statement = select(func.count(TelemetryReading.id))
        
        conditions = []
        if sensor_id:
            conditions.append(TelemetryReading.sensor_id == sensor_id)
        if start_time:
            conditions.append(TelemetryReading.timestamp >= start_time)
        if end_time:
            conditions.append(TelemetryReading.timestamp <= end_time)
        
        if conditions:
            statement = statement.where(and_(*conditions))
        
        return self.session.exec(statement).one()
    
    # Alert operations
    
    def create_alert(
        self,
        sensor_id: str,
        alert_type: str,
        severity: AlertSeverity,
        title: str,
        message: str,
        value: Optional[float] = None,
        threshold: Optional[float] = None
    ) -> Alert:
        """Create alert"""
        alert = Alert(
            sensor_id=sensor_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            value=value,
            threshold=threshold
        )
        
        self.session.add(alert)
        self.session.commit()
        self.session.refresh(alert)
        
        # Create event for alert
        self.create_event(
            event_type=EventType.THRESHOLD_EXCEEDED,
            sensor_id=sensor_id,
            severity=severity.value,
            title=f"Alert: {title}",
            message=message,
            details=json.dumps({
                'alert_id': alert.id,
                'alert_type': alert_type,
                'value': value,
                'threshold': threshold
            })
        )
        
        return alert
    
    def get_alerts(
        self,
        sensor_id: Optional[str] = None,
        severity: Optional[AlertSeverity] = None,
        acknowledged: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Alert]:
        """Get alerts with filters"""
        statement = select(Alert)
        
        conditions = []
        if sensor_id:
            conditions.append(Alert.sensor_id == sensor_id)
        if severity:
            conditions.append(Alert.severity == severity)
        if acknowledged is not None:
            conditions.append(Alert.is_acknowledged == acknowledged)
        
        if conditions:
            statement = statement.where(and_(*conditions))
        
        statement = statement.order_by(desc(Alert.created_at))
        statement = statement.offset(offset).limit(limit)
        
        return self.session.exec(statement).all()
    
    def acknowledge_alert(self, alert_id: int, acknowledged_by: str) -> bool:
        """Acknowledge alert"""
        statement = select(Alert).where(Alert.id == alert_id)
        alert = self.session.exec(statement).first()
        
        if alert:
            alert.is_acknowledged = True
            alert.acknowledged_by = acknowledged_by
            alert.acknowledged_at = datetime.utcnow()
            self.session.add(alert)
            self.session.commit()
            return True
        
        return False
    
    def resolve_alert(self, alert_id: int) -> bool:
        """Resolve alert"""
        statement = select(Alert).where(Alert.id == alert_id)
        alert = self.session.exec(statement).first()
        
        if alert:
            alert.resolved_at = datetime.utcnow()
            self.session.add(alert)
            self.session.commit()
            return True
        
        return False
    
    # Event operations
    
    def create_event(
        self,
        event_type: EventType,
        title: str,
        message: str,
        sensor_id: Optional[str] = None,
        severity: str = "info",
        details: Optional[str] = None,
        source: str = "cloud"
    ) -> Event:
        """Create event"""
        event = Event(
            event_type=event_type,
            sensor_id=sensor_id,
            severity=severity,
            title=title,
            message=message,
            details=details,
            source=source
        )
        
        self.session.add(event)
        self.session.commit()
        self.session.refresh(event)
        return event
    
    def get_events(
        self,
        event_type: Optional[EventType] = None,
        sensor_id: Optional[str] = None,
        severity: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Event]:
        """Get events with filters"""
        statement = select(Event)
        
        conditions = []
        if event_type:
            conditions.append(Event.event_type == event_type)
        if sensor_id:
            conditions.append(Event.sensor_id == sensor_id)
        if severity:
            conditions.append(Event.severity == severity)
        if start_time:
            conditions.append(Event.created_at >= start_time)
        if end_time:
            conditions.append(Event.created_at <= end_time)
        
        if conditions:
            statement = statement.where(and_(*conditions))
        
        statement = statement.order_by(desc(Event.created_at))
        statement = statement.offset(offset).limit(limit)
        
        return self.session.exec(statement).all()
    
    # Security event operations
    
    def create_security_event(
        self,
        event_type: str,
        message: str,
        sensor_id: Optional[str] = None,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        threat_level: str = "low",
        blocked: bool = False,
        details: Optional[str] = None
    ) -> SecurityEvent:
        """Create security event"""
        event = SecurityEvent(
            event_type=event_type,
            sensor_id=sensor_id,
            source_ip=source_ip,
            user_agent=user_agent,
            threat_level=threat_level,
            blocked=blocked,
            message=message,
            details=details
        )
        
        self.session.add(event)
        self.session.commit()
        self.session.refresh(event)
        return event
    
    # Statistics and dashboard
    
    def get_dashboard_stats(self) -> DashboardStats:
        """Get dashboard statistics"""
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Sensor stats
        total_sensors = self.session.exec(
            select(func.count(Sensor.id))
        ).one()
        
        active_sensors = self.session.exec(
            select(func.count(Sensor.id)).where(Sensor.is_active == True)
        ).one()
        
        # Reading stats
        total_readings = self.session.exec(
            select(func.count(TelemetryReading.id))
        ).one()
        
        # Alert stats
        total_alerts = self.session.exec(
            select(func.count(Alert.id))
        ).one()
        
        unacknowledged_alerts = self.session.exec(
            select(func.count(Alert.id)).where(Alert.is_acknowledged == False)
        ).one()
        
        # Security events today
        security_events_today = self.session.exec(
            select(func.count(SecurityEvent.id)).where(
                SecurityEvent.created_at >= today_start
            )
        ).one()
        
        # Average readings per hour (last 24 hours)
        yesterday = now - timedelta(hours=24)
        readings_24h = self.session.exec(
            select(func.count(TelemetryReading.id)).where(
                TelemetryReading.timestamp >= yesterday
            )
        ).one()
        avg_readings_per_hour = readings_24h / 24.0
        
        # System uptime (mock - would normally be from system metrics)
        system_uptime_hours = 24.0  # Placeholder
        
        return DashboardStats(
            total_sensors=total_sensors,
            active_sensors=active_sensors,
            total_readings=total_readings,
            total_alerts=total_alerts,
            unacknowledged_alerts=unacknowledged_alerts,
            security_events_today=security_events_today,
            avg_readings_per_hour=avg_readings_per_hour,
            system_uptime_hours=system_uptime_hours
        )
    
    def get_sensor_summaries(self) -> List[SensorSummary]:
        """Get sensor summaries for dashboard"""
        sensors = self.get_sensors()
        summaries = []
        
        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)
        
        for sensor in sensors:
            # Get latest reading
            latest_reading = self.get_latest_reading(sensor.sensor_id)
            
            # Get reading count in last 24h
            reading_count_24h = self.get_readings_count(
                sensor_id=sensor.sensor_id,
                start_time=last_24h
            )
            
            # Get alert count in last 24h
            alert_count_24h = self.session.exec(
                select(func.count(Alert.id)).where(
                    and_(
                        Alert.sensor_id == sensor.sensor_id,
                        Alert.created_at >= last_24h
                    )
                )
            ).one()
            
            summaries.append(SensorSummary(
                sensor_id=sensor.sensor_id,
                sensor_type=sensor.sensor_type.value,
                name=sensor.name,
                is_active=sensor.is_active,
                last_reading_time=latest_reading.timestamp if latest_reading else None,
                last_reading_value=latest_reading.value if latest_reading else None,
                reading_count_24h=reading_count_24h,
                alert_count_24h=alert_count_24h
            ))
        
        return summaries
    
    def _check_telemetry_alerts(self, reading: TelemetryReading):
        """Check telemetry reading for alert conditions"""
        # Define thresholds (in real system, these would be configurable)
        thresholds = {
            SensorType.TEMPERATURE: {'min': 15.0, 'max': 35.0},
            SensorType.HUMIDITY: {'min': 20.0, 'max': 80.0},
            SensorType.WIND: {'min': 0.0, 'max': 20.0}
        }
        
        sensor_thresholds = thresholds.get(reading.sensor_type)
        if not sensor_thresholds:
            return
        
        # Check for threshold violations
        if reading.value < sensor_thresholds['min']:
            self.create_alert(
                sensor_id=reading.sensor_id,
                alert_type="threshold_low",
                severity=AlertSeverity.MEDIUM,
                title=f"{reading.sensor_type.value.title()} Below Threshold",
                message=f"{reading.sensor_type.value.title()} reading of {reading.value} {reading.unit} is below minimum threshold of {sensor_thresholds['min']} {reading.unit}",
                value=reading.value,
                threshold=sensor_thresholds['min']
            )
        elif reading.value > sensor_thresholds['max']:
            severity = AlertSeverity.HIGH if reading.value > sensor_thresholds['max'] * 1.2 else AlertSeverity.MEDIUM
            self.create_alert(
                sensor_id=reading.sensor_id,
                alert_type="threshold_high",
                severity=severity,
                title=f"{reading.sensor_type.value.title()} Above Threshold",
                message=f"{reading.sensor_type.value.title()} reading of {reading.value} {reading.unit} is above maximum threshold of {sensor_thresholds['max']} {reading.unit}",
                value=reading.value,
                threshold=sensor_thresholds['max']
            )