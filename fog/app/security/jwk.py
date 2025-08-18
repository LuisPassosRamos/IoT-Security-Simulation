"""
JWT utilities for fog service
"""

import jwt
import time
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta


def generate_service_token(
    service_name: str,
    secret_key: str,
    expire_minutes: int = 60,
    algorithm: str = "HS256"
) -> str:
    """
    Generate JWT token for service-to-service communication
    
    Args:
        service_name: Name of the service
        secret_key: JWT secret key
        expire_minutes: Token expiration time in minutes
        algorithm: JWT algorithm
        
    Returns:
        JWT token string
    """
    now = datetime.now(timezone.utc)
    expire_time = now + timedelta(minutes=expire_minutes)
    
    payload = {
        'sub': service_name,
        'iat': int(now.timestamp()),
        'exp': int(expire_time.timestamp()),
        'type': 'service'
    }
    
    return jwt.encode(payload, secret_key, algorithm=algorithm)


def verify_service_token(
    token: str,
    secret_key: str,
    algorithm: str = "HS256"
) -> Optional[Dict[str, Any]]:
    """
    Verify JWT service token
    
    Args:
        token: JWT token string
        secret_key: JWT secret key
        algorithm: JWT algorithm
        
    Returns:
        Token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        
        # Check if token is for service communication
        if payload.get('type') != 'service':
            return None
        
        return payload
        
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def create_auth_header(token: str) -> Dict[str, str]:
    """
    Create authorization header with Bearer token
    
    Args:
        token: JWT token
        
    Returns:
        Authorization header dictionary
    """
    return {'Authorization': f'Bearer {token}'}


def extract_bearer_token(auth_header: str) -> Optional[str]:
    """
    Extract token from Bearer authorization header
    
    Args:
        auth_header: Authorization header value
        
    Returns:
        Token string or None if invalid format
    """
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    
    return auth_header[7:]  # Remove 'Bearer ' prefix