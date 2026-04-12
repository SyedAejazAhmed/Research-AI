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

    # Optimistic budget: keep highest-signal files when repositories are large.
    # Complexity: scan is O(n), ranking is O(r log r), memory is O(r), where
    # n = total files visited and r = relevant files before capping.
    MAX_SELECTED_FILES: int = 1_500

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
        ".lock", ".pth", ".pt", ".ckpt", ".onnx", ".h5", ".hdf5", ".bin",
    })

    MAX_FILE_SIZE_BYTES: int = 1_048_576  # 1 MB

    CRITICAL_FILENAMES: FrozenSet[str] = frozenset({
        "requirements.txt", "package.json", "pyproject.toml",
        "Cargo.toml", "go.mod", "Gemfile", "Pipfile",
        "docker-compose.yml", "docker-compose.yaml",
        "Dockerfile", "Makefile",
    })

    HIGH_SIGNAL_EXTENSIONS: FrozenSet[str] = frozenset({
        ".py", ".ipynb", ".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs",
        ".go", ".java", ".c", ".cpp", ".h", ".hpp", ".cs", ".rs", ".rb",
        ".php", ".swift", ".kt", ".kts", ".sql", ".sh", ".bash", ".ps1",
    })

    MEDIUM_SIGNAL_EXTENSIONS: FrozenSet[str] = frozenset({
        ".md", ".rst", ".txt", ".json", ".yaml", ".yml", ".toml", ".cfg",
        ".ini", ".xml", ".proto", ".tf", ".hcl", ".html", ".css", ".scss",
        ".less",
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

    def _optimistic_priority(self, relative_path: Path) -> int:
        """Score files by expected signal for repository reasoning."""
        score = 0
        name = relative_path.name
        name_lower = name.lower()
        suffix = relative_path.suffix.lower()

        if name in self.CRITICAL_FILENAMES:
            score += 140
        if name in self.INCLUDED_FILENAMES:
            score += 80
        if name_lower.startswith("readme"):
            score += 60

        if suffix in self.HIGH_SIGNAL_EXTENSIONS:
            score += 55
        elif suffix in self.MEDIUM_SIGNAL_EXTENSIONS:
            score += 30
        else:
            score += 8

        if any(part.lower() in {"src", "app", "core", "server", "backend", "frontend"} for part in relative_path.parts):
            score += 18
        if any(part.lower() in {"tests", "test"} for part in relative_path.parts):
            score += 10

        depth = len(relative_path.parts)
        score += max(0, 18 - min(depth, 18))
        return score

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

        if len(relevant) > self.MAX_SELECTED_FILES:
            relevant.sort(
                key=lambda p: (
                    -self._optimistic_priority(p.relative_to(repo_path)),
                    self.file_size(p),
                    p.relative_to(repo_path).as_posix(),
                )
            )
            dropped = len(relevant) - self.MAX_SELECTED_FILES
            relevant = relevant[: self.MAX_SELECTED_FILES]
            logger.info(
                "Optimistic cap applied — retained %d files, dropped %d lower-priority files.",
                len(relevant),
                dropped,
            )

        return relevant
