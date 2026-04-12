"""
repo_handler.py

Handles GitHub repository URL validation, cloning to a temporary directory,
and cleanup. Enforces HTTPS-only, public repository access.
"""

import logging
import json
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
import zipfile
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
    _PARTIAL_CLONE_TIMEOUT: int = 180
    _ARCHIVE_TIMEOUT: int = 180
    _CLASSIC_CLONE_TIMEOUT: int = 300

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

        git_partial_error: Optional[str] = None
        archive_error: Optional[str] = None

        try:
            # Optimistic first attempt: partial clone limits downloaded blob data.
            self._clone_with_git(clone_url, timeout=self._PARTIAL_CLONE_TIMEOUT, partial=True)
        except RepoHandlerError as exc:
            git_partial_error = str(exc)
            logger.info("Partial clone unavailable, trying archive fallback: %s", exc)

            try:
                self._download_archive(validated_url, repo_name, timeout=self._ARCHIVE_TIMEOUT)
            except RepoHandlerError as arch_exc:
                archive_error = str(arch_exc)
                logger.info("Archive fallback unavailable, trying classic shallow clone: %s", arch_exc)
                self._clone_with_git(clone_url, timeout=self._CLASSIC_CLONE_TIMEOUT, partial=False)

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

        if git_partial_error and archive_error:
            logger.info(
                "Repository fetched after fallbacks. partial_error=%s archive_error=%s",
                git_partial_error,
                archive_error,
            )

        logger.info(f"Clone successful — {file_count} file(s) found.")
        return self._repo_path, repo_name

    def _clone_with_git(self, clone_url: str, timeout: int, partial: bool) -> None:
        """Run a git clone command with fallback-aware options."""
        if not self._repo_path:
            raise RepoHandlerError("Internal clone state not initialized.")

        if self._repo_path.exists():
            shutil.rmtree(self._repo_path, ignore_errors=True)

        cmd = [
            "git",
            "clone",
            "--depth",
            "1",
            "--single-branch",
            "--no-tags",
            "--recurse-submodules=no",
        ]
        if partial:
            cmd.extend(["--filter=blob:none"])
        cmd.extend([clone_url, str(self._repo_path)])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except FileNotFoundError as exc:
            raise RepoHandlerError(
                "Git executable not found. Ensure git is installed and in PATH."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise RepoHandlerError(
                f"Clone timed out after {timeout} s. The repository may be too large "
                "or the network may be unreachable."
            ) from exc

        if result.returncode != 0:
            stderr = (result.stderr or "").strip() or (result.stdout or "").strip()
            raise RepoHandlerError(f"Git clone failed (exit {result.returncode}): {stderr}")

    def _download_archive(self, repo_url: str, repo_name: str, timeout: int) -> None:
        """Download and extract repository archive via codeload GitHub fallback."""
        if not self._temp_dir or not self._repo_path:
            raise RepoHandlerError("Internal clone state not initialized.")

        owner, repo = self._extract_owner_repo(repo_url)
        branches = self._candidate_branches(owner, repo)
        last_error: Optional[Exception] = None

        for branch in branches:
            archive_url = f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/{branch}"
            archive_file = self._temp_dir / f"{repo_name}_{branch}.zip"
            extract_dir = self._temp_dir / f"_extract_{branch}"
            try:
                # Ensure partial clone leftovers do not interfere with archive extraction.
                if self._repo_path.exists():
                    shutil.rmtree(self._repo_path, ignore_errors=True)
                if extract_dir.exists():
                    shutil.rmtree(extract_dir, ignore_errors=True)
                extract_dir.mkdir(parents=True, exist_ok=True)

                request = urllib.request.Request(
                    archive_url,
                    headers={"User-Agent": "Yukti-RepoAnalyzer"},
                )
                with urllib.request.urlopen(request, timeout=timeout) as response, archive_file.open("wb") as out:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        out.write(chunk)

                extracted_root = self._extract_archive(archive_file, extract_dir)
                shutil.move(str(extracted_root), str(self._repo_path))
                logger.info("Archive fallback succeeded for branch '%s'.", branch)
                return
            except Exception as exc:
                last_error = exc
                logger.warning("Archive fetch failed for branch '%s': %s", branch, exc)
            finally:
                if archive_file.exists():
                    archive_file.unlink(missing_ok=True)
                if extract_dir.exists():
                    shutil.rmtree(extract_dir, ignore_errors=True)

        raise RepoHandlerError(
            f"Archive download fallback failed. Last error: {last_error}"
        )

    def _candidate_branches(self, owner: str, repo: str) -> Tuple[str, ...]:
        """Fetch preferred branch candidates, defaulting to common branch names."""
        default_branch = ""
        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        try:
            request = urllib.request.Request(
                api_url,
                headers={"User-Agent": "Yukti-RepoAnalyzer"},
            )
            with urllib.request.urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8", errors="replace"))
                default_branch = str(payload.get("default_branch", "")).strip()
        except Exception as exc:
            logger.warning("Could not resolve default branch via GitHub API: %s", exc)

        ordered = []
        for branch in (default_branch, "main", "master"):
            if branch and branch not in ordered:
                ordered.append(branch)
        return tuple(ordered)

    def _extract_archive(self, archive_file: Path, extraction_root: Path) -> Path:
        """Extract a downloaded zip archive safely and return extracted root directory."""
        extraction_root = extraction_root.resolve()
        top_level_roots = set()

        with zipfile.ZipFile(archive_file, "r") as zf:
            members = zf.infolist()
            if not members:
                raise RepoHandlerError("Downloaded archive is empty.")

            for member in members:
                member_path = Path(member.filename)
                if member_path.is_absolute() or ".." in member_path.parts:
                    raise RepoHandlerError("Unsafe path detected inside archive.")

                if member_path.parts:
                    top_level_roots.add(member_path.parts[0])

                target = (extraction_root / member.filename).resolve()
                try:
                    target.relative_to(extraction_root)
                except ValueError as exc:
                    raise RepoHandlerError("Archive path escapes extraction directory.")
                except Exception as exc:
                    raise RepoHandlerError("Archive extraction path validation failed.") from exc

            zf.extractall(extraction_root)

        extracted_roots = [
            extraction_root / root_name
            for root_name in sorted(top_level_roots)
            if (extraction_root / root_name).is_dir()
        ]
        if not extracted_roots:
            raise RepoHandlerError("Archive extraction produced no directory.")

        if len(extracted_roots) > 1:
            logger.warning(
                "Archive contains multiple top-level directories; choosing '%s'.",
                extracted_roots[0].name,
            )

        return extracted_roots[0]

    @staticmethod
    def _extract_owner_repo(url: str) -> Tuple[str, str]:
        """Extract owner/repo from a validated GitHub repository URL."""
        parsed = urlparse(url)
        parts = parsed.path.strip("/").split("/")
        if len(parts) < 2:
            raise RepoHandlerError("URL must include owner and repository name.")
        return parts[0], parts[1]

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
