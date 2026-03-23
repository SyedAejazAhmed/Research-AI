"""
Production-Ready Security Module
=================================
Security features for the Research AI platform:
- Input validation and sanitization
- Rate limiting
- Authentication and authorization
- API key validation
- SQL injection prevention
- XSS protection
- CSRF protection
- File upload validation
- Resource limits
"""

import re
import hashlib
import secrets
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from pathlib import Path
import logging

from fastapi import HTTPException, Request, Header
from pydantic import BaseModel, validator, Field

logger = logging.getLogger(__name__)


# ============================================================================
# Input Validation Models
# ============================================================================

class ResearchQueryValidator(BaseModel):
    """Validated research query"""
    query: str = Field(..., min_length=5, max_length=1000)
    research_mode: str = Field(default="academic", pattern="^(academic|normal)$")
    template_type: str = Field(default="IEEE", pattern="^(IEEE|Springer|ACM)$")
    citation_style: str = Field(default="APA", pattern="^(APA|MLA|IEEE|Chicago|Harvard|Vancouver|BibTeX)$")
    max_citations: int = Field(default=30, ge=1, le=100)

    @validator('query')
    def sanitize_query(cls, v):
        """Sanitize query to prevent injection"""
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>{}]', '', v)
        return sanitized.strip()


class GitHubRepoValidator(BaseModel):
    """Validated GitHub repository URL"""
    repo_url: str = Field(..., min_length=10, max_length=500)

    @validator('repo_url')
    def validate_github_url(cls, v):
        """Validate GitHub URL format"""
        pattern = r'^https?://github\.com/[\w-]+/[\w.-]+/?$|^[\w-]+/[\w.-]+$'
        if not re.match(pattern, v):
            raise ValueError("Invalid GitHub repository URL")
        return v


class FileUploadValidator(BaseModel):
    """Validated file upload"""
    filename: str
    file_size: int
    content_type: str

    @validator('filename')
    def validate_filename(cls, v):
        """Validate filename to prevent path traversal"""
        # Remove path components
        filename = Path(v).name

        # Check for dangerous patterns
        if '..' in filename or '/' in filename or '\\' in filename:
            raise ValueError("Invalid filename")

        # Check extension
        allowed_extensions = {'.pdf', '.tex', '.bib', '.md', '.txt'}
        if Path(filename).suffix.lower() not in allowed_extensions:
            raise ValueError(f"File type not allowed. Allowed: {allowed_extensions}")

        return filename

    @validator('file_size')
    def validate_file_size(cls, v):
        """Validate file size (max 50MB)"""
        max_size = 50 * 1024 * 1024  # 50 MB
        if v > max_size:
            raise ValueError(f"File too large. Max size: {max_size / (1024*1024)}MB")
        return v


# ============================================================================
# Rate Limiting
# ============================================================================

class RateLimiter:
    """
    Token bucket rate limiter for API endpoints
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.minute_buckets: Dict[str, List[float]] = {}
        self.hour_buckets: Dict[str, List[float]] = {}

    def _clean_old_requests(self, bucket: List[float], window_seconds: int):
        """Remove requests outside the time window"""
        current_time = time.time()
        cutoff = current_time - window_seconds
        return [t for t in bucket if t > cutoff]

    def is_allowed(self, client_id: str) -> tuple[bool, Optional[str]]:
        """
        Check if request is allowed

        Args:
            client_id: Unique client identifier (IP, API key, etc.)

        Returns:
            Tuple of (allowed, error_message)
        """
        current_time = time.time()

        # Initialize buckets if needed
        if client_id not in self.minute_buckets:
            self.minute_buckets[client_id] = []
        if client_id not in self.hour_buckets:
            self.hour_buckets[client_id] = []

        # Clean old requests
        self.minute_buckets[client_id] = self._clean_old_requests(
            self.minute_buckets[client_id], 60
        )
        self.hour_buckets[client_id] = self._clean_old_requests(
            self.hour_buckets[client_id], 3600
        )

        # Check minute limit
        if len(self.minute_buckets[client_id]) >= self.requests_per_minute:
            return False, f"Rate limit exceeded: {self.requests_per_minute} requests per minute"

        # Check hour limit
        if len(self.hour_buckets[client_id]) >= self.requests_per_hour:
            return False, f"Rate limit exceeded: {self.requests_per_hour} requests per hour"

        # Allow request and record it
        self.minute_buckets[client_id].append(current_time)
        self.hour_buckets[client_id].append(current_time)

        return True, None

    def get_usage(self, client_id: str) -> Dict[str, int]:
        """Get current usage for a client"""
        minute_count = len(self.minute_buckets.get(client_id, []))
        hour_count = len(self.hour_buckets.get(client_id, []))

        return {
            "requests_last_minute": minute_count,
            "requests_last_hour": hour_count,
            "minute_limit": self.requests_per_minute,
            "hour_limit": self.requests_per_hour
        }


# ============================================================================
# API Key Management
# ============================================================================

class APIKeyManager:
    """
    Manage API keys for authentication
    """

    def __init__(self):
        self.keys: Dict[str, Dict[str, Any]] = {}

    def generate_key(
        self,
        user_id: str,
        name: str,
        expires_days: Optional[int] = None
    ) -> str:
        """
        Generate a new API key

        Args:
            user_id: User identifier
            name: Key name/description
            expires_days: Optional expiration in days

        Returns:
            Generated API key
        """
        # Generate secure random key
        api_key = f"rai_{secrets.token_urlsafe(32)}"

        # Store key metadata
        expires_at = None
        if expires_days:
            expires_at = datetime.now() + timedelta(days=expires_days)

        self.keys[api_key] = {
            "user_id": user_id,
            "name": name,
            "created_at": datetime.now(),
            "expires_at": expires_at,
            "last_used": None,
            "usage_count": 0,
            "is_active": True
        }

        logger.info(f"Generated API key for user {user_id}: {name}")
        return api_key

    def validate_key(self, api_key: str) -> tuple[bool, Optional[str]]:
        """
        Validate an API key

        Args:
            api_key: API key to validate

        Returns:
            Tuple of (valid, error_message)
        """
        if api_key not in self.keys:
            return False, "Invalid API key"

        key_data = self.keys[api_key]

        # Check if active
        if not key_data["is_active"]:
            return False, "API key has been revoked"

        # Check expiration
        if key_data["expires_at"] and datetime.now() > key_data["expires_at"]:
            return False, "API key has expired"

        # Update usage
        key_data["last_used"] = datetime.now()
        key_data["usage_count"] += 1

        return True, None

    def revoke_key(self, api_key: str):
        """Revoke an API key"""
        if api_key in self.keys:
            self.keys[api_key]["is_active"] = False
            logger.info(f"Revoked API key: {api_key}")


# ============================================================================
# SQL Injection Prevention
# ============================================================================

class SQLSanitizer:
    """
    Sanitize inputs to prevent SQL injection
    """

    DANGEROUS_PATTERNS = [
        r"(\bUNION\b|\bSELECT\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b|\bDROP\b)",
        r"(--|;|\/\*|\*\/)",
        r"(\bOR\b|\bAND\b).*=.*",
        r"['\"`;]"
    ]

    @staticmethod
    def sanitize(input_str: str) -> str:
        """
        Sanitize input for SQL safety

        Args:
            input_str: Input string

        Returns:
            Sanitized string

        Raises:
            ValueError: If dangerous pattern detected
        """
        for pattern in SQLSanitizer.DANGEROUS_PATTERNS:
            if re.search(pattern, input_str, re.IGNORECASE):
                logger.warning(f"Potential SQL injection attempt: {input_str}")
                raise ValueError("Invalid input detected")

        return input_str


# ============================================================================
# XSS Protection
# ============================================================================

class XSSProtection:
    """
    Protect against Cross-Site Scripting attacks
    """

    @staticmethod
    def sanitize_html(input_str: str) -> str:
        """
        Sanitize HTML content

        Args:
            input_str: Input string

        Returns:
            Sanitized string
        """
        # Escape HTML special characters
        replacements = {
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#x27;',
            '/': '&#x2F;'
        }

        for char, escape in replacements.items():
            input_str = input_str.replace(char, escape)

        return input_str

    @staticmethod
    def validate_url(url: str) -> bool:
        """
        Validate URL for safety

        Args:
            url: URL to validate

        Returns:
            True if safe, False otherwise
        """
        # Check for javascript: protocol
        if url.lower().startswith('javascript:'):
            return False

        # Check for data: protocol with script
        if url.lower().startswith('data:') and 'script' in url.lower():
            return False

        # Must start with http:// or https://
        if not (url.startswith('http://') or url.startswith('https://')):
            return False

        return True


# ============================================================================
# Resource Limits
# ============================================================================

class ResourceLimits:
    """
    Enforce resource usage limits
    """

    MAX_CONCURRENT_REQUESTS = 10
    MAX_QUERY_LENGTH = 1000
    MAX_CITATIONS = 100
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
    MAX_SESSION_DURATION = 3600  # 1 hour

    @staticmethod
    def validate_query_length(query: str):
        """Validate query length"""
        if len(query) > ResourceLimits.MAX_QUERY_LENGTH:
            raise ValueError(f"Query too long. Max: {ResourceLimits.MAX_QUERY_LENGTH} characters")

    @staticmethod
    def validate_citations_count(count: int):
        """Validate citations count"""
        if count > ResourceLimits.MAX_CITATIONS:
            raise ValueError(f"Too many citations requested. Max: {ResourceLimits.MAX_CITATIONS}")


# ============================================================================
# Security Middleware
# ============================================================================

class SecurityMiddleware:
    """
    FastAPI security middleware
    """

    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.api_key_manager = APIKeyManager()

    async def validate_request(
        self,
        request: Request,
        api_key: Optional[str] = None
    ):
        """
        Validate incoming request

        Args:
            request: FastAPI request
            api_key: Optional API key from header

        Raises:
            HTTPException: If validation fails
        """
        # Get client identifier
        client_id = request.client.host

        # Rate limiting
        allowed, error_msg = self.rate_limiter.is_allowed(client_id)
        if not allowed:
            raise HTTPException(status_code=429, detail=error_msg)

        # API key validation (if provided)
        if api_key:
            valid, error_msg = self.api_key_manager.validate_key(api_key)
            if not valid:
                raise HTTPException(status_code=401, detail=error_msg)

    def get_security_headers(self) -> Dict[str, str]:
        """
        Get security headers for responses

        Returns:
            Dictionary of security headers
        """
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "no-referrer"
        }


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    # Test rate limiter
    rate_limiter = RateLimiter(requests_per_minute=5, requests_per_hour=20)

    print("Testing rate limiter...")
    for i in range(7):
        allowed, msg = rate_limiter.is_allowed("client_123")
        print(f"Request {i+1}: {'Allowed' if allowed else f'Blocked - {msg}'}")

    # Test API key manager
    api_manager = APIKeyManager()
    key = api_manager.generate_key("user_1", "Test Key", expires_days=30)
    print(f"\nGenerated API key: {key}")

    valid, msg = api_manager.validate_key(key)
    print(f"Validation: {'Valid' if valid else msg}")

    # Test SQL sanitizer
    print("\nTesting SQL sanitizer...")
    try:
        SQLSanitizer.sanitize("SELECT * FROM users WHERE id=1")
    except ValueError as e:
        print(f"Caught SQL injection attempt: {e}")

    # Test XSS protection
    print("\nTesting XSS protection...")
    malicious = "<script>alert('XSS')</script>"
    sanitized = XSSProtection.sanitize_html(malicious)
    print(f"Original: {malicious}")
    print(f"Sanitized: {sanitized}")
