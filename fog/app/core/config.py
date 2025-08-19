"""
Configuration management for fog service
"""

import os
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class MQTTConfig:
    """MQTT configuration"""
    host: str
    port: int
    secure_port: int
    username: Optional[str] = None
    password: Optional[str] = None
    use_tls: bool = False


@dataclass
class SecurityConfig:
    """Security configuration"""
    sensor_hmac_keys: Dict[str, str]
    aes_gcm_key: str
    jwt_secret: str
    enable_signature_verification: bool = True
    enable_timestamp_validation: bool = True
    enable_nonce_validation: bool = True
    enable_rate_limiting: bool = True
    timestamp_window_seconds: int = 120
    nonce_cache_size: int = 10000


@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    messages_per_minute: int = 60
    burst_capacity: int = 10


@dataclass
class CloudConfig:
    """Cloud service configuration"""
    url: str
    api_key: str
    timeout_seconds: int = 30


@dataclass
class FogConfig:
    """Main fog service configuration"""
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    mqtt: MQTTConfig = None
    security: SecurityConfig = None
    rate_limit: RateLimitConfig = None
    cloud: CloudConfig = None


def load_config() -> FogConfig:
    """Load configuration from environment variables"""
    
    # MQTT configuration
    mqtt_config = MQTTConfig(
        host=os.getenv('MQTT_HOST', 'localhost'),
        port=int(os.getenv('MQTT_PORT', '1883')),
        secure_port=int(os.getenv('MQTT_SECURE_PORT', '8883')),
        username=os.getenv('MQTT_USERNAME'),
        password=os.getenv('MQTT_PASSWORD'),
        use_tls=os.getenv('ENABLE_TLS', 'false').lower() == 'true'
    )
    
    # Security configuration
    sensor_hmac_keys = {
        'temp-01': os.getenv('SENSOR_TEMP_HMAC_KEY', ''),
        'humidity-01': os.getenv('SENSOR_HUMIDITY_HMAC_KEY', ''),
        'wind-01': os.getenv('SENSOR_WIND_HMAC_KEY', '')
    }
    
    security_config = SecurityConfig(
        sensor_hmac_keys=sensor_hmac_keys,
        aes_gcm_key=os.getenv('AES_GCM_KEY', ''),
        jwt_secret=os.getenv('JWT_SECRET_KEY', ''),
        enable_signature_verification=os.getenv('ENABLE_SIGNATURE_VERIFICATION', 'true').lower() == 'true',
        enable_timestamp_validation=os.getenv('ENABLE_TIMESTAMP_VALIDATION', 'true').lower() == 'true',
        enable_nonce_validation=os.getenv('ENABLE_NONCE_VALIDATION', 'true').lower() == 'true',
        enable_rate_limiting=os.getenv('ENABLE_RATE_LIMITING', 'true').lower() == 'true',
        timestamp_window_seconds=int(os.getenv('TIMESTAMP_WINDOW_SECONDS', '120')),
        nonce_cache_size=int(os.getenv('NONCE_CACHE_SIZE', '10000'))
    )
    
    # Rate limiting configuration
    rate_limit_config = RateLimitConfig(
        messages_per_minute=int(os.getenv('RATE_LIMIT_PER_MINUTE', '60')),
        burst_capacity=int(os.getenv('RATE_LIMIT_BURST', '10'))
    )
    
    # Cloud configuration
    cloud_config = CloudConfig(
        url=os.getenv('CLOUD_URL', 'https://localhost:8443'),
        api_key=os.getenv('FOG_API_KEY', ''),
        timeout_seconds=int(os.getenv('CLOUD_TIMEOUT_SECONDS', '30'))
    )
    
    return FogConfig(
        host=os.getenv('FOG_HOST', '0.0.0.0'),
        port=int(os.getenv('FOG_PORT', '8000')),
        log_level=os.getenv('LOG_LEVEL', 'INFO'),
        mqtt=mqtt_config,
        security=security_config,
        rate_limit=rate_limit_config,
        cloud=cloud_config
    )