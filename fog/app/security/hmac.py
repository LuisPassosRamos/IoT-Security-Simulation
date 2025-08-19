"""
HMAC signature verification for fog service
"""

import hmac
import hashlib
import json
import base64
from typing import Dict, Any, Optional


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
    canonical = _canonicalize_payload(payload)
    
    # Convert hex key to bytes
    key_bytes = bytes.fromhex(key)
    
    # Generate HMAC
    signature = hmac.new(
        key_bytes,
        canonical.encode('utf-8'),
        hashlib.sha256
    ).digest()
    
    return base64.b64encode(signature).decode('utf-8')


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
        expected_signature = generate_hmac_signature(payload, key)
        return hmac.compare_digest(signature, expected_signature)
    except Exception:
        return False


def _canonicalize_payload(payload: Dict[str, Any]) -> str:
    """
    Create canonical representation of payload for signing
    
    Args:
        payload: Dictionary payload
        
    Returns:
        Canonical string representation
    """
    # Remove signature field if present
    payload_copy = payload.copy()
    if 'sig' in payload_copy:
        del payload_copy['sig']
    
    # Sort keys and create deterministic JSON
    return json.dumps(payload_copy, sort_keys=True, separators=(',', ':'))


def extract_signature_payload(payload: Dict[str, Any]) -> tuple[Dict[str, Any], Optional[str]]:
    """
    Extract signature from payload and return both
    
    Args:
        payload: Full payload with signature
        
    Returns:
        Tuple of (payload without signature, signature)
    """
    signature = payload.get('sig')
    payload_without_sig = payload.copy()
    
    if 'sig' in payload_without_sig:
        del payload_without_sig['sig']
    
    return payload_without_sig, signature