"""
Authentication API endpoints
"""

from fastapi import APIRouter, HTTPException, status, Depends, Header
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional

from app.security.jwt import jwt_handler, verify_api_key, create_admin_token, security
from app.security.crypto import verify_password


router = APIRouter(prefix="/api/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    """Login request model"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response model"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


class ApiKeyValidationResponse(BaseModel):
    """API key validation response"""
    valid: bool
    key_type: str


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Admin login endpoint
    
    Args:
        request: Login credentials
        
    Returns:
        JWT token for admin access
    """
    # Simple admin authentication (in production, use proper user management)
    admin_username = "admin"
    admin_password_hash = "admin123"  # In production, use hashed password
    
    if request.username != admin_username or request.password != admin_password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generate token
    token = create_admin_token()
    
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in=28800  # 8 hours
    )


@router.post("/validate-token")
async def validate_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Validate JWT token
    
    Args:
        credentials: JWT token
        
    Returns:
        Token validation result
    """
    token = credentials.credentials
    payload = jwt_handler.verify_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    return {
        "valid": True,
        "subject": payload.get('sub'),
        "type": payload.get('type'),
        "expires_at": payload.get('exp')
    }


@router.post("/validate-api-key", response_model=ApiKeyValidationResponse)
async def validate_api_key_endpoint(x_api_key: Optional[str] = Header(None)):
    """
    Validate API key
    
    Args:
        x_api_key: API key from header
        
    Returns:
        API key validation result
    """
    if not x_api_key:
        return ApiKeyValidationResponse(valid=False, key_type="none")
    
    is_valid = verify_api_key(x_api_key)
    
    # Determine key type (simplified)
    key_type = "unknown"
    if is_valid:
        if "fog" in x_api_key.lower():
            key_type = "fog"
        elif "admin" in x_api_key.lower():
            key_type = "admin"
        else:
            key_type = "service"
    
    return ApiKeyValidationResponse(valid=is_valid, key_type=key_type)


@router.post("/refresh")
async def refresh_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Refresh JWT token
    
    Args:
        credentials: Current JWT token
        
    Returns:
        New JWT token
    """
    token = credentials.credentials
    payload = jwt_handler.verify_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    # Generate new token with same subject
    new_token = jwt_handler.generate_token(
        subject=payload.get('sub'),
        token_type=payload.get('type', 'access')
    )
    
    return LoginResponse(
        access_token=new_token,
        token_type="bearer",
        expires_in=3600
    )


@router.post("/logout")
async def logout():
    """
    Logout endpoint (token invalidation would be handled client-side)
    """
    return {"message": "Logged out successfully"}