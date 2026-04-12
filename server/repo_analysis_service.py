"""
Repository analysis service used by API endpoints.

This module bridges FastAPI routes with the repo_analyzer pipeline so both
GitHub URLs and local folders follow the same structure-first analysis flow.
"""

from __future__ import annotations

import logging
import os
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from repo_analyzer.file_filter import FileFilter
from repo_analyzer.image_cataloger import ImageCataloger
from repo_analyzer.repo_handler import RepoHandler, RepoHandlerError
from repo_analyzer.structure_generator import StructureGenerator

logger = logging.getLogger(__name__)


class RepoAnalysisError(Exception):
    """Raised when repository analysis cannot be completed."""


OPTIMISTIC_ALGORITHM = {
    "name": "Optimistic Budgeted Repository Analysis",
    "description": (
        "Single shared analyzer for both GitHub URL and folder inputs. "
        "Uses optimistic fetch, structure-first traversal, budgeted file ranking, "
        "and notebook-aware image-path extraction."
    ),
    "time_complexity": "O(n + r log r)",
    "space_complexity": "O(r + i)",
    "symbols": {
        "n": "all files visited during traversal",
        "r": "relevant files before cap",
        "i": "image/image-reference manifest entries",
    },
}


def _ensure_output_dirs(base: Path) -> None:
    for sub in ("images", "project structure", "summary", "title"):
        (base / sub).mkdir(parents=True, exist_ok=True)


def _safe_slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", value or "")
    cleaned = cleaned.strip("._-")
    return cleaned or "repository"


def _resolve_api_key() -> str:
    return os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")


def _fallback_summary(repo_name: str, tree: str, relevant_files: List[Path], image_count: int) -> str:
    ext_counts: Dict[str, int] = {}
    for f in relevant_files:
        ext = f.suffix.lower() or "<none>"
        ext_counts[ext] = ext_counts.get(ext, 0) + 1

    top_ext_lines = []
    for ext, count in sorted(ext_counts.items(), key=lambda x: x[1], reverse=True)[:12]:
        top_ext_lines.append(f"- `{ext}`: {count} file(s)")

    tree_lines = tree.splitlines()
    tree_preview = "\n".join(tree_lines[:140])
    if len(tree_lines) > 140:
        tree_preview += "\n... [truncated]"

    summary_parts = [
        f"# Project Overview\nRepository `{repo_name}` was analyzed with a structure-first pass.",
        "# Problem Statement\nNot explicitly defined in repository.",
        "# Objectives\nNot explicitly defined in repository.",
        "# System Architecture\nThe architecture was inferred from repository structure and filtered source files.",
        "# Core Components\nNot explicitly defined in repository.",
        "# Technologies Used\n" + ("\n".join(top_ext_lines) if top_ext_lines else "Not explicitly defined in repository."),
        "# Data Flow / Execution Flow\nNot explicitly defined in repository.",
        "# Key Algorithms / Models\nNot explicitly defined in repository.",
        "# Configuration & Dependencies\nInspect key manifest/config files in the repository root for dependency detail.",
        "# Deployment / Running Instructions\nNot explicitly defined in repository.",
        "# Limitations\nThis summary was generated without Gemini API access, so it is conservative.",
        "# Future Scope\nAdd GEMINI_API_KEY to enable richer semantic summarization and title refinement.",
        f"\n## Analysis Stats\n- Relevant files: {len(relevant_files)}\n- Cataloged images: {image_count}\n\n## Structure Preview\n```\n{tree_preview}\n```",
    ]
    return "\n\n".join(summary_parts)


def _fallback_title(repo_name: str, existing_title: Optional[str]) -> str:
    if existing_title and existing_title.strip():
        return existing_title.strip()
    clean = repo_name.replace("-", " ").replace("_", " ").strip().title()
    return f"Technical Structure and Implementation Analysis of {clean}"


def _generate_summary_and_title(
    repo_path: Path,
    repo_name: str,
    tree: str,
    relevant_files: List[Path],
    image_entries: List[Dict[str, Any]],
    existing_title: Optional[str],
) -> Dict[str, Any]:
    api_key = _resolve_api_key()
    if api_key:
        try:
            from repo_analyzer.summarizer import Summarizer
            from repo_analyzer.title_generator import TitleGenerator

            summarizer = Summarizer(api_key=api_key)
            title_generator = TitleGenerator(api_key=api_key)

            if relevant_files:
                file_summaries = summarizer.summarize_files_batch(relevant_files, repo_path)
            else:
                file_summaries = []

            summary = summarizer.generate_summary(
                file_summaries=file_summaries,
                repo_name=repo_name,
                tree=tree,
                image_entries=image_entries,
            )
            title = title_generator.generate_title(
                summary=summary,
                repo_name=repo_name,
                existing_title=existing_title,
            )
            return {
                "summary": summary,
                "title": title,
                "engine": "gemini",
            }
        except Exception as exc:
            logger.warning("Gemini summarization failed, using fallback summary: %s", exc)

    return {
        "summary": _fallback_summary(repo_name, tree, relevant_files, len(image_entries)),
        "title": _fallback_title(repo_name, existing_title),
        "engine": "fallback",
    }


def analyze_repo_path(
    repo_path: Path,
    output_dir: Path,
    existing_title: Optional[str] = None,
    source_type: str = "local_folder",
    source_value: Optional[str] = None,
) -> Dict[str, Any]:
    """Analyze a local repository path and persist structure/summary/title outputs."""
    repo_path = repo_path.resolve()
    if not repo_path.exists() or not repo_path.is_dir():
        raise RepoAnalysisError(f"Repository path not found: {repo_path}")

    repo_name = repo_path.name or "repository"
    run_id = uuid.uuid4().hex[:8]

    output_root = output_dir if output_dir.is_absolute() else (Path.cwd() / output_dir)
    run_output_dir = output_root.resolve() / f"{_safe_slug(repo_name)}_{run_id}"
    _ensure_output_dirs(run_output_dir)

    structure_generator = StructureGenerator()
    file_filter = FileFilter()
    image_cataloger = ImageCataloger()

    tree = structure_generator.generate_tree(repo_path, repo_name)
    structure_path = run_output_dir / "project structure" / "structure.txt"
    structure_generator.save_tree(tree, structure_path)

    relevant_files = file_filter.filter_files(repo_path)
    image_entries = image_cataloger.catalog_images(
        repo_path=repo_path,
        source_files=relevant_files,
        output_images_dir=run_output_dir / "images",
    )

    generated = _generate_summary_and_title(
        repo_path=repo_path,
        repo_name=repo_name,
        tree=tree,
        relevant_files=relevant_files,
        image_entries=image_entries,
        existing_title=existing_title,
    )

    summary_text = generated["summary"]
    title_text = generated["title"]

    summary_path = run_output_dir / "summary" / "summary.md"
    summary_path.write_text(summary_text, encoding="utf-8")

    title_path = run_output_dir / "title" / "title.txt"
    title_path.write_text(title_text, encoding="utf-8")

    top_files = []
    for file_path in relevant_files[:200]:
        try:
            top_files.append(file_path.relative_to(repo_path).as_posix())
        except Exception:
            top_files.append(file_path.name)

    notebook_image_refs = sum(1 for e in image_entries if e.get("source") == "notebook_reference")
    repo_image_files = sum(1 for e in image_entries if e.get("source") == "repository_file")

    return {
        "repository_name": repo_name,
        "title": title_text,
        "summary": summary_text,
        "tree": tree,
        "source_type": source_type,
        "source_value": source_value or str(repo_path),
        "next_pipeline_order": [
            "repo_analysis",
            "reference_curation",
            "section_synthesis",
            "writing_verification_publication",
        ],
        "summary_engine": generated["engine"],
        "algorithm": {
            **OPTIMISTIC_ALGORITHM,
            "limits": {
                "max_selected_files": getattr(file_filter, "MAX_SELECTED_FILES", None),
                "max_file_size_bytes": getattr(file_filter, "MAX_FILE_SIZE_BYTES", None),
            },
        },
        "statistics": {
            "relevant_files": len(relevant_files),
            "image_artifacts": len(image_entries),
            "repository_image_files": repo_image_files,
            "notebook_image_references": notebook_image_refs,
            "tree_entries": len(tree.splitlines()),
        },
        "top_files": top_files,
        "outputs": {
            "base_dir": str(run_output_dir),
            "structure": str(structure_path),
            "summary": str(summary_path),
            "title": str(title_path),
            "images_manifest": str(run_output_dir / "images" / "image_manifest.json"),
        },
    }


def analyze_github_repository(
    repo_url: str,
    output_dir: Path,
    existing_title: Optional[str] = None,
) -> Dict[str, Any]:
    """Clone and analyze a GitHub repository using the repo_analyzer pipeline."""
    handler = RepoHandler()
    try:
        repo_path, _repo_name = handler.clone(repo_url)
        return analyze_repo_path(
            repo_path=repo_path,
            output_dir=output_dir,
            existing_title=existing_title,
            source_type="github_url",
            source_value=repo_url,
        )
    except RepoHandlerError as exc:
        raise RepoAnalysisError(str(exc)) from exc
    except Exception as exc:
        raise RepoAnalysisError(str(exc)) from exc
    finally:
        handler.cleanup()


def analyze_local_repository(
    folder_path: str,
    output_dir: Path,
    existing_title: Optional[str] = None,
) -> Dict[str, Any]:
    """Analyze an existing local folder path using the shared repo_analyzer flow."""
    path = Path(folder_path).expanduser().resolve()
    return analyze_repo_path(
        repo_path=path,
        output_dir=output_dir,
        existing_title=existing_title,
        source_type="local_folder",
        source_value=str(path),
    )
