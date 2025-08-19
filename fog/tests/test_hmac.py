"""
Unit tests for HMAC signature verification
"""

import pytest
from app.security.hmac import (
    generate_hmac_signature,
    verify_hmac_signature,
    extract_signature_payload,
    _canonicalize_payload
)


class TestHMACSignature:
    """Test HMAC signature functionality"""
    
    def setup_method(self):
        """Setup test data"""
        self.test_key = "a1b2c3d4e5f6789abcdef0123456789abcdef0123456789abcdef0123456789a"
        self.test_payload = {
            "sensor_id": "temp-01",
            "ts": "2024-01-01T12:00:00Z",
            "type": "temperature",
            "value": 25.5,
            "unit": "°C",
            "nonce": "test-nonce-123",
            "enc": False,
            "ver": 1
        }
    
    def test_canonicalize_payload(self):
        """Test payload canonicalization"""
        canonical = _canonicalize_payload(self.test_payload)
        
        # Should be deterministic JSON
        assert isinstance(canonical, str)
        assert "sensor_id" in canonical
        assert "temp-01" in canonical
        
        # Should be consistent
        canonical2 = _canonicalize_payload(self.test_payload)
        assert canonical == canonical2
    
    def test_canonicalize_removes_signature(self):
        """Test that signature is removed during canonicalization"""
        payload_with_sig = self.test_payload.copy()
        payload_with_sig["sig"] = "test-signature"
        
        canonical_with_sig = _canonicalize_payload(payload_with_sig)
        canonical_without_sig = _canonicalize_payload(self.test_payload)
        
        assert canonical_with_sig == canonical_without_sig
        assert "sig" not in canonical_with_sig
    
    def test_generate_signature(self):
        """Test signature generation"""
        signature = generate_hmac_signature(self.test_payload, self.test_key)
        
        assert isinstance(signature, str)
        assert len(signature) > 0
        
        # Should be base64 encoded
        import base64
        try:
            decoded = base64.b64decode(signature)
            assert len(decoded) == 32  # SHA256 is 32 bytes
        except Exception:
            pytest.fail("Signature is not valid base64")
    
    def test_verify_valid_signature(self):
        """Test verification of valid signature"""
        signature = generate_hmac_signature(self.test_payload, self.test_key)
        
        is_valid = verify_hmac_signature(self.test_payload, signature, self.test_key)
        assert is_valid is True
    
    def test_verify_invalid_signature(self):
        """Test verification of invalid signature"""
        invalid_signature = "invalid-signature-123"
        
        is_valid = verify_hmac_signature(self.test_payload, invalid_signature, self.test_key)
        assert is_valid is False
    
    def test_verify_wrong_key(self):
        """Test verification with wrong key"""
        signature = generate_hmac_signature(self.test_payload, self.test_key)
        wrong_key = "b2c3d4e5f6789abcdef0123456789abcdef0123456789abcdef0123456789ab1"
        
        is_valid = verify_hmac_signature(self.test_payload, signature, wrong_key)
        assert is_valid is False
    
    def test_verify_modified_payload(self):
        """Test verification with modified payload"""
        signature = generate_hmac_signature(self.test_payload, self.test_key)
        
        modified_payload = self.test_payload.copy()
        modified_payload["value"] = 30.0  # Modify the value
        
        is_valid = verify_hmac_signature(modified_payload, signature, self.test_key)
        assert is_valid is False
    
    def test_extract_signature_payload(self):
        """Test signature extraction"""
        test_signature = "test-signature-123"
        payload_with_sig = self.test_payload.copy()
        payload_with_sig["sig"] = test_signature
        
        payload, signature = extract_signature_payload(payload_with_sig)
        
        assert signature == test_signature
        assert "sig" not in payload
        assert payload["sensor_id"] == self.test_payload["sensor_id"]
    
    def test_extract_signature_no_signature(self):
        """Test signature extraction when no signature present"""
        payload, signature = extract_signature_payload(self.test_payload)
        
        assert signature is None
        assert payload == self.test_payload
    
    def test_signature_order_independence(self):
        """Test that payload order doesn't affect signature"""
        # Create payload with different key order
        reordered_payload = {
            "ver": 1,
            "unit": "°C",
            "type": "temperature",
            "ts": "2024-01-01T12:00:00Z",
            "sensor_id": "temp-01",
            "value": 25.5,
            "nonce": "test-nonce-123",
            "enc": False
        }
        
        sig1 = generate_hmac_signature(self.test_payload, self.test_key)
        sig2 = generate_hmac_signature(reordered_payload, self.test_key)
        
        assert sig1 == sig2
        
        # Verify both work
        assert verify_hmac_signature(self.test_payload, sig1, self.test_key)
        assert verify_hmac_signature(reordered_payload, sig1, self.test_key)
    
    def test_empty_payload(self):
        """Test with empty payload"""
        empty_payload = {}
        signature = generate_hmac_signature(empty_payload, self.test_key)
        
        assert isinstance(signature, str)
        assert verify_hmac_signature(empty_payload, signature, self.test_key)
    
    def test_invalid_key_format(self):
        """Test with invalid key format"""
        invalid_key = "not-hex-key"
        
        with pytest.raises(ValueError):
            generate_hmac_signature(self.test_payload, invalid_key)
    
    def test_signature_consistency(self):
        """Test that same input always produces same signature"""
        sig1 = generate_hmac_signature(self.test_payload, self.test_key)
        sig2 = generate_hmac_signature(self.test_payload, self.test_key)
        sig3 = generate_hmac_signature(self.test_payload, self.test_key)
        
        assert sig1 == sig2 == sig3