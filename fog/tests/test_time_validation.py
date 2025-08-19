"""
Unit tests for timestamp validation
"""

import pytest
from datetime import datetime, timezone, timedelta
from app.core.time import (
    get_current_timestamp,
    get_current_iso_timestamp,
    parse_iso_timestamp,
    is_timestamp_valid,
    get_timestamp_age
)


class TestTimeValidation:
    """Test timestamp validation functionality"""
    
    def test_get_current_timestamp(self):
        """Test current timestamp generation"""
        ts = get_current_timestamp()
        
        assert isinstance(ts, float)
        assert ts > 0
        
        # Should be recent (within last second)
        import time
        now = time.time()
        assert abs(now - ts) < 1.0
    
    def test_get_current_iso_timestamp(self):
        """Test current ISO timestamp generation"""
        iso_ts = get_current_iso_timestamp()
        
        assert isinstance(iso_ts, str)
        assert "T" in iso_ts
        assert iso_ts.endswith("+00:00") or iso_ts.endswith("Z")
        
        # Should be parseable
        parsed = parse_iso_timestamp(iso_ts)
        assert parsed is not None
    
    def test_parse_iso_timestamp_valid(self):
        """Test parsing valid ISO timestamps"""
        test_cases = [
            "2024-01-01T12:00:00Z",
            "2024-01-01T12:00:00+00:00",
            "2024-01-01T12:00:00.123456Z",
            "2024-01-01T12:00:00.123456+00:00",
            "2024-12-31T23:59:59Z"
        ]
        
        for timestamp_str in test_cases:
            parsed = parse_iso_timestamp(timestamp_str)
            assert parsed is not None
            assert isinstance(parsed, float)
            assert parsed > 0
    
    def test_parse_iso_timestamp_invalid(self):
        """Test parsing invalid ISO timestamps"""
        test_cases = [
            "invalid-timestamp",
            "2024-01-01",
            "12:00:00",
            "2024-13-01T12:00:00Z",  # Invalid month
            "2024-01-32T12:00:00Z",  # Invalid day
            "2024-01-01T25:00:00Z",  # Invalid hour
            "",
            None
        ]
        
        for timestamp_str in test_cases:
            parsed = parse_iso_timestamp(timestamp_str)
            assert parsed is None
    
    def test_is_timestamp_valid_current(self):
        """Test validation of current timestamp"""
        current_iso = get_current_iso_timestamp()
        
        assert is_timestamp_valid(current_iso, window_seconds=120)
        assert is_timestamp_valid(current_iso, window_seconds=1)
    
    def test_is_timestamp_valid_old(self):
        """Test validation of old timestamp"""
        # Create timestamp from 5 minutes ago
        old_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        old_iso = old_time.isoformat()
        
        assert not is_timestamp_valid(old_iso, window_seconds=60)  # Outside 1 minute window
        assert not is_timestamp_valid(old_iso, window_seconds=120)  # Outside 2 minute window
        assert is_timestamp_valid(old_iso, window_seconds=400)  # Within 6+ minute window
    
    def test_is_timestamp_valid_future(self):
        """Test validation of future timestamp"""
        # Create timestamp from 5 minutes in future
        future_time = datetime.now(timezone.utc) + timedelta(minutes=5)
        future_iso = future_time.isoformat()
        
        assert not is_timestamp_valid(future_iso, window_seconds=60)  # Outside 1 minute window
        assert not is_timestamp_valid(future_iso, window_seconds=120)  # Outside 2 minute window
        assert is_timestamp_valid(future_iso, window_seconds=400)  # Within 6+ minute window
    
    def test_is_timestamp_valid_edge_cases(self):
        """Test validation edge cases"""
        # Exactly at window boundary
        boundary_time = datetime.now(timezone.utc) - timedelta(seconds=120)
        boundary_iso = boundary_time.isoformat()
        
        assert is_timestamp_valid(boundary_iso, window_seconds=120)
        assert not is_timestamp_valid(boundary_iso, window_seconds=119)
        
        # Invalid timestamp string
        assert not is_timestamp_valid("invalid", window_seconds=120)
        assert not is_timestamp_valid("", window_seconds=120)
    
    def test_get_timestamp_age_current(self):
        """Test age calculation for current timestamp"""
        current_iso = get_current_iso_timestamp()
        age = get_timestamp_age(current_iso)
        
        assert age is not None
        assert isinstance(age, float)
        assert 0 <= age <= 1.0  # Should be very recent
    
    def test_get_timestamp_age_old(self):
        """Test age calculation for old timestamp"""
        old_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        old_iso = old_time.isoformat()
        
        age = get_timestamp_age(old_iso)
        
        assert age is not None
        assert isinstance(age, float)
        assert 290 <= age <= 310  # Should be around 300 seconds (5 minutes)
    
    def test_get_timestamp_age_future(self):
        """Test age calculation for future timestamp"""
        future_time = datetime.now(timezone.utc) + timedelta(minutes=5)
        future_iso = future_time.isoformat()
        
        age = get_timestamp_age(future_iso)
        
        assert age is not None
        assert isinstance(age, float)
        assert -310 <= age <= -290  # Should be around -300 seconds (negative age)
    
    def test_get_timestamp_age_invalid(self):
        """Test age calculation for invalid timestamp"""
        age = get_timestamp_age("invalid-timestamp")
        assert age is None
        
        age = get_timestamp_age("")
        assert age is None
    
    def test_timestamp_formats_consistency(self):
        """Test consistency between different timestamp formats"""
        # Test with Z suffix
        ts_z = "2024-01-01T12:00:00Z"
        parsed_z = parse_iso_timestamp(ts_z)
        
        # Test with +00:00 suffix
        ts_offset = "2024-01-01T12:00:00+00:00"
        parsed_offset = parse_iso_timestamp(ts_offset)
        
        # Should parse to same timestamp
        assert parsed_z == parsed_offset
    
    def test_timestamp_precision(self):
        """Test timestamp precision handling"""
        # Test without microseconds
        ts_no_micro = "2024-01-01T12:00:00Z"
        parsed_no_micro = parse_iso_timestamp(ts_no_micro)
        
        # Test with microseconds
        ts_micro = "2024-01-01T12:00:00.123456Z"
        parsed_micro = parse_iso_timestamp(ts_micro)
        
        # Both should parse successfully
        assert parsed_no_micro is not None
        assert parsed_micro is not None
        
        # Microsecond version should be slightly larger
        assert parsed_micro > parsed_no_micro
    
    def test_timezone_handling(self):
        """Test timezone handling in timestamps"""
        base_time = "2024-01-01T12:00:00"
        
        # UTC variations
        utc_z = parse_iso_timestamp(base_time + "Z")
        utc_offset = parse_iso_timestamp(base_time + "+00:00")
        
        # Different timezone
        plus_one = parse_iso_timestamp(base_time + "+01:00")
        minus_one = parse_iso_timestamp(base_time + "-01:00")
        
        assert utc_z == utc_offset
        assert plus_one < utc_z  # +01:00 is earlier in UTC
        assert minus_one > utc_z  # -01:00 is later in UTC
    
    def test_window_size_validation(self):
        """Test different window sizes"""
        # Current timestamp should be valid for any reasonable window
        current_iso = get_current_iso_timestamp()
        
        window_sizes = [1, 10, 60, 120, 300, 600, 3600]
        for window in window_sizes:
            assert is_timestamp_valid(current_iso, window_seconds=window)
        
        # Very old timestamp should only be valid for large windows
        very_old = datetime.now(timezone.utc) - timedelta(hours=2)
        very_old_iso = very_old.isoformat()
        
        assert not is_timestamp_valid(very_old_iso, window_seconds=60)
        assert not is_timestamp_valid(very_old_iso, window_seconds=3600)
        assert is_timestamp_valid(very_old_iso, window_seconds=10800)  # 3+ hours