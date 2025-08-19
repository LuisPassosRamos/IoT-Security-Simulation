"""
MQTT worker for fog service
Subscribes to sensor telemetry and processes messages
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable
import paho.mqtt.client as mqtt
from cachetools import LRUCache

from app.core.config import FogConfig
from app.core.logging import log_security_event, log_telemetry_event, log_performance_event
from app.core.time import is_timestamp_valid, get_timestamp_age
from app.security.hmac import verify_hmac_signature, extract_signature_payload
from app.security.aead import decrypt_sensor_payload, is_payload_encrypted
from app.ratelimit.limiter import RateLimiter
from app.models.telemetry import TelemetryPayload, ProcessedTelemetry, ValidationResult
from app.models.events import EventType, EventSeverity, SecurityEvent


class MQTTWorker:
    """MQTT worker for processing sensor telemetry"""
    
    def __init__(self, config: FogConfig, cloud_sender: Callable):
        self.config = config
        self.cloud_sender = cloud_sender
        self.client: Optional[mqtt.Client] = None
        self.running = False
        
        # Initialize rate limiter
        self.rate_limiter = RateLimiter(
            messages_per_minute=config.rate_limit.messages_per_minute,
            burst_capacity=config.rate_limit.burst_capacity
        ) if config.security.enable_rate_limiting else None
        
        # Nonce cache for replay protection
        self.nonce_cache = LRUCache(
            maxsize=config.security.nonce_cache_size
        ) if config.security.enable_nonce_validation else None
        
        # Statistics
        self.stats = {
            'total_messages': 0,
            'valid_messages': 0,
            'invalid_signatures': 0,
            'invalid_timestamps': 0,
            'replay_attempts': 0,
            'rate_limited': 0,
            'encryption_failures': 0
        }
        
        # Logger
        import logging
        self.logger = logging.getLogger('fog.mqtt_worker')
    
    async def start(self):
        """Start MQTT worker"""
        self.running = True
        
        # Create MQTT client
        self.client = mqtt.Client("fog-service")
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        # Configure authentication
        if self.config.mqtt.username and self.config.mqtt.password:
            self.client.username_pw_set(
                self.config.mqtt.username,
                self.config.mqtt.password
            )
        
        # Configure TLS if enabled
        if self.config.mqtt.use_tls:
            import ssl
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            self.client.tls_set_context(context)
        
        try:
            # Connect to broker
            port = self.config.mqtt.secure_port if self.config.mqtt.use_tls else self.config.mqtt.port
            self.client.connect(self.config.mqtt.host, port, 60)
            
            # Start network loop
            self.client.loop_start()
            
            self.logger.info(f"MQTT worker started, connected to {self.config.mqtt.host}:{port}")
            
        except Exception as e:
            self.logger.error(f"Failed to start MQTT worker: {e}")
            raise
    
    async def stop(self):
        """Stop MQTT worker"""
        self.running = False
        
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
        
        self.logger.info("MQTT worker stopped")
    
    def _on_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            self.logger.info("Connected to MQTT broker")
            
            # Subscribe to telemetry topics
            topic = "greenhouse/+/telemetry"
            client.subscribe(topic, qos=1)
            self.logger.info(f"Subscribed to {topic}")
            
        else:
            self.logger.error(f"Failed to connect to MQTT broker: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback"""
        if rc != 0:
            self.logger.warning(f"Unexpected disconnection from MQTT broker: {rc}")
        else:
            self.logger.info("Disconnected from MQTT broker")
    
    def _on_message(self, client, userdata, msg):
        """MQTT message callback"""
        try:
            # Parse message
            topic_parts = msg.topic.split('/')
            if len(topic_parts) != 3 or topic_parts[2] != 'telemetry':
                self.logger.warning(f"Invalid topic format: {msg.topic}")
                return
            
            sensor_id = topic_parts[1]
            payload = json.loads(msg.payload.decode())
            
            # Process message asynchronously
            asyncio.create_task(self._process_telemetry(sensor_id, payload))
            
        except Exception as e:
            self.logger.error(f"Error processing MQTT message: {e}")
    
    async def _process_telemetry(self, sensor_id: str, payload: Dict[str, Any]):
        """Process telemetry message"""
        start_time = asyncio.get_event_loop().time()
        self.stats['total_messages'] += 1
        
        try:
            # Validate and parse payload
            validation_result = await self._validate_telemetry(sensor_id, payload)
            
            if validation_result.valid:
                self.stats['valid_messages'] += 1
                
                # Send to cloud
                await self.cloud_sender(validation_result.telemetry)
                
                log_telemetry_event(
                    self.logger,
                    "processed",
                    f"Successfully processed telemetry from {sensor_id}",
                    sensor_id,
                    value=validation_result.telemetry.value,
                    unit=validation_result.telemetry.unit
                )
            else:
                # Log validation failures
                for error in validation_result.errors:
                    log_security_event(
                        self.logger,
                        "validation_failed",
                        error,
                        sensor_id,
                        severity="WARNING"
                    )
                
                # Update statistics based on error types
                for error in validation_result.errors:
                    if "signature" in error.lower():
                        self.stats['invalid_signatures'] += 1
                    elif "timestamp" in error.lower():
                        self.stats['invalid_timestamps'] += 1
                    elif "replay" in error.lower():
                        self.stats['replay_attempts'] += 1
                    elif "rate" in error.lower():
                        self.stats['rate_limited'] += 1
                    elif "encryption" in error.lower():
                        self.stats['encryption_failures'] += 1
            
            # Log security events
            for event in validation_result.security_events:
                log_security_event(
                    self.logger,
                    event['type'],
                    event['message'],
                    sensor_id,
                    severity=event.get('severity', 'INFO'),
                    **event.get('details', {})
                )
            
        except Exception as e:
            log_security_event(
                self.logger,
                "processing_error",
                f"Error processing telemetry: {e}",
                sensor_id,
                severity="ERROR"
            )
        
        finally:
            # Log performance
            processing_time = (asyncio.get_event_loop().time() - start_time) * 1000
            log_performance_event(
                self.logger,
                "telemetry_processing",
                f"Processed telemetry in {processing_time:.2f}ms",
                duration_ms=processing_time,
                sensor_id=sensor_id
            )
    
    async def _validate_telemetry(self, sensor_id: str, payload: Dict[str, Any]) -> ValidationResult:
        """Validate telemetry payload"""
        errors = []
        warnings = []
        security_events = []
        
        try:
            # Parse payload structure
            telemetry_payload = TelemetryPayload(**payload)
        except Exception as e:
            return ValidationResult(
                valid=False,
                errors=[f"Invalid payload structure: {e}"]
            )
        
        # Rate limiting check
        rate_limit_passed = True
        if self.rate_limiter and self.config.security.enable_rate_limiting:
            rate_limit_passed = await self.rate_limiter.check_rate_limit(sensor_id)
            if not rate_limit_passed:
                errors.append("Rate limit exceeded")
                security_events.append({
                    'type': 'rate_limit_exceeded',
                    'message': f"Rate limit exceeded for sensor {sensor_id}",
                    'severity': 'WARNING',
                    'details': {'sensor_id': sensor_id}
                })
        
        # Signature verification
        signature_valid = True
        if self.config.security.enable_signature_verification:
            hmac_key = self.config.security.sensor_hmac_keys.get(sensor_id)
            if not hmac_key:
                signature_valid = False
                errors.append(f"No HMAC key configured for sensor {sensor_id}")
            else:
                payload_without_sig, signature = extract_signature_payload(payload)
                if not signature:
                    signature_valid = False
                    errors.append("Missing signature")
                else:
                    signature_valid = verify_hmac_signature(payload_without_sig, signature, hmac_key)
                    if not signature_valid:
                        errors.append("Invalid HMAC signature")
                        security_events.append({
                            'type': 'invalid_signature',
                            'message': f"Invalid signature from sensor {sensor_id}",
                            'severity': 'ERROR',
                            'details': {'sensor_id': sensor_id, 'signature': signature}
                        })
        
        # Timestamp validation
        timestamp_valid = True
        if self.config.security.enable_timestamp_validation:
            timestamp_valid = is_timestamp_valid(
                telemetry_payload.ts,
                self.config.security.timestamp_window_seconds
            )
            if not timestamp_valid:
                age = get_timestamp_age(telemetry_payload.ts)
                errors.append(f"Timestamp outside valid window (age: {age:.1f}s)")
                security_events.append({
                    'type': 'invalid_timestamp',
                    'message': f"Invalid timestamp from sensor {sensor_id}",
                    'severity': 'WARNING',
                    'details': {'sensor_id': sensor_id, 'timestamp': telemetry_payload.ts, 'age_seconds': age}
                })
        
        # Nonce validation (replay protection)
        nonce_valid = True
        if self.nonce_cache and self.config.security.enable_nonce_validation:
            if telemetry_payload.nonce in self.nonce_cache:
                nonce_valid = False
                errors.append("Nonce already used (replay attack)")
                security_events.append({
                    'type': 'replay_attack',
                    'message': f"Replay attack detected from sensor {sensor_id}",
                    'severity': 'ERROR',
                    'details': {'sensor_id': sensor_id, 'nonce': telemetry_payload.nonce}
                })
            else:
                # Add nonce to cache
                self.nonce_cache[telemetry_payload.nonce] = True
        
        # Decrypt if needed
        decrypted = False
        value = telemetry_payload.value
        unit = telemetry_payload.unit
        sensor_type = telemetry_payload.type
        
        if is_payload_encrypted(payload):
            decrypted_payload = decrypt_sensor_payload(payload, self.config.security.aes_gcm_key)
            if decrypted_payload:
                value = decrypted_payload.get('value')
                sensor_type = decrypted_payload.get('type', telemetry_payload.type)
                unit = unit or decrypted_payload.get('unit')
                decrypted = True
            else:
                errors.append("Failed to decrypt payload")
                security_events.append({
                    'type': 'decryption_failed',
                    'message': f"Failed to decrypt payload from sensor {sensor_id}",
                    'severity': 'ERROR',
                    'details': {'sensor_id': sensor_id}
                })
        
        # Check if we have required data
        if value is None or sensor_type is None:
            errors.append("Missing required telemetry data")
        
        # Overall validation
        valid = (
            len(errors) == 0 and
            signature_valid and
            timestamp_valid and
            nonce_valid and
            rate_limit_passed and
            value is not None
        )
        
        processed_telemetry = None
        if valid:
            processed_telemetry = ProcessedTelemetry(
                sensor_id=sensor_id,
                timestamp=datetime.fromisoformat(telemetry_payload.ts.replace('Z', '+00:00')),
                sensor_type=sensor_type,
                value=value,
                unit=unit or "",
                nonce=telemetry_payload.nonce,
                signature_valid=signature_valid,
                timestamp_valid=timestamp_valid,
                nonce_valid=nonce_valid,
                rate_limit_passed=rate_limit_passed,
                decrypted=decrypted
            )
        
        return ValidationResult(
            valid=valid,
            telemetry=processed_telemetry,
            errors=errors,
            warnings=warnings,
            security_events=security_events
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get worker statistics"""
        stats = self.stats.copy()
        
        # Add rate limiter stats if available
        if self.rate_limiter:
            stats['rate_limiter'] = self.rate_limiter.get_stats()
        
        return stats