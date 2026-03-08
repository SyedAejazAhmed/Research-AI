"""
repo_handler.py

Handles GitHub repository URL validation, cloning to a temporary directory,
and cleanup. Enforces HTTPS-only, public repository access.
"""

import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class RepoHandlerError(Exception):
    """Raised when repository validation or cloning fails."""
    pass


class RepoHandler:
    """Validates GitHub URLs and clones repositories for static analysis."""

    _GITHUB_HOST: str = "github.com"

    def __init__(self) -> None:
        """Initialize RepoHandler with no active temp directory."""
        self._temp_dir: Optional[Path] = None
        self._repo_path: Optional[Path] = None

    # ------------------------------------------------------------------
    # URL validation
    # ------------------------------------------------------------------

    def validate_url(self, url: str) -> str:
        """Validate and normalise a GitHub repository URL.

        Args:
            url: Raw URL string provided by the user.

        Returns:
            Cleaned HTTPS URL without trailing slash or `.git` suffix.

        Raises:
            RepoHandlerError: If the URL is malformed or not a GitHub repo.
        """
        url = url.strip()
        if not url:
            raise RepoHandlerError("Repository URL must not be empty.")

        parsed = urlparse(url)

        if parsed.scheme != "https":
            raise RepoHandlerError(
                f"URL must use HTTPS scheme. Received: '{parsed.scheme or 'none'}'."
            )

        if parsed.hostname != self._GITHUB_HOST:
            raise RepoHandlerError(
                f"URL must point to {self._GITHUB_HOST}. "
                f"Received host: '{parsed.hostname}'."
            )

        clean_url = url.rstrip("/")
        if clean_url.endswith(".git"):
            clean_url = clean_url[:-4]

        path_parts = parsed.path.strip("/").split("/")
        if len(path_parts) < 2 or not path_parts[0] or not path_parts[1]:
            raise RepoHandlerError(
                "URL must include both owner and repository name "
                "(e.g. https://github.com/owner/repo)."
            )

        # Reject URLs that drill into sub-paths (tree, blob, etc.)
        # We only want the top-level repo URL
        if len(path_parts) > 2:
            logger.warning(
                "URL contains sub-path segments beyond owner/repo; "
                "they will be ignored."
            )
            clean_url = f"https://{self._GITHUB_HOST}/{path_parts[0]}/{path_parts[1]}"

        logger.info(f"Validated URL: {clean_url}")
        return clean_url

    @staticmethod
    def extract_repo_name(url: str) -> str:
        """Extract the repository name from a validated URL.

        Args:
            url: A validated (cleaned) GitHub URL.

        Returns:
            Repository name string.
        """
        return url.rstrip("/").split("/")[-1]

    # ------------------------------------------------------------------
    # Cloning
    # ------------------------------------------------------------------

    def clone(self, url: str) -> Tuple[Path, str]:
        """Clone a GitHub repository into a temporary directory.

        Performs a shallow clone (``--depth 1``) to minimise bandwidth.

        Args:
            url: GitHub repository URL (HTTPS).

        Returns:
            Tuple of (path to cloned repo, repository name).

        Raises:
            RepoHandlerError: On validation failure, clone failure, or timeout.
        """
        validated_url = self.validate_url(url)
        repo_name = self.extract_repo_name(validated_url)

        self._temp_dir = Path(tempfile.mkdtemp(prefix="gh_intel_"))
        self._repo_path = self._temp_dir / repo_name

        logger.info(f"Cloning repository '{repo_name}' …")
        logger.info(f"Temp directory: {self._temp_dir}")

        clone_url = validated_url + ".git"

        try:
            result = subprocess.run(
                ["git", "clone", "--depth", "1", clone_url, str(self._repo_path)],
                capture_output=True,
                text=True,
                timeout=300,
            )
        except FileNotFoundError:
            raise RepoHandlerError(
                "Git executable not found. Ensure git is installed and in PATH."
            )
        except subprocess.TimeoutExpired:
            raise RepoHandlerError(
                "Clone timed out after 300 s. The repository may be too large "
                "or the network may be unreachable."
            )

        if result.returncode != 0:
            stderr = result.stderr.strip()
            raise RepoHandlerError(f"Git clone failed (exit {result.returncode}): {stderr}")

        # Verify clone produced content
        if not self._repo_path.exists():
            raise RepoHandlerError("Clone directory was not created.")

        all_files = list(self._repo_path.rglob("*"))
        file_count = sum(1 for f in all_files if f.is_file())
        non_git = [
            c for c in self._repo_path.iterdir() if c.name != ".git"
        ]

        if not non_git:
            logger.warning(
                "Repository appears to be empty (no files outside .git)."
            )

        logger.info(f"Clone successful — {file_count} file(s) found.")
        return self._repo_path, repo_name

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def cleanup(self) -> None:
        """Remove the temporary directory created during cloning."""
        if self._temp_dir and self._temp_dir.exists():
            shutil.rmtree(self._temp_dir, ignore_errors=True)
            logger.info("Temporary clone directory cleaned up.")

    @property
    def repo_path(self) -> Optional[Path]:
        """Path to the cloned repository, or *None* if not yet cloned."""
        return self._repo_path
