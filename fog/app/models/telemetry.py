"""
Telemetry data models for fog service
"""

from typing import Optional, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator


class TelemetryPayload(BaseModel):
    """Raw telemetry payload from sensor"""
    sensor_id: str
    ts: str  # ISO timestamp
    type: str
    value: Optional[float] = None  # May be None if encrypted
    unit: Optional[str] = None    # May be None if encrypted
    nonce: str
    enc: bool = False
    sig: str
    ver: int = 1
    encrypted_data: Optional[Dict[str, str]] = None
    
    @validator('ts')
    def validate_timestamp(cls, v):
        """Validate ISO timestamp format"""
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except ValueError:
            raise ValueError('Invalid ISO timestamp format')
    
    @validator('ver')
    def validate_version(cls, v):
        """Validate protocol version"""
        if v != 1:
            raise ValueError('Unsupported protocol version')
        return v


class ProcessedTelemetry(BaseModel):
    """Processed and validated telemetry data"""
    sensor_id: str
    timestamp: datetime
    sensor_type: str
    value: float
    unit: str
    nonce: str
    signature_valid: bool
    timestamp_valid: bool
    nonce_valid: bool
    rate_limit_passed: bool
    decrypted: bool = False
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ValidationResult(BaseModel):
    """Result of telemetry validation"""
    valid: bool
    telemetry: Optional[ProcessedTelemetry] = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    security_events: list[Dict[str, Any]] = Field(default_factory=list)


class CloudTelemetryDTO(BaseModel):
    """DTO for sending telemetry to cloud service"""
    sensor_id: str
    timestamp: str  # ISO format
    sensor_type: str
    value: float
    unit: str
    fog_processed_at: str  # ISO format
    security_validated: bool
    
    @classmethod
    def from_processed(cls, telemetry: ProcessedTelemetry) -> 'CloudTelemetryDTO':
        """Create DTO from processed telemetry"""
        return cls(
            sensor_id=telemetry.sensor_id,
            timestamp=telemetry.timestamp.isoformat(),
            sensor_type=telemetry.sensor_type,
            value=telemetry.value,
            unit=telemetry.unit,
            fog_processed_at=datetime.utcnow().isoformat(),
            security_validated=(
                telemetry.signature_valid and
                telemetry.timestamp_valid and
                telemetry.nonce_valid and
                telemetry.rate_limit_passed
            )
        )