"""
main.py

CLI entry-point and orchestrator for the GitHub Repository Intelligence Agent.

Usage:
    python main.py --repo <github_url> [--title "optional title"] [--output ./outputs/GitHub]

Environment:
    GEMINI_API_KEY  — Google AI / Gemini API key (can also be passed via --api-key).
"""

import argparse
import logging
import os
import sys
from pathlib import Path

from repo_handler import RepoHandler, RepoHandlerError
from file_filter import FileFilter
from structure_generator import StructureGenerator
from summarizer import Summarizer
from title_generator import TitleGenerator

# ======================================================================
# Logging configuration
# ======================================================================

LOG_FORMAT = "%(asctime)s [%(levelname)-7s] %(name)s: %(message)s"
LOG_DATE_FMT = "%Y-%m-%d %H:%M:%S"


def _setup_logging() -> None:
    """Configure structured logging to stderr."""
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FMT,
        stream=sys.stderr,
    )


logger = logging.getLogger(__name__)


# ======================================================================
# CLI argument parsing
# ======================================================================

def parse_args() -> argparse.Namespace:
    """Parse and return command-line arguments.

    Returns:
        Parsed argument namespace.
    """
    parser = argparse.ArgumentParser(
        description="GitHub Repository Intelligence Agent — "
                    "generates structured summary, title, and directory tree "
                    "from a public GitHub repository.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--repo",
        required=True,
        type=str,
        help="HTTPS URL of a public GitHub repository.",
    )
    parser.add_argument(
        "--title",
        required=False,
        type=str,
        default=None,
        help="Optional research paper title to refine.",
    )
    parser.add_argument(
        "--output",
        required=False,
        type=str,
        default=None,
        help="Output directory path (default: ./outputs/GitHub).",
    )
    parser.add_argument(
        "--api-key",
        required=False,
        type=str,
        default=None,
        help="Gemini API key (overrides GEMINI_API_KEY env var).",
    )
    parser.add_argument(
        "--model",
        required=False,
        type=str,
        default="gemini-2.0-flash",
        help="Gemini model name (default: gemini-2.0-flash).",
    )
    return parser.parse_args()


# ======================================================================
# API key resolution
# ======================================================================

def resolve_api_key(cli_key: str | None) -> str:
    """Resolve the Gemini API key from CLI flag or environment.

    Args:
        cli_key: Value passed via ``--api-key``, or *None*.

    Returns:
        API key string.

    Raises:
        SystemExit: If no key can be found.
    """
    key = cli_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        logger.error(
            "No API key provided. Pass --api-key or set the "
            "GEMINI_API_KEY environment variable."
        )
        sys.exit(1)
    return key


# ======================================================================
# Output directory helpers
# ======================================================================

def ensure_output_dirs(base: Path) -> None:
    """Create the required output directory structure.

    Args:
        base: Root output directory (e.g. ``./GitHub``).
    """
    for sub in ("images", "project structure", "summary", "title"):
        (base / sub).mkdir(parents=True, exist_ok=True)
    logger.info("Output directory structure verified: %s", base.resolve())


# ======================================================================
# Pipeline
# ======================================================================

def run_pipeline(args: argparse.Namespace) -> None:
    """Execute the full intelligence pipeline.

    Steps:
        1. Clone repository
        2. Generate directory tree
        3. Filter relevant files
        4. Summarise (direct or hierarchical)
        5. Generate / improve title
        6. Persist all outputs

    Args:
        args: Parsed CLI arguments.
    """
    api_key = resolve_api_key(args.api_key)
    output_dir = Path(args.output) if args.output else Path("./outputs/GitHub")
    ensure_output_dirs(output_dir)

    # Instantiate modules
    repo_handler = RepoHandler()
    file_filter = FileFilter()
    structure_gen = StructureGenerator()
    summarizer = Summarizer(api_key=api_key, model_name=args.model)
    title_gen = TitleGenerator(api_key=api_key, model_name=args.model)

    try:
        # ── Step 1: Clone ──────────────────────────────────────────
        _banner("STEP 1 — Cloning repository")
        repo_path, repo_name = repo_handler.clone(args.repo)

        # ── Step 2: Directory tree ─────────────────────────────────
        _banner("STEP 2 — Generating directory tree")
        tree = structure_gen.generate_tree(repo_path, repo_name)
        structure_out = output_dir / "project structure" / "structure.txt"
        structure_gen.save_tree(tree, structure_out)

        # ── Step 3: File filtering ─────────────────────────────────
        _banner("STEP 3 — Filtering relevant files")
        relevant_files = file_filter.filter_files(repo_path)

        if not relevant_files:
            logger.warning("No relevant source files found — generating minimal outputs.")
            summary_text = Summarizer.fallback_summary(repo_name)
            title_text = TitleGenerator._fallback_title(repo_name)
        else:
            # ── Step 4: Summarise ──────────────────────────────────
            _banner("STEP 4 — Generating file / module summaries")
            file_summaries = summarizer.summarize_files_batch(relevant_files, repo_path)

            _banner("STEP 4b — Generating structured summary")
            summary_text = summarizer.generate_summary(file_summaries, repo_name, tree)

            # ── Step 5: Title ──────────────────────────────────────
            _banner("STEP 5 — Generating title")
            title_text = title_gen.generate_title(
                summary_text, repo_name, existing_title=args.title
            )

        # ── Step 6: Write outputs ──────────────────────────────────
        _banner("STEP 6 — Saving outputs")

        summary_out = output_dir / "summary" / "summary.md"
        Summarizer.save_summary(summary_text, summary_out)

        title_out = output_dir / "title" / "title.txt"
        TitleGenerator.save_title(title_text, title_out)

        # ── Done ───────────────────────────────────────────────────
        _banner("PIPELINE COMPLETE")
        logger.info("Output directory : %s", output_dir.resolve())
        logger.info("  ├── project structure/structure.txt")
        logger.info("  ├── summary/summary.md")
        logger.info("  ├── title/title.txt")
        logger.info("  └── images/   (reserved)")

    except RepoHandlerError as exc:
        logger.error("Repository error: %s", exc)
        sys.exit(1)
    except KeyboardInterrupt:
        logger.warning("Interrupted by user.")
        sys.exit(130)
    except Exception as exc:
        logger.error("Unexpected error: %s", exc, exc_info=True)
        sys.exit(1)
    finally:
        repo_handler.cleanup()


def _banner(text: str) -> None:
    """Log a section banner for readability."""
    logger.info("=" * 64)
    logger.info(text)
    logger.info("=" * 64)


# ======================================================================
# Entry-point
# ======================================================================

def main() -> None:
    """Script entry-point."""
    _setup_logging()
    args = parse_args()
    run_pipeline(args)


if __name__ == "__main__":
    main()
