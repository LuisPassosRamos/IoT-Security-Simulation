"""
Seed Data Script for IoT Security Simulation
Populates the cloud database with sample data for demonstration
"""

import asyncio
import json
import random
import sys
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

# Add the cloud app to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'cloud'))

from sqlmodel import Session, create_engine
from cloud.app.db.models import (
    Sensor, TelemetryReading, Alert, Event, SecurityEvent,
    SensorType, AlertSeverity, EventType
)
from cloud.app.db import init_database


class DataSeeder:
    """Seeds the database with sample IoT data"""
    
    def __init__(self, database_url: str = "sqlite:///./demo.db"):
        self.engine = create_engine(database_url)
        self.sensors = [
            {"id": "temp-01", "type": SensorType.TEMPERATURE, "name": "Greenhouse Temperature Sensor", "location": "Main Greenhouse"},
            {"id": "humidity-01", "type": SensorType.HUMIDITY, "name": "Greenhouse Humidity Sensor", "location": "Main Greenhouse"},
            {"id": "wind-01", "type": SensorType.WIND, "name": "Greenhouse Wind Sensor", "location": "Greenhouse Roof"}
        ]
    
    def seed_all(self):
        """Seed all data types"""
        print("IoT Security Simulation - Database Seeder")
        print("==========================================")
        
        # Initialize database
        print("Initializing database...")
        init_database(self.engine)
        
        with Session(self.engine) as session:
            print("Seeding data...")
            
            # Create sensors
            self.seed_sensors(session)
            
            # Create historical telemetry data
            self.seed_telemetry_readings(session)
            
            # Create sample alerts
            self.seed_alerts(session)
            
            # Create system events
            self.seed_events(session)
            
            # Create security events
            self.seed_security_events(session)
            
            session.commit()
        
        print("Database seeding completed successfully!")
    
    def seed_sensors(self, session: Session):
        """Create sensor records"""
        print("  Creating sensors...")
        
        for sensor_data in self.sensors:
            sensor = Sensor(
                sensor_id=sensor_data["id"],
                sensor_type=sensor_data["type"],
                name=sensor_data["name"],
                location=sensor_data["location"],
                is_active=True,
                last_seen=datetime.now(timezone.utc) - timedelta(minutes=random.randint(1, 60)),
                created_at=datetime.now(timezone.utc) - timedelta(days=30)
            )
            session.add(sensor)
        
        print(f"    Created {len(self.sensors)} sensors")
    
    def seed_telemetry_readings(self, session: Session):
        """Create historical telemetry readings"""
        print("  Creating telemetry readings...")
        
        readings_count = 0
        
        # Generate data for the last 7 days
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=7)
        
        # Generate readings every 10 minutes
        current_time = start_time
        interval = timedelta(minutes=10)
        
        while current_time <= end_time:
            for sensor_data in self.sensors:
                # Generate realistic sensor values
                value = self._generate_sensor_value(sensor_data["type"], current_time)
                unit = self._get_sensor_unit(sensor_data["type"])
                
                # Occasionally simulate missing readings (sensor offline)
                if random.random() < 0.02:  # 2% chance of missing reading
                    current_time += interval
                    continue
                
                reading = TelemetryReading(
                    sensor_id=sensor_data["id"],
                    timestamp=current_time,
                    sensor_type=sensor_data["type"],
                    value=value,
                    unit=unit,
                    fog_processed_at=current_time + timedelta(seconds=random.randint(1, 10)),
                    security_validated=random.random() > 0.05,  # 95% security validated
                    received_at=current_time + timedelta(seconds=random.randint(1, 30))
                )
                session.add(reading)
                readings_count += 1
            
            current_time += interval
        
        print(f"    Created {readings_count} telemetry readings")
    
    def seed_alerts(self, session: Session):
        """Create sample alerts"""
        print("  Creating alerts...")
        
        alerts_data = [
            {
                "sensor_id": "temp-01",
                "alert_type": "threshold_high",
                "severity": AlertSeverity.HIGH,
                "title": "Temperature Above Threshold",
                "message": "Temperature reading of 35.2°C exceeds maximum threshold of 30.0°C",
                "value": 35.2,
                "threshold": 30.0,
                "created_at": datetime.now(timezone.utc) - timedelta(hours=2)
            },
            {
                "sensor_id": "humidity-01",
                "alert_type": "threshold_low",
                "severity": AlertSeverity.MEDIUM,
                "title": "Humidity Below Threshold",
                "message": "Humidity reading of 15.5% is below minimum threshold of 20.0%",
                "value": 15.5,
                "threshold": 20.0,
                "created_at": datetime.now(timezone.utc) - timedelta(hours=6),
                "is_acknowledged": True,
                "acknowledged_by": "admin",
                "acknowledged_at": datetime.now(timezone.utc) - timedelta(hours=5)
            },
            {
                "sensor_id": "wind-01",
                "alert_type": "threshold_high",
                "severity": AlertSeverity.CRITICAL,
                "title": "High Wind Speed Detected",
                "message": "Wind speed of 25.8 m/s exceeds critical threshold of 20.0 m/s",
                "value": 25.8,
                "threshold": 20.0,
                "created_at": datetime.now(timezone.utc) - timedelta(hours=12)
            },
            {
                "sensor_id": "temp-01",
                "alert_type": "sensor_offline",
                "severity": AlertSeverity.HIGH,
                "title": "Sensor Communication Lost",
                "message": "No data received from temperature sensor for 30 minutes",
                "created_at": datetime.now(timezone.utc) - timedelta(days=1),
                "resolved_at": datetime.now(timezone.utc) - timedelta(days=1) + timedelta(hours=1)
            }
        ]
        
        for alert_data in alerts_data:
            alert = Alert(**alert_data)
            session.add(alert)
        
        print(f"    Created {len(alerts_data)} alerts")
    
    def seed_events(self, session: Session):
        """Create system events"""
        print("  Creating system events...")
        
        events_data = [
            {
                "event_type": EventType.SYSTEM_STARTUP,
                "severity": "info",
                "title": "Cloud Service Started",
                "message": "Cloud service started successfully",
                "source": "cloud",
                "created_at": datetime.now(timezone.utc) - timedelta(days=7)
            },
            {
                "event_type": EventType.SENSOR_ONLINE,
                "sensor_id": "temp-01",
                "severity": "info",
                "title": "Sensor Connected",
                "message": "Temperature sensor came online",
                "source": "fog",
                "created_at": datetime.now(timezone.utc) - timedelta(days=6)
            },
            {
                "event_type": EventType.TELEMETRY_RECEIVED,
                "sensor_id": "humidity-01",
                "severity": "info",
                "title": "Telemetry Data Received",
                "message": "Received telemetry data from humidity sensor",
                "source": "fog",
                "created_at": datetime.now(timezone.utc) - timedelta(hours=1)
            },
            {
                "event_type": EventType.SECURITY_VIOLATION,
                "sensor_id": "wind-01",
                "severity": "warning",
                "title": "Invalid Message Signature",
                "message": "Received message with invalid HMAC signature",
                "source": "fog",
                "details": json.dumps({"signature_validation": "failed", "message_id": "12345"}),
                "created_at": datetime.now(timezone.utc) - timedelta(hours=3)
            },
            {
                "event_type": EventType.THRESHOLD_EXCEEDED,
                "sensor_id": "temp-01",
                "severity": "error",
                "title": "Temperature Threshold Exceeded",
                "message": "Temperature exceeded critical threshold",
                "source": "cloud",
                "created_at": datetime.now(timezone.utc) - timedelta(hours=2)
            }
        ]
        
        # Add more random events
        for i in range(50):
            event_type = random.choice(list(EventType))
            sensor_id = random.choice([s["id"] for s in self.sensors]) if random.random() > 0.3 else None
            severity = random.choice(["info", "warning", "error"])
            
            event = Event(
                event_type=event_type,
                sensor_id=sensor_id,
                severity=severity,
                title=f"Event {i+1}",
                message=f"System event {i+1} - {event_type.value}",
                source=random.choice(["cloud", "fog", "sensor"]),
                created_at=datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 168))  # Last week
            )
            events_data.append(event.__dict__)
        
        for event_data in events_data:
            if isinstance(event_data, dict):
                event = Event(**{k: v for k, v in event_data.items() if k != 'id'})
            else:
                event = event_data
            session.add(event)
        
        print(f"    Created {len(events_data)} events")
    
    def seed_security_events(self, session: Session):
        """Create security events"""
        print("  Creating security events...")
        
        security_events = []
        
        # Generate security events for the last 24 hours
        for i in range(20):
            event_types = ["invalid_signature", "replay_attack", "rate_limit_exceeded", "suspicious_activity"]
            threat_levels = ["low", "medium", "high", "critical"]
            
            event = SecurityEvent(
                event_type=random.choice(event_types),
                sensor_id=random.choice([s["id"] for s in self.sensors]) if random.random() > 0.2 else None,
                source_ip=f"192.168.1.{random.randint(10, 250)}",
                user_agent="IoT-Device/1.0",
                threat_level=random.choice(threat_levels),
                blocked=random.random() > 0.3,  # 70% blocked
                message=f"Security event {i+1} detected",
                details=json.dumps({
                    "event_id": f"sec_{i+1}",
                    "detection_method": "signature_analysis",
                    "confidence": random.uniform(0.7, 1.0)
                }),
                created_at=datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 24))
            )
            security_events.append(event)
        
        for event in security_events:
            session.add(event)
        
        print(f"    Created {len(security_events)} security events")
    
    def _generate_sensor_value(self, sensor_type: SensorType, timestamp: datetime) -> float:
        """Generate realistic sensor values with daily patterns"""
        
        # Time-based variation (daily cycle)
        hour = timestamp.hour
        daily_factor = 0.5 * (1 + random.random() * 0.4)  # Random daily variation
        
        if sensor_type == SensorType.TEMPERATURE:
            # Temperature varies with time of day
            base_temp = 22.0
            daily_variation = 5.0 * daily_factor * (0.5 - abs(hour - 12) / 24)
            noise = random.uniform(-1.0, 1.0)
            return round(base_temp + daily_variation + noise, 2)
        
        elif sensor_type == SensorType.HUMIDITY:
            # Humidity inversely related to temperature pattern
            base_humidity = 50.0
            daily_variation = -10.0 * daily_factor * (0.5 - abs(hour - 12) / 24)
            noise = random.uniform(-5.0, 5.0)
            return round(max(20.0, min(80.0, base_humidity + daily_variation + noise)), 2)
        
        elif sensor_type == SensorType.WIND:
            # Wind speed with some randomness
            base_wind = 3.0
            daily_variation = 2.0 * daily_factor if 6 <= hour <= 18 else 1.0  # More wind during day
            noise = random.uniform(-1.5, 1.5)
            return round(max(0.0, base_wind + daily_variation + noise), 2)
        
        return 0.0
    
    def _get_sensor_unit(self, sensor_type: SensorType) -> str:
        """Get unit for sensor type"""
        units = {
            SensorType.TEMPERATURE: "°C",
            SensorType.HUMIDITY: "%",
            SensorType.WIND: "m/s"
        }
        return units.get(sensor_type, "unit")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Seed IoT Security Simulation Database")
    parser.add_argument("--database-url", default="sqlite:///./demo.db", help="Database URL")
    parser.add_argument("--clear", action="store_true", help="Clear existing data before seeding")
    
    args = parser.parse_args()
    
    if args.clear:
        print("Clearing existing database...")
        if os.path.exists("demo.db"):
            os.remove("demo.db")
    
    seeder = DataSeeder(args.database_url)
    seeder.seed_all()
    
    print("\nDatabase seeding completed!")
    print(f"Database file: {args.database_url}")
    print("\nYou can now start the cloud service to view the seeded data.")


if __name__ == "__main__":
    main()