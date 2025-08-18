"""
Unit tests for rate limiting
"""

import pytest
import asyncio
import time
from app.ratelimit.limiter import TokenBucket, LeakyBucket, RateLimiter


class TestTokenBucket:
    """Test token bucket rate limiter"""
    
    @pytest.mark.asyncio
    async def test_token_bucket_init(self):
        """Test token bucket initialization"""
        bucket = TokenBucket(capacity=10, refill_rate=5.0)
        
        assert bucket.capacity == 10
        assert bucket.refill_rate == 5.0
        assert bucket.tokens == 10  # Starts full
    
    @pytest.mark.asyncio
    async def test_token_bucket_consume_success(self):
        """Test successful token consumption"""
        bucket = TokenBucket(capacity=10, refill_rate=5.0)
        
        # Should be able to consume tokens initially
        result = await bucket.consume(3)
        assert result is True
        assert bucket.get_tokens() == 7
    
    @pytest.mark.asyncio
    async def test_token_bucket_consume_failure(self):
        """Test token consumption failure"""
        bucket = TokenBucket(capacity=5, refill_rate=1.0)
        
        # Consume all tokens
        result = await bucket.consume(5)
        assert result is True
        
        # Should fail to consume more
        result = await bucket.consume(1)
        assert result is False
        assert bucket.get_tokens() == 0
    
    @pytest.mark.asyncio
    async def test_token_bucket_refill(self):
        """Test token refill over time"""
        bucket = TokenBucket(capacity=10, refill_rate=10.0)  # 10 tokens per second
        
        # Consume all tokens
        await bucket.consume(10)
        assert bucket.get_tokens() == 0
        
        # Wait for refill
        await asyncio.sleep(0.5)  # Wait 0.5 seconds
        
        # Should have refilled ~5 tokens
        result = await bucket.consume(1)
        assert result is True
        
        # Check approximate token count (allow for timing variations)
        tokens = bucket.get_tokens()
        assert 3 <= tokens <= 6  # Should be around 4-5 tokens


class TestLeakyBucket:
    """Test leaky bucket rate limiter"""
    
    @pytest.mark.asyncio
    async def test_leaky_bucket_init(self):
        """Test leaky bucket initialization"""
        bucket = LeakyBucket(capacity=10, leak_rate=5.0)
        
        assert bucket.capacity == 10
        assert bucket.leak_rate == 5.0
        assert bucket.level == 0  # Starts empty
    
    @pytest.mark.asyncio
    async def test_leaky_bucket_add_success(self):
        """Test successful item addition"""
        bucket = LeakyBucket(capacity=10, leak_rate=5.0)
        
        # Should be able to add items initially
        result = await bucket.add(3)
        assert result is True
        assert bucket.get_level() == 3
    
    @pytest.mark.asyncio
    async def test_leaky_bucket_add_overflow(self):
        """Test bucket overflow"""
        bucket = LeakyBucket(capacity=5, leak_rate=1.0)
        
        # Fill bucket
        result = await bucket.add(5)
        assert result is True
        
        # Should fail to add more (overflow)
        result = await bucket.add(1)
        assert result is False
        assert bucket.get_level() == 5
    
    @pytest.mark.asyncio
    async def test_leaky_bucket_leak(self):
        """Test bucket leaking over time"""
        bucket = LeakyBucket(capacity=10, leak_rate=10.0)  # 10 items per second
        
        # Fill bucket
        await bucket.add(10)
        assert bucket.get_level() == 10
        
        # Wait for leak
        await asyncio.sleep(0.5)  # Wait 0.5 seconds
        
        # Should have leaked ~5 items
        level = bucket.get_level()
        assert 4 <= level <= 6  # Should be around 5 items


class TestRateLimiter:
    """Test rate limiter with per-sensor tracking"""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_init(self):
        """Test rate limiter initialization"""
        limiter = RateLimiter(
            messages_per_minute=60,
            burst_capacity=10,
            algorithm="token_bucket"
        )
        
        assert limiter.messages_per_minute == 60
        assert limiter.burst_capacity == 10
        assert limiter.algorithm == "token_bucket"
        assert len(limiter.limiters) == 0
        assert len(limiter.stats) == 0
    
    @pytest.mark.asyncio
    async def test_rate_limiter_allow_initial(self):
        """Test initial requests are allowed"""
        limiter = RateLimiter(
            messages_per_minute=60,
            burst_capacity=10,
            algorithm="token_bucket"
        )
        
        # First few requests should be allowed
        for i in range(5):
            result = await limiter.check_rate_limit("sensor-01")
            assert result is True
        
        # Check statistics
        stats = limiter.get_stats("sensor-01")
        assert stats['total_requests'] == 5
        assert stats['allowed_requests'] == 5
        assert stats['blocked_requests'] == 0
    
    @pytest.mark.asyncio
    async def test_rate_limiter_block_burst(self):
        """Test burst blocking"""
        limiter = RateLimiter(
            messages_per_minute=60,
            burst_capacity=3,  # Small burst capacity
            algorithm="token_bucket"
        )
        
        # First 3 should be allowed
        for i in range(3):
            result = await limiter.check_rate_limit("sensor-01")
            assert result is True
        
        # Next request should be blocked
        result = await limiter.check_rate_limit("sensor-01")
        assert result is False
        
        # Check statistics
        stats = limiter.get_stats("sensor-01")
        assert stats['total_requests'] == 4
        assert stats['allowed_requests'] == 3
        assert stats['blocked_requests'] == 1
    
    @pytest.mark.asyncio
    async def test_rate_limiter_per_sensor(self):
        """Test per-sensor rate limiting"""
        limiter = RateLimiter(
            messages_per_minute=60,
            burst_capacity=2,
            algorithm="token_bucket"
        )
        
        # Sensor 1: consume all tokens
        await limiter.check_rate_limit("sensor-01")
        await limiter.check_rate_limit("sensor-01")
        
        # Sensor 1 should be blocked
        result = await limiter.check_rate_limit("sensor-01")
        assert result is False
        
        # Sensor 2 should still be allowed
        result = await limiter.check_rate_limit("sensor-02")
        assert result is True
        
        # Check per-sensor stats
        stats1 = limiter.get_stats("sensor-01")
        stats2 = limiter.get_stats("sensor-02")
        
        assert stats1['blocked_requests'] == 1
        assert stats2['blocked_requests'] == 0
    
    @pytest.mark.asyncio
    async def test_rate_limiter_leaky_bucket(self):
        """Test leaky bucket algorithm"""
        limiter = RateLimiter(
            messages_per_minute=60,
            burst_capacity=3,
            algorithm="leaky_bucket"
        )
        
        # First few requests should be allowed
        for i in range(3):
            result = await limiter.check_rate_limit("sensor-01")
            assert result is True
        
        # Should be blocked when bucket is full
        result = await limiter.check_rate_limit("sensor-01")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_rate_limiter_recovery(self):
        """Test rate limiter recovery over time"""
        limiter = RateLimiter(
            messages_per_minute=120,  # 2 per second
            burst_capacity=2,
            algorithm="token_bucket"
        )
        
        # Consume all tokens
        await limiter.check_rate_limit("sensor-01")
        await limiter.check_rate_limit("sensor-01")
        
        # Should be blocked
        result = await limiter.check_rate_limit("sensor-01")
        assert result is False
        
        # Wait for refill
        await asyncio.sleep(1.0)  # Wait 1 second
        
        # Should be allowed again
        result = await limiter.check_rate_limit("sensor-01")
        assert result is True
    
    def test_rate_limiter_global_stats(self):
        """Test global statistics"""
        limiter = RateLimiter(
            messages_per_minute=60,
            burst_capacity=10,
            algorithm="token_bucket"
        )
        
        # Simulate some requests
        limiter.stats["sensor-01"] = {
            'total_requests': 10,
            'allowed_requests': 8,
            'blocked_requests': 2,
            'last_request': time.time()
        }
        limiter.stats["sensor-02"] = {
            'total_requests': 5,
            'allowed_requests': 5,
            'blocked_requests': 0,
            'last_request': time.time()
        }
        
        global_stats = limiter.get_stats()
        
        assert global_stats['global']['total_sensors'] == 2
        assert global_stats['global']['total_requests'] == 15
        assert global_stats['global']['total_allowed'] == 13
        assert global_stats['global']['total_blocked'] == 2
    
    def test_rate_limiter_reset_stats(self):
        """Test statistics reset"""
        limiter = RateLimiter(
            messages_per_minute=60,
            burst_capacity=10,
            algorithm="token_bucket"
        )
        
        # Add some stats
        limiter.stats["sensor-01"] = {
            'total_requests': 10,
            'allowed_requests': 8,
            'blocked_requests': 2,
            'last_request': time.time()
        }
        
        # Reset specific sensor
        limiter.reset_stats("sensor-01")
        assert "sensor-01" not in limiter.stats
        
        # Add stats again
        limiter.stats["sensor-01"] = {'total_requests': 5}
        limiter.stats["sensor-02"] = {'total_requests': 3}
        
        # Reset all
        limiter.reset_stats()
        assert len(limiter.stats) == 0
    
    @pytest.mark.asyncio
    async def test_rate_limiter_concurrent_access(self):
        """Test concurrent access to rate limiter"""
        limiter = RateLimiter(
            messages_per_minute=120,  # 2 per second
            burst_capacity=5,
            algorithm="token_bucket"
        )
        
        # Create multiple concurrent tasks
        async def make_requests(sensor_id, count):
            results = []
            for _ in range(count):
                result = await limiter.check_rate_limit(sensor_id)
                results.append(result)
            return results
        
        # Run concurrent tasks
        task1 = make_requests("sensor-01", 3)
        task2 = make_requests("sensor-01", 3)
        
        results1, results2 = await asyncio.gather(task1, task2)
        
        # Should have some successful and some failed requests
        total_allowed = sum(results1) + sum(results2)
        assert total_allowed <= 5  # Can't exceed burst capacity
        
        # Check final stats
        stats = limiter.get_stats("sensor-01")
        assert stats['total_requests'] == 6
        assert stats['allowed_requests'] == total_allowed
        assert stats['blocked_requests'] == 6 - total_allowed