"""
AES-GCM encryption/decryption for fog service
"""

import base64
import json
from typing import Dict, Any, Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def decrypt_payload(encrypted_data: Dict[str, str], key: str) -> Optional[str]:
    """
    Decrypt data using AES-GCM
    
    Args:
        encrypted_data: Dictionary with ciphertext and nonce
        key: AES key (hex string)
        
    Returns:
        Decrypted string data or None if decryption fails
    """
    try:
        key_bytes = bytes.fromhex(key)
        aesgcm = AESGCM(key_bytes)
        
        # Decode base64 data
        ciphertext = base64.b64decode(encrypted_data['ciphertext'])
        nonce = base64.b64decode(encrypted_data['nonce'])
        
        # Decrypt data
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        
        return plaintext.decode('utf-8')
        
    except Exception:
        return None


def encrypt_payload(data: str, key: str) -> Optional[Dict[str, str]]:
    """
    Encrypt data using AES-GCM
    
    Args:
        data: String data to encrypt
        key: AES key (hex string)
        
    Returns:
        Dictionary with encrypted data and nonce or None if encryption fails
    """
    try:
        key_bytes = bytes.fromhex(key)
        aesgcm = AESGCM(key_bytes)
        
        # Generate random nonce
        import os
        nonce = os.urandom(12)
        
        # Encrypt data
        ciphertext = aesgcm.encrypt(nonce, data.encode('utf-8'), None)
        
        return {
            'ciphertext': base64.b64encode(ciphertext).decode('utf-8'),
            'nonce': base64.b64encode(nonce).decode('utf-8')
        }
        
    except Exception:
        return None


def decrypt_sensor_payload(payload: Dict[str, Any], aes_key: str) -> Optional[Dict[str, Any]]:
    """
    Decrypt sensor payload if encrypted
    
    Args:
        payload: Sensor payload
        aes_key: AES encryption key
        
    Returns:
        Payload with decrypted data or None if decryption fails
    """
    if not payload.get('enc', False):
        # Not encrypted, return as-is
        return payload
    
    encrypted_data = payload.get('encrypted_data')
    if not encrypted_data:
        return None
    
    # Decrypt the sensitive data
    decrypted_json = decrypt_payload(encrypted_data, aes_key)
    if decrypted_json is None:
        return None
    
    try:
        decrypted_data = json.loads(decrypted_json)
        
        # Merge decrypted data back into payload
        result = payload.copy()
        result.update(decrypted_data)
        
        # Remove encrypted data
        if 'encrypted_data' in result:
            del result['encrypted_data']
        
        return result
        
    except json.JSONDecodeError:
        return None


def is_payload_encrypted(payload: Dict[str, Any]) -> bool:
    """
    Check if payload is encrypted
    
    Args:
        payload: Sensor payload
        
    Returns:
        True if payload is encrypted
    """
    return payload.get('enc', False) and 'encrypted_data' in payload