"""
file_filter.py

Filters repository files based on extension inclusion/exclusion policies,
size limits, and directory exclusion rules.
"""

import logging
from pathlib import Path
from typing import FrozenSet, List

logger = logging.getLogger(__name__)


class FileFilter:
    """Applies inclusion/exclusion rules to select meaningful repository files."""

    EXCLUDED_DIRS: FrozenSet[str] = frozenset({
        ".git", "node_modules", "venv", ".venv", "env", ".env",
        "__pycache__", "build", "dist", ".tox",
        ".mypy_cache", ".pytest_cache", ".ruff_cache",
        ".eggs", ".idea", ".vscode", ".vs",
        "vendor", "third_party", "site-packages",
        ".next", ".nuxt", ".output", ".cache",
        "coverage", ".coverage", "htmlcov",
    })

    INCLUDED_EXTENSIONS: FrozenSet[str] = frozenset({
        ".py", ".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs",
        ".ipynb",
        ".md", ".rst", ".txt",
        ".json", ".yaml", ".yml", ".toml", ".cfg", ".ini",
        ".html", ".css", ".scss", ".less",
        ".sql",
        ".sh", ".bash", ".bat", ".ps1",
        ".r", ".R",
        ".go", ".java", ".c", ".cpp", ".h", ".hpp", ".cs",
        ".rs", ".rb", ".php", ".swift", ".kt", ".kts",
        ".lua", ".ex", ".exs", ".erl", ".hs",
        ".tf", ".hcl",
        ".xml", ".proto",
    })

    INCLUDED_FILENAMES: FrozenSet[str] = frozenset({
        "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
        "Makefile", "CMakeLists.txt",
        ".gitignore", ".dockerignore", ".editorconfig",
        "Procfile", "Pipfile", "Gemfile", "Cargo.toml",
        "requirements.txt", "requirements-dev.txt",
        "package.json", "package-lock.json",
        "setup.py", "setup.cfg", "pyproject.toml",
        "go.mod", "go.sum",
        "tsconfig.json", "jest.config.js", "webpack.config.js",
        "babel.config.js", ".babelrc",
        "LICENSE", "CHANGELOG.md", "CONTRIBUTING.md",
    })

    BINARY_EXTENSIONS: FrozenSet[str] = frozenset({
        ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg", ".webp",
        ".mp3", ".mp4", ".avi", ".mov", ".wav", ".flac",
        ".zip", ".tar", ".gz", ".bz2", ".rar", ".7z", ".xz",
        ".exe", ".dll", ".so", ".dylib", ".o", ".a",
        ".pyc", ".pyo", ".class", ".jar", ".war",
        ".woff", ".woff2", ".ttf", ".eot",
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        ".db", ".sqlite", ".sqlite3",
        ".lock",
    })

    MAX_FILE_SIZE_BYTES: int = 1_048_576  # 1 MB

    CRITICAL_FILENAMES: FrozenSet[str] = frozenset({
        "requirements.txt", "package.json", "pyproject.toml",
        "Cargo.toml", "go.mod", "Gemfile", "Pipfile",
        "docker-compose.yml", "docker-compose.yaml",
        "Dockerfile", "Makefile",
    })

    def __init__(self) -> None:
        """Initialise the filter (stateless)."""
        pass

    # ------------------------------------------------------------------
    # Predicate helpers
    # ------------------------------------------------------------------

    def is_excluded_dir(self, name: str) -> bool:
        """Return *True* if a directory name should be excluded."""
        return name in self.EXCLUDED_DIRS

    def is_included_file(self, file_path: Path) -> bool:
        """Return *True* if a file matches inclusion criteria."""
        if file_path.name in self.INCLUDED_FILENAMES:
            return True
        if file_path.suffix.lower() in self.INCLUDED_EXTENSIONS:
            return True
        return False

    def is_binary_file(self, file_path: Path) -> bool:
        """Return *True* if a file has a known binary extension."""
        if file_path.suffix.lower() in self.BINARY_EXTENSIONS:
            return True
        # Minified bundles
        name_lower = file_path.name.lower()
        if name_lower.endswith(".min.js") or name_lower.endswith(".min.css"):
            return True
        return False

    @staticmethod
    def file_size(file_path: Path) -> int:
        """Return file size in bytes, or 0 on error."""
        try:
            return file_path.stat().st_size
        except OSError:
            return 0

    # ------------------------------------------------------------------
    # Main filtering
    # ------------------------------------------------------------------

    def filter_files(self, repo_path: Path) -> List[Path]:
        """Walk the repository and return a sorted list of relevant files.

        Args:
            repo_path: Root path of the cloned repository.

        Returns:
            List of *Path* objects for files that passed all filters.
        """
        relevant: List[Path] = []
        skipped: int = 0
        oversized: int = 0

        for file_path in sorted(repo_path.rglob("*")):
            if not file_path.is_file():
                continue

            relative = file_path.relative_to(repo_path)

            # --- excluded directories ---
            if any(part in self.EXCLUDED_DIRS for part in relative.parts[:-1]):
                skipped += 1
                continue

            # --- binary / minified ---
            if self.is_binary_file(file_path):
                skipped += 1
                continue

            # --- inclusion check ---
            if not self.is_included_file(file_path):
                skipped += 1
                continue

            # --- size gate ---
            size = self.file_size(file_path)
            if size > self.MAX_FILE_SIZE_BYTES:
                if file_path.name in self.CRITICAL_FILENAMES:
                    logger.warning(
                        "Including oversized critical file: %s (%d bytes)",
                        relative, size,
                    )
                else:
                    oversized += 1
                    logger.warning(
                        "Skipping oversized file: %s (%d bytes)", relative, size
                    )
                    continue

            relevant.append(file_path)

        logger.info(
            "File filter result — included: %d, skipped: %d, oversized: %d",
            len(relevant), skipped, oversized,
        )
        return relevant
