"""
structure_generator.py

Generates a full directory tree representation for a cloned repository
and saves it to a text file.
"""

import logging
from pathlib import Path
from typing import FrozenSet, List

logger = logging.getLogger(__name__)


class StructureGenerator:
    """Builds and persists a visual directory tree."""

    EXCLUDED_DIRS: FrozenSet[str] = frozenset({
        ".git", "node_modules", "venv", ".venv", "env", ".env",
        "__pycache__", "build", "dist",
        ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache",
        ".eggs", ".idea", ".vscode", ".vs",
        "vendor", "site-packages",
        ".next", ".nuxt", ".output", ".cache",
        "coverage", ".coverage", "htmlcov",
    })

    EXCLUDED_EXTENSIONS: FrozenSet[str] = frozenset({
        ".pyc", ".pyo", ".class", ".o", ".a",
        ".exe", ".dll", ".so", ".dylib",
    })

    MAX_FILE_SIZE: int = 1_048_576  # 1 MB

    def __init__(self) -> None:
        """Initialise the generator (stateless)."""
        pass

    # ------------------------------------------------------------------
    # Tree construction
    # ------------------------------------------------------------------

    def generate_tree(self, repo_path: Path, repo_name: str) -> str:
        """Create a directory-tree string for the repository.

        Args:
            repo_path: Path to the cloned repository root.
            repo_name: Human-readable repository name (used as root label).

        Returns:
            Multi-line string representing the tree.
        """
        lines: List[str] = [f"{repo_name}/"]
        self._walk(repo_path, prefix="", lines=lines)
        tree = "\n".join(lines)
        logger.info("Directory tree generated — %d entries.", len(lines))
        return tree

    def _walk(self, directory: Path, prefix: str, lines: List[str]) -> None:
        """Recursively append entries for *directory* to *lines*.

        Args:
            directory: Current directory being walked.
            prefix: Connector prefix for indentation.
            lines: Accumulator list of formatted lines.
        """
        entries = sorted(
            directory.iterdir(),
            key=lambda e: (not e.is_dir(), e.name.lower()),
        )

        # Apply filters
        filtered: List[Path] = []
        for entry in entries:
            if entry.is_dir() and entry.name in self.EXCLUDED_DIRS:
                continue
            if entry.is_file():
                if entry.suffix.lower() in self.EXCLUDED_EXTENSIONS:
                    continue
                try:
                    size = entry.stat().st_size
                except OSError:
                    size = 0
                if size > self.MAX_FILE_SIZE:
                    if entry.suffix.lower() not in {
                        ".json", ".yaml", ".yml", ".xml", ".toml",
                    }:
                        continue
            filtered.append(entry)

        for idx, entry in enumerate(filtered):
            is_last = idx == len(filtered) - 1
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{entry.name}")

            if entry.is_dir():
                extension = "    " if is_last else "│   "
                self._walk(entry, prefix + extension, lines)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_tree(self, tree: str, output_path: Path) -> None:
        """Write the tree string to *output_path*.

        Args:
            tree: The formatted directory tree.
            output_path: Destination file path.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(tree, encoding="utf-8")
        logger.info("Directory tree saved to: %s", output_path)
