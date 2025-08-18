"""
Cryptographic utilities for cloud service
"""

import hashlib
import secrets
import base64
from typing import Optional


def generate_secure_token(length: int = 32) -> str:
    """
    Generate cryptographically secure random token
    
    Args:
        length: Token length in bytes
        
    Returns:
        Hex encoded token
    """
    return secrets.token_hex(length)


def generate_api_key(prefix: str = "api", length: int = 32) -> str:
    """
    Generate API key with prefix
    
    Args:
        prefix: Key prefix
        length: Random part length in bytes
        
    Returns:
        API key with prefix
    """
    random_part = secrets.token_hex(length)
    return f"{prefix}_{random_part}"


def hash_password(password: str) -> str:
    """
    Hash password using PBKDF2
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password
    """
    salt = secrets.token_bytes(32)
    pwdhash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100000  # 100k iterations
    )
    
    # Combine salt and hash
    combined = salt + pwdhash
    return base64.b64encode(combined).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify password against hash
    
    Args:
        password: Plain text password
        hashed: Hashed password
        
    Returns:
        True if password matches
    """
    try:
        combined = base64.b64decode(hashed.encode('utf-8'))
        salt = combined[:32]
        stored_hash = combined[32:]
        
        pwdhash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100000
        )
        
        return secrets.compare_digest(stored_hash, pwdhash)
    except Exception:
        return False


def generate_nonce(length: int = 16) -> str:
    """
    Generate cryptographic nonce
    
    Args:
        length: Nonce length in bytes
        
    Returns:
        Base64 encoded nonce
    """
    nonce = secrets.token_bytes(length)
    return base64.b64encode(nonce).decode('utf-8')


def hash_data(data: str, algorithm: str = 'sha256') -> str:
    """
    Hash data using specified algorithm
    
    Args:
        data: Data to hash
        algorithm: Hash algorithm
        
    Returns:
        Hex encoded hash
    """
    hasher = hashlib.new(algorithm)
    hasher.update(data.encode('utf-8'))
    return hasher.hexdigest()


def generate_csrf_token() -> str:
    """Generate CSRF token"""
    return generate_secure_token(24)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for security
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove dangerous characters
    dangerous_chars = ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*']
    sanitized = filename
    
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '_')
    
    # Limit length
    if len(sanitized) > 255:
        sanitized = sanitized[:255]
    
    # Ensure not empty
    if not sanitized or sanitized.isspace():
        sanitized = f"file_{generate_secure_token(8)}"
    
    return sanitized


def mask_sensitive_data(data: str, mask_char: str = '*', reveal_chars: int = 4) -> str:
    """
    Mask sensitive data for logging
    
    Args:
        data: Sensitive data to mask
        mask_char: Character to use for masking
        reveal_chars: Number of characters to reveal at start/end
        
    Returns:
        Masked data
    """
    if len(data) <= reveal_chars * 2:
        return mask_char * len(data)
    
    start = data[:reveal_chars]
    end = data[-reveal_chars:]
    middle = mask_char * (len(data) - reveal_chars * 2)
    
    return f"{start}{middle}{end}"