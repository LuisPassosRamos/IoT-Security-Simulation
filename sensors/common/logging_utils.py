"""
Logging utilities for sensors
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
        if hasattr(record, 'sensor_id'):
            log_entry['sensor_id'] = record.sensor_id
        
        if hasattr(record, 'topic'):
            log_entry['topic'] = record.topic
        
        if hasattr(record, 'event_type'):
            log_entry['event_type'] = record.event_type
        
        return json.dumps(log_entry, default=str)


def setup_logging(
    level: str = "INFO",
    sensor_id: str = None,
    use_json: bool = True
) -> logging.Logger:
    """
    Setup structured logging for sensor
    
    Args:
        level: Logging level
        sensor_id: Sensor identifier
        use_json: Whether to use JSON formatting
        
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
    
    if use_json:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Create sensor-specific logger
    if sensor_id:
        sensor_logger = logging.getLogger(f"sensor.{sensor_id}")
        return sensor_logger
    
    return logger


def log_sensor_event(
    logger: logging.Logger,
    event_type: str,
    message: str,
    sensor_id: str = None,
    **kwargs
):
    """
    Log sensor event with structured data
    
    Args:
        logger: Logger instance
        event_type: Type of event
        message: Event message
        sensor_id: Sensor identifier
        **kwargs: Additional fields
    """
    extra = {
        'event_type': event_type,
        'sensor_id': sensor_id,
        **kwargs
    }
    
    logger.info(message, extra=extra)


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