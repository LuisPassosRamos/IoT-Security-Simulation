"""
JWT authentication for cloud service
"""

import jwt
import time
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os


class JWTHandler:
    """JWT token handler for authentication"""
    
    def __init__(self):
        self.secret_key = os.getenv('JWT_SECRET_KEY', 'default-secret-key')
        self.algorithm = "HS256"
        self.token_expire_minutes = 60
    
    def generate_token(self, subject: str, token_type: str = "access", expire_minutes: Optional[int] = None) -> str:
        """
        Generate JWT token
        
        Args:
            subject: Token subject (user ID, service name, etc.)
            token_type: Type of token (access, refresh, service)
            expire_minutes: Custom expiration time
            
        Returns:
            JWT token string
        """
        now = datetime.now(timezone.utc)
        expire_time = now + timedelta(minutes=expire_minutes or self.token_expire_minutes)
        
        payload = {
            'sub': subject,
            'iat': int(now.timestamp()),
            'exp': int(expire_time.timestamp()),
            'type': token_type
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify JWT token
        
        Args:
            token: JWT token string
            
        Returns:
            Token payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def get_subject(self, token: str) -> Optional[str]:
        """Get subject from token"""
        payload = self.verify_token(token)
        return payload.get('sub') if payload else None


# Global JWT handler instance
jwt_handler = JWTHandler()

# Security dependency
security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    FastAPI dependency to get current authenticated user
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        User subject from token
        
    Raises:
        HTTPException: If token is invalid
    """
    token = credentials.credentials
    payload = jwt_handler.verify_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return payload.get('sub')


def verify_service_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    FastAPI dependency to verify service-to-service token
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        Service name from token
        
    Raises:
        HTTPException: If token is invalid or not a service token
    """
    token = credentials.credentials
    payload = jwt_handler.verify_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if payload.get('type') != 'service':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Service token required",
        )
    
    return payload.get('sub')


def verify_api_key(api_key: str) -> bool:
    """
    Verify API key
    
    Args:
        api_key: API key to verify
        
    Returns:
        True if valid, False otherwise
    """
    valid_keys = {
        os.getenv('FOG_API_KEY', 'fog_api_key_default'),
        os.getenv('ADMIN_API_KEY', 'admin_api_key_default')
    }
    
    return api_key in valid_keys


def create_admin_token() -> str:
    """Create admin token for UI authentication"""
    return jwt_handler.generate_token(
        subject="admin",
        token_type="access",
        expire_minutes=480  # 8 hours
    )