"""
Logging utilities for fog service
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Dict, Any


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'service': 'fog',
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'getMessage', 'exc_info', 
                          'exc_text', 'stack_info']:
                log_entry[key] = value
        
        return json.dumps(log_entry, default=str)


def setup_logging(level: str = "INFO") -> logging.Logger:
    """
    Setup structured logging for fog service
    
    Args:
        level: Logging level
        
    Returns:
        Configured logger
    """
    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    formatter = JSONFormatter()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger


def log_security_event(
    logger: logging.Logger,
    event_type: str,
    message: str,
    sensor_id: str = None,
    severity: str = "INFO",
    **kwargs
):
    """
    Log security-related event
    
    Args:
        logger: Logger instance
        event_type: Type of security event
        message: Event message
        sensor_id: Sensor identifier
        severity: Event severity
        **kwargs: Additional fields
    """
    extra = {
        'event_type': f"security.{event_type}",
        'sensor_id': sensor_id,
        'severity': severity,
        **kwargs
    }
    
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    
    level = level_map.get(severity.upper(), logging.INFO)
    logger.log(level, message, extra=extra)


def log_telemetry_event(
    logger: logging.Logger,
    event_type: str,
    message: str,
    sensor_id: str = None,
    **kwargs
):
    """
    Log telemetry-related event
    
    Args:
        logger: Logger instance
        event_type: Type of telemetry event
        message: Event message
        sensor_id: Sensor identifier
        **kwargs: Additional fields
    """
    extra = {
        'event_type': f"telemetry.{event_type}",
        'sensor_id': sensor_id,
        **kwargs
    }
    
    logger.info(message, extra=extra)


def log_performance_event(
    logger: logging.Logger,
    event_type: str,
    message: str,
    duration_ms: float = None,
    **kwargs
):
    """
    Log performance-related event
    
    Args:
        logger: Logger instance
        event_type: Type of performance event
        message: Event message
        duration_ms: Duration in milliseconds
        **kwargs: Additional fields
    """
    extra = {
        'event_type': f"performance.{event_type}",
        'duration_ms': duration_ms,
        **kwargs
    }
    
    logger.info(message, extra=extra)