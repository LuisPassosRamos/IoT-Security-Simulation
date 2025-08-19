"""
Common utilities for IoT sensors
"""

import hmac
import hashlib
import json
import base64
import time
import uuid
import random
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os


class SecurityUtils:
    """Security utilities for sensors"""
    
    @staticmethod
    def generate_hmac_signature(payload: Dict[str, Any], key: str) -> str:
        """
        Generate HMAC-SHA256 signature for payload
        
        Args:
            payload: Dictionary payload to sign
            key: HMAC key (hex string)
            
        Returns:
            Base64 encoded signature
        """
        # Create canonical representation
        canonical = SecurityUtils._canonicalize_payload(payload)
        
        # Convert hex key to bytes
        key_bytes = bytes.fromhex(key)
        
        # Generate HMAC
        signature = hmac.new(
            key_bytes,
            canonical.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        return base64.b64encode(signature).decode('utf-8')
    
    @staticmethod
    def verify_hmac_signature(payload: Dict[str, Any], signature: str, key: str) -> bool:
        """
        Verify HMAC-SHA256 signature
        
        Args:
            payload: Dictionary payload to verify
            signature: Base64 encoded signature
            key: HMAC key (hex string)
            
        Returns:
            True if signature is valid
        """
        try:
            expected_signature = SecurityUtils.generate_hmac_signature(payload, key)
            return hmac.compare_digest(signature, expected_signature)
        except Exception:
            return False
    
    @staticmethod
    def encrypt_payload(data: str, key: str) -> Dict[str, str]:
        """
        Encrypt data using AES-GCM
        
        Args:
            data: String data to encrypt
            key: AES key (hex string)
            
        Returns:
            Dictionary with encrypted data and nonce
        """
        key_bytes = bytes.fromhex(key)
        aesgcm = AESGCM(key_bytes)
        
        # Generate random nonce
        nonce = os.urandom(12)
        
        # Encrypt data
        ciphertext = aesgcm.encrypt(nonce, data.encode('utf-8'), None)
        
        return {
            'ciphertext': base64.b64encode(ciphertext).decode('utf-8'),
            'nonce': base64.b64encode(nonce).decode('utf-8')
        }
    
    @staticmethod
    def decrypt_payload(encrypted_data: Dict[str, str], key: str) -> str:
        """
        Decrypt data using AES-GCM
        
        Args:
            encrypted_data: Dictionary with ciphertext and nonce
            key: AES key (hex string)
            
        Returns:
            Decrypted string data
        """
        key_bytes = bytes.fromhex(key)
        aesgcm = AESGCM(key_bytes)
        
        # Decode base64 data
        ciphertext = base64.b64decode(encrypted_data['ciphertext'])
        nonce = base64.b64decode(encrypted_data['nonce'])
        
        # Decrypt data
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        
        return plaintext.decode('utf-8')
    
    @staticmethod
    def _canonicalize_payload(payload: Dict[str, Any]) -> str:
        """
        Create canonical representation of payload for signing
        
        Args:
            payload: Dictionary payload
            
        Returns:
            Canonical string representation
        """
        # Sort keys and create deterministic JSON
        return json.dumps(payload, sort_keys=True, separators=(',', ':'))


class PayloadGenerator:
    """Generate sensor payloads with security features"""
    
    def __init__(self, sensor_id: str, sensor_type: str, hmac_key: str, aes_key: Optional[str] = None):
        self.sensor_id = sensor_id
        self.sensor_type = sensor_type
        self.hmac_key = hmac_key
        self.aes_key = aes_key
    
    def generate_reading(self, value: float, unit: str, enable_encryption: bool = False) -> Dict[str, Any]:
        """
        Generate a sensor reading with security features
        
        Args:
            value: Sensor reading value
            unit: Unit of measurement
            enable_encryption: Whether to encrypt the payload
            
        Returns:
            Complete sensor payload with security features
        """
        # Generate base payload
        payload = {
            'sensor_id': self.sensor_id,
            'ts': datetime.now(timezone.utc).isoformat(),
            'type': self.sensor_type,
            'value': value,
            'unit': unit,
            'nonce': str(uuid.uuid4()),
            'enc': enable_encryption,
            'ver': 1
        }
        
        # Encrypt if requested
        if enable_encryption and self.aes_key:
            # Encrypt the sensitive data
            sensitive_data = json.dumps({
                'value': value,
                'type': self.sensor_type
            })
            encrypted = SecurityUtils.encrypt_payload(sensitive_data, self.aes_key)
            payload['encrypted_data'] = encrypted
            # Remove plaintext sensitive data
            del payload['value']
            del payload['type']
        
        # Generate signature (always on the full payload structure)
        signature_payload = payload.copy()
        if 'sig' in signature_payload:
            del signature_payload['sig']
        
        signature = SecurityUtils.generate_hmac_signature(signature_payload, self.hmac_key)
        payload['sig'] = signature
        
        return payload


class SensorSimulator:
    """Simulate sensor readings with realistic variations"""
    
    def __init__(self, sensor_type: str):
        self.sensor_type = sensor_type
        self.last_value = self._get_base_value()
    
    def _get_base_value(self) -> float:
        """Get base value for sensor type"""
        if self.sensor_type == 'temperature':
            return random.uniform(20.0, 25.0)  # °C
        elif self.sensor_type == 'humidity':
            return random.uniform(40.0, 60.0)  # %
        elif self.sensor_type == 'wind':
            return random.uniform(0.0, 10.0)  # m/s
        else:
            return random.uniform(0.0, 100.0)
    
    def get_unit(self) -> str:
        """Get unit for sensor type"""
        if self.sensor_type == 'temperature':
            return '°C'
        elif self.sensor_type == 'humidity':
            return '%'
        elif self.sensor_type == 'wind':
            return 'm/s'
        else:
            return 'unit'
    
    def get_reading(self) -> float:
        """Generate realistic sensor reading with small variations"""
        # Add small random variation to last value
        variation = random.uniform(-0.5, 0.5)
        
        if self.sensor_type == 'temperature':
            # Temperature varies slowly
            variation *= 0.1
            self.last_value += variation
            # Keep within reasonable bounds
            self.last_value = max(15.0, min(35.0, self.last_value))
            
        elif self.sensor_type == 'humidity':
            # Humidity can vary more
            variation *= 0.5
            self.last_value += variation
            # Keep within 0-100%
            self.last_value = max(20.0, min(80.0, self.last_value))
            
        elif self.sensor_type == 'wind':
            # Wind can be more variable
            variation *= 2.0
            self.last_value += variation
            # Keep non-negative
            self.last_value = max(0.0, min(25.0, self.last_value))
        
        return round(self.last_value, 2)


class ClockSkewSimulator:
    """Simulate clock skew for testing timestamp validation"""
    
    def __init__(self, max_skew_seconds: int = 10):
        self.max_skew_seconds = max_skew_seconds
        self._current_skew = 0
    
    def get_skewed_timestamp(self) -> str:
        """Get timestamp with simulated clock skew"""
        now = datetime.now(timezone.utc)
        skewed_time = now.timestamp() + self._current_skew
        return datetime.fromtimestamp(skewed_time, timezone.utc).isoformat()
    
    def add_random_skew(self):
        """Add random clock skew"""
        self._current_skew += random.uniform(-2, 2)
        # Keep within bounds
        self._current_skew = max(-self.max_skew_seconds, 
                                min(self.max_skew_seconds, self._current_skew))
    
    def reset_skew(self):
        """Reset clock skew to zero"""
        self._current_skew = 0