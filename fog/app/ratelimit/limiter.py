"""
Rate limiting implementation for fog service
"""

import time
import asyncio
from typing import Dict, Optional
from collections import defaultdict


class TokenBucket:
    """Token bucket rate limiter"""
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket
        
        Args:
            capacity: Maximum number of tokens
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self._lock = asyncio.Lock()
    
    async def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from bucket
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False if rate limited
        """
        async with self._lock:
            # Refill tokens based on elapsed time
            now = time.time()
            elapsed = now - self.last_refill
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.refill_rate
            )
            self.last_refill = now
            
            # Check if we have enough tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            return False
    
    def get_tokens(self) -> float:
        """Get current number of tokens"""
        return self.tokens


class LeakyBucket:
    """Leaky bucket rate limiter"""
    
    def __init__(self, capacity: int, leak_rate: float):
        """
        Initialize leaky bucket
        
        Args:
            capacity: Maximum bucket capacity
            leak_rate: Items leaked per second
        """
        self.capacity = capacity
        self.leak_rate = leak_rate
        self.level = 0.0
        self.last_leak = time.time()
        self._lock = asyncio.Lock()
    
    async def add(self, amount: int = 1) -> bool:
        """
        Try to add items to bucket
        
        Args:
            amount: Number of items to add
            
        Returns:
            True if items were added, False if bucket overflowed
        """
        async with self._lock:
            # Leak items based on elapsed time
            now = time.time()
            elapsed = now - self.last_leak
            self.level = max(0, self.level - elapsed * self.leak_rate)
            self.last_leak = now
            
            # Check if we can add items without overflow
            if self.level + amount <= self.capacity:
                self.level += amount
                return True
            
            return False
    
    def get_level(self) -> float:
        """Get current bucket level"""
        return self.level


class RateLimiter:
    """Rate limiter with per-sensor tracking"""
    
    def __init__(
        self,
        messages_per_minute: int = 60,
        burst_capacity: int = 10,
        algorithm: str = "token_bucket"
    ):
        """
        Initialize rate limiter
        
        Args:
            messages_per_minute: Maximum messages per minute per sensor
            burst_capacity: Burst capacity for rate limiting
            algorithm: Rate limiting algorithm ('token_bucket' or 'leaky_bucket')
        """
        self.messages_per_minute = messages_per_minute
        self.burst_capacity = burst_capacity
        self.algorithm = algorithm
        
        # Per-sensor rate limiters
        self.limiters: Dict[str, object] = {}
        
        # Statistics
        self.stats = defaultdict(lambda: {
            'total_requests': 0,
            'allowed_requests': 0,
            'blocked_requests': 0,
            'last_request': None
        })
    
    def _get_limiter(self, sensor_id: str):
        """Get or create rate limiter for sensor"""
        if sensor_id not in self.limiters:
            if self.algorithm == "token_bucket":
                # Convert per-minute to per-second rate
                refill_rate = self.messages_per_minute / 60.0
                self.limiters[sensor_id] = TokenBucket(
                    capacity=self.burst_capacity,
                    refill_rate=refill_rate
                )
            else:  # leaky_bucket
                leak_rate = self.messages_per_minute / 60.0
                self.limiters[sensor_id] = LeakyBucket(
                    capacity=self.burst_capacity,
                    leak_rate=leak_rate
                )
        
        return self.limiters[sensor_id]
    
    async def check_rate_limit(self, sensor_id: str) -> bool:
        """
        Check if request should be rate limited
        
        Args:
            sensor_id: Sensor identifier
            
        Returns:
            True if request is allowed, False if rate limited
        """
        limiter = self._get_limiter(sensor_id)
        
        # Update statistics
        self.stats[sensor_id]['total_requests'] += 1
        self.stats[sensor_id]['last_request'] = time.time()
        
        # Check rate limit
        if self.algorithm == "token_bucket":
            allowed = await limiter.consume()
        else:  # leaky_bucket
            allowed = await limiter.add()
        
        if allowed:
            self.stats[sensor_id]['allowed_requests'] += 1
        else:
            self.stats[sensor_id]['blocked_requests'] += 1
        
        return allowed
    
    def get_stats(self, sensor_id: Optional[str] = None) -> Dict:
        """
        Get rate limiting statistics
        
        Args:
            sensor_id: Specific sensor ID or None for all sensors
            
        Returns:
            Statistics dictionary
        """
        if sensor_id:
            return dict(self.stats.get(sensor_id, {}))
        
        return {
            'per_sensor': dict(self.stats),
            'global': {
                'total_sensors': len(self.stats),
                'total_requests': sum(s['total_requests'] for s in self.stats.values()),
                'total_allowed': sum(s['allowed_requests'] for s in self.stats.values()),
                'total_blocked': sum(s['blocked_requests'] for s in self.stats.values())
            }
        }
    
    def reset_stats(self, sensor_id: Optional[str] = None):
        """Reset statistics"""
        if sensor_id:
            if sensor_id in self.stats:
                del self.stats[sensor_id]
        else:
            self.stats.clear()