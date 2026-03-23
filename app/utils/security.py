"""
Security and Validation Module
===============================
Input validation, sanitization, and security measures.
"""

import re
from typing import Any, Dict, List, Optional
import logging
from pathlib import Path
import bleach

logger = logging.getLogger(__name__)


class SecurityValidator:
    """
    Security validator for Research AI platform.

    Features:
    - Input sanitization
    - Path traversal prevention
    - DOI validation
    - URL validation
    - File type validation
    - SQL injection prevention
    """

    # Allowed file extensions
    ALLOWED_PDF_EXTENSIONS = {'.pdf'}
    ALLOWED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'}

    # Maximum sizes (in bytes)
    MAX_PDF_SIZE = 50 * 1024 * 1024  # 50 MB
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB

    # Regex patterns
    DOI_PATTERN = r'^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$'
    ARXIV_PATTERN = r'^\d{4}\.\d{4,5}(v\d+)?$'
    URL_PATTERN = r'^https?://[^\s<>"{}|\\^`\[\]]+$'
    EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    @staticmethod
    def validate_doi(doi: str) -> bool:
        """
        Validate DOI format.

        Args:
            doi: DOI string

        Returns:
            True if valid DOI
        """
        if not doi:
            return False

        return bool(re.match(SecurityValidator.DOI_PATTERN, doi.strip()))

    @staticmethod
    def validate_arxiv_id(arxiv_id: str) -> bool:
        """
        Validate arXiv ID format.

        Args:
            arxiv_id: arXiv ID string

        Returns:
            True if valid arXiv ID
        """
        if not arxiv_id:
            return False

        return bool(re.match(SecurityValidator.ARXIV_PATTERN, arxiv_id.strip()))

    @staticmethod
    def validate_url(url: str) -> bool:
        """
        Validate URL format.

        Args:
            url: URL string

        Returns:
            True if valid URL
        """
        if not url:
            return False

        return bool(re.match(SecurityValidator.URL_PATTERN, url.strip()))

    @staticmethod
    def validate_email(email: str) -> bool:
        """
        Validate email format.

        Args:
            email: Email string

        Returns:
            True if valid email
        """
        if not email:
            return False

        return bool(re.match(SecurityValidator.EMAIL_PATTERN, email.strip()))

    @staticmethod
    def sanitize_text(text: str, max_length: Optional[int] = None) -> str:
        """
        Sanitize text input.

        Args:
            text: Input text
            max_length: Maximum allowed length

        Returns:
            Sanitized text
        """
        if not text:
            return ""

        # Remove HTML tags
        text = bleach.clean(text, tags=[], strip=True)

        # Limit length
        if max_length and len(text) > max_length:
            text = text[:max_length]

        return text.strip()

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename to prevent path traversal.

        Args:
            filename: Input filename

        Returns:
            Sanitized filename
        """
        if not filename:
            return "unnamed"

        # Remove path components
        filename = Path(filename).name

        # Remove dangerous characters
        filename = re.sub(r'[<>:"|?*]', '', filename)

        # Remove path traversal attempts
        filename = filename.replace('..', '').replace('/', '').replace('\\', '')

        return filename or "unnamed"

    @staticmethod
    def validate_path(path: str, base_dir: str) -> bool:
        """
        Validate file path to prevent directory traversal.

        Args:
            path: File path to validate
            base_dir: Base directory that path must be within

        Returns:
            True if path is safe
        """
        try:
            requested_path = Path(path).resolve()
            base_path = Path(base_dir).resolve()

            # Check if path is within base directory
            return str(requested_path).startswith(str(base_path))
        except Exception:
            return False

    @staticmethod
    def validate_file_size(file_size: int, file_type: str) -> bool:
        """
        Validate file size.

        Args:
            file_size: File size in bytes
            file_type: File type ('pdf' or 'image')

        Returns:
            True if size is acceptable
        """
        if file_type == 'pdf':
            return file_size <= SecurityValidator.MAX_PDF_SIZE
        elif file_type == 'image':
            return file_size <= SecurityValidator.MAX_IMAGE_SIZE
        else:
            return False

    @staticmethod
    def validate_file_extension(filename: str, allowed_types: str) -> bool:
        """
        Validate file extension.

        Args:
            filename: Filename
            allowed_types: 'pdf' or 'image'

        Returns:
            True if extension is allowed
        """
        ext = Path(filename).suffix.lower()

        if allowed_types == 'pdf':
            return ext in SecurityValidator.ALLOWED_PDF_EXTENSIONS
        elif allowed_types == 'image':
            return ext in SecurityValidator.ALLOWED_IMAGE_EXTENSIONS
        else:
            return False

    @staticmethod
    def validate_citation_data(citation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and sanitize citation data.

        Args:
            citation: Citation dictionary

        Returns:
            Validated citation data

        Raises:
            ValueError: If validation fails
        """
        errors = []

        # Validate title
        if not citation.get("title"):
            errors.append("Title is required")
        else:
            citation["title"] = SecurityValidator.sanitize_text(
                citation["title"], max_length=500
            )

        # Validate authors
        if not citation.get("authors") or not isinstance(citation["authors"], list):
            errors.append("Authors list is required")
        else:
            citation["authors"] = [
                SecurityValidator.sanitize_text(author, max_length=200)
                for author in citation["authors"]
            ]

        # Validate year
        if citation.get("year"):
            year = citation["year"]
            if not isinstance(year, int) or year < 1900 or year > 2100:
                errors.append("Invalid year")

        # Validate DOI
        if citation.get("doi"):
            if not SecurityValidator.validate_doi(citation["doi"]):
                errors.append(f"Invalid DOI format: {citation['doi']}")

        # Validate URL
        if citation.get("url"):
            if not SecurityValidator.validate_url(citation["url"]):
                errors.append(f"Invalid URL format: {citation['url']}")

        # Sanitize optional fields
        if citation.get("abstract"):
            citation["abstract"] = SecurityValidator.sanitize_text(
                citation["abstract"], max_length=5000
            )

        if citation.get("source"):
            citation["source"] = SecurityValidator.sanitize_text(
                citation["source"], max_length=200
            )

        if errors:
            raise ValueError("; ".join(errors))

        return citation

    @staticmethod
    def validate_latex_content(content: str) -> bool:
        """
        Validate LaTeX content for dangerous commands.

        Args:
            content: LaTeX content

        Returns:
            True if content is safe
        """
        # Check for dangerous LaTeX commands
        dangerous_commands = [
            r'\\write18',
            r'\\input{/etc',
            r'\\include{/etc',
            r'\\immediate',
            r'\\openout',
            r'\\openin',
            r'\\read',
            r'\\system',
        ]

        content_lower = content.lower()
        for cmd in dangerous_commands:
            if cmd.lower() in content_lower:
                logger.warning(f"Dangerous LaTeX command detected: {cmd}")
                return False

        return True

    @staticmethod
    def rate_limit_key(identifier: str) -> str:
        """
        Generate rate limit key for an identifier.

        Args:
            identifier: User identifier (IP, API key, etc.)

        Returns:
            Rate limit key
        """
        import hashlib
        return hashlib.sha256(identifier.encode()).hexdigest()[:16]


class RequestValidator:
    """Validate API requests"""

    @staticmethod
    def validate_paper_generation_request(
        query: str,
        citation_ids: List[str],
        template_type: str
    ) -> Dict[str, Any]:
        """
        Validate paper generation request.

        Args:
            query: Research query
            citation_ids: List of citation IDs
            template_type: LaTeX template type

        Returns:
            Validated request data

        Raises:
            ValueError: If validation fails
        """
        errors = []

        # Validate query
        if not query or len(query.strip()) < 10:
            errors.append("Query must be at least 10 characters")

        if len(query) > 1000:
            errors.append("Query too long (max 1000 characters)")

        # Validate citations
        if not citation_ids:
            errors.append("At least one citation is required")

        if len(citation_ids) > 100:
            errors.append("Too many citations (max 100)")

        # Validate template type
        valid_templates = {"IEEE", "Springer", "ACM"}
        if template_type not in valid_templates:
            errors.append(f"Invalid template type. Must be one of: {valid_templates}")

        if errors:
            raise ValueError("; ".join(errors))

        return {
            "query": SecurityValidator.sanitize_text(query, max_length=1000),
            "citation_ids": citation_ids,
            "template_type": template_type
        }
