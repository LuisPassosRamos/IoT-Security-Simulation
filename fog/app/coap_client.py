"""
CoAP client for fog service
Makes on-demand requests to sensors
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional, List
from aiocoap import Context, Message, Code
from aiocoap.numbers import ContentFormat

from app.core.logging import log_performance_event, log_security_event
from app.models.telemetry import TelemetryPayload, ValidationResult
from app.security.hmac import verify_hmac_signature, extract_signature_payload
from app.security.aead import decrypt_sensor_payload


class CoAPClient:
    """CoAP client for requesting sensor data"""
    
    def __init__(self, config):
        self.config = config
        self.context: Optional[Context] = None
        self.logger = None
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'timeout_requests': 0,
            'invalid_responses': 0
        }
    
    async def start(self):
        """Start CoAP client"""
        try:
            self.context = await Context.create_client_context()
            
            import logging
            self.logger = logging.getLogger('fog.coap_client')
            self.logger.info("CoAP client started")
            
        except Exception as e:
            raise Exception(f"Failed to start CoAP client: {e}")
    
    async def stop(self):
        """Stop CoAP client"""
        if self.context:
            await self.context.shutdown()
            self.logger.info("CoAP client stopped")
    
    async def get_sensor_reading(
        self,
        sensor_host: str,
        sensor_port: int = 5683,
        path: str = "current",
        timeout: float = 10.0
    ) -> Optional[ValidationResult]:
        """
        Get current reading from sensor via CoAP
        
        Args:
            sensor_host: Sensor hostname/IP
            sensor_port: CoAP port
            path: Resource path
            timeout: Request timeout in seconds
            
        Returns:
            ValidationResult with sensor data or None if failed
        """
        if not self.context:
            self.logger.error("CoAP client not started")
            return None
        
        start_time = time.time()
        self.stats['total_requests'] += 1
        
        try:
            # Create request
            uri = f"coap://{sensor_host}:{sensor_port}/{path}"
            request = Message(code=Code.GET, uri=uri)
            
            self.logger.debug(f"Sending CoAP GET request to {uri}")
            
            # Send request with timeout
            response = await asyncio.wait_for(
                self.context.request(request).response,
                timeout=timeout
            )
            
            processing_time = (time.time() - start_time) * 1000
            
            if response.code.is_successful():
                # Parse JSON response
                payload = json.loads(response.payload.decode('utf-8'))
                
                # Validate the response
                validation_result = await self._validate_coap_response(sensor_host, payload)
                
                if validation_result.valid:
                    self.stats['successful_requests'] += 1
                    
                    log_performance_event(
                        self.logger,
                        "coap_request_success",
                        f"CoAP request to {sensor_host} successful",
                        duration_ms=processing_time,
                        sensor_host=sensor_host,
                        response_size=len(response.payload)
                    )
                else:
                    self.stats['invalid_responses'] += 1
                    
                    log_security_event(
                        self.logger,
                        "coap_invalid_response",
                        f"Invalid CoAP response from {sensor_host}",
                        severity="WARNING",
                        sensor_host=sensor_host,
                        errors=validation_result.errors
                    )
                
                return validation_result
            else:
                self.stats['failed_requests'] += 1
                self.logger.warning(f"CoAP request to {uri} failed with code: {response.code}")
                return None
                
        except asyncio.TimeoutError:
            self.stats['timeout_requests'] += 1
            processing_time = (time.time() - start_time) * 1000
            
            log_security_event(
                self.logger,
                "coap_timeout",
                f"CoAP request to {sensor_host} timed out",
                severity="WARNING",
                sensor_host=sensor_host,
                timeout_seconds=timeout,
                duration_ms=processing_time
            )
            return None
            
        except Exception as e:
            self.stats['failed_requests'] += 1
            processing_time = (time.time() - start_time) * 1000
            
            log_security_event(
                self.logger,
                "coap_error",
                f"CoAP request to {sensor_host} failed: {e}",
                severity="ERROR",
                sensor_host=sensor_host,
                error=str(e),
                duration_ms=processing_time
            )
            return None
    
    async def _validate_coap_response(self, sensor_host: str, payload: Dict[str, Any]) -> ValidationResult:
        """
        Validate CoAP response from sensor
        
        Args:
            sensor_host: Sensor hostname
            payload: Response payload
            
        Returns:
            ValidationResult
        """
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
        
        sensor_id = telemetry_payload.sensor_id
        
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
                            'type': 'coap_invalid_signature',
                            'message': f"Invalid signature in CoAP response from {sensor_host}",
                            'severity': 'ERROR',
                            'details': {'sensor_id': sensor_id, 'sensor_host': sensor_host}
                        })
        
        # Timestamp validation (more lenient for CoAP as it's on-demand)
        timestamp_valid = True
        if self.config.security.enable_timestamp_validation:
            # Use a larger window for CoAP responses
            from app.core.time import is_timestamp_valid
            timestamp_valid = is_timestamp_valid(
                telemetry_payload.ts,
                self.config.security.timestamp_window_seconds * 2  # Double the window for CoAP
            )
            if not timestamp_valid:
                warnings.append("Timestamp outside valid window")
        
        # Decrypt if needed
        decrypted = False
        value = telemetry_payload.value
        unit = telemetry_payload.unit
        sensor_type = telemetry_payload.type
        
        if telemetry_payload.enc and 'encrypted_data' in payload:
            decrypted_payload = decrypt_sensor_payload(payload, self.config.security.aes_gcm_key)
            if decrypted_payload:
                value = decrypted_payload.get('value')
                sensor_type = decrypted_payload.get('type', telemetry_payload.type)
                unit = unit or decrypted_payload.get('unit')
                decrypted = True
            else:
                errors.append("Failed to decrypt payload")
                security_events.append({
                    'type': 'coap_decryption_failed',
                    'message': f"Failed to decrypt CoAP response from {sensor_host}",
                    'severity': 'ERROR',
                    'details': {'sensor_id': sensor_id, 'sensor_host': sensor_host}
                })
        
        # Check if we have required data
        if value is None or sensor_type is None:
            errors.append("Missing required telemetry data")
        
        # Overall validation (more lenient for CoAP)
        valid = (
            len(errors) == 0 and
            signature_valid and
            value is not None
        )
        
        processed_telemetry = None
        if valid:
            from datetime import datetime
            from app.models.telemetry import ProcessedTelemetry
            
            processed_telemetry = ProcessedTelemetry(
                sensor_id=sensor_id,
                timestamp=datetime.fromisoformat(telemetry_payload.ts.replace('Z', '+00:00')),
                sensor_type=sensor_type,
                value=value,
                unit=unit or "",
                nonce=telemetry_payload.nonce,
                signature_valid=signature_valid,
                timestamp_valid=timestamp_valid,
                nonce_valid=True,  # No nonce validation for CoAP
                rate_limit_passed=True,  # No rate limiting for CoAP
                decrypted=decrypted
            )
        
        return ValidationResult(
            valid=valid,
            telemetry=processed_telemetry,
            errors=errors,
            warnings=warnings,
            security_events=security_events
        )
    
    async def poll_sensors(self, sensor_configs: List[Dict[str, Any]]) -> List[ValidationResult]:
        """
        Poll multiple sensors concurrently
        
        Args:
            sensor_configs: List of sensor configuration dicts with 'host', 'port', 'id'
            
        Returns:
            List of ValidationResults
        """
        tasks = []
        
        for config in sensor_configs:
            task = self.get_sensor_reading(
                sensor_host=config['host'],
                sensor_port=config.get('port', 5683),
                timeout=config.get('timeout', 10.0)
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and None results
        valid_results = []
        for result in results:
            if isinstance(result, ValidationResult):
                valid_results.append(result)
            elif isinstance(result, Exception):
                self.logger.error(f"Error polling sensor: {result}")
        
        return valid_results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics"""
        return self.stats.copy()