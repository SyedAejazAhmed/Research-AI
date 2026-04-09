"""
image_cataloger.py

Catalog image artifacts in a repository and persist descriptive metadata.

Goal:
- Keep images for later paper drafting phases.
- Store a practical description for each image (e.g., training curve,
  confusion matrix, ROC curve) inferred from filename and nearby code hints.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
from pathlib import Path
from typing import Dict, List, Sequence

logger = logging.getLogger(__name__)


class ImageCataloger:
    """Discovers repository images and stores them with descriptions."""

    IMAGE_EXTENSIONS = {
        ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".webp", ".tif", ".tiff"
    }

    EXCLUDED_DIRS = {
        ".git", "node_modules", "venv", ".venv", "env", ".env",
        "__pycache__", "build", "dist", ".tox", ".mypy_cache",
        ".pytest_cache", ".ruff_cache", ".idea", ".vscode", ".vs",
        "coverage", "htmlcov", ".next", ".nuxt", ".cache",
    }

    GENERATED_DIR_HINTS = {
        "output", "outputs", "result", "results", "plot", "plots", "figure", "figures",
        "eval", "evaluation", "artifact", "artifacts", "runs", "experiments", "reports",
    }

    GENERATED_NAME_HINTS = {
        "plot", "curve", "graph", "chart", "figure", "training", "validation", "loss",
        "accuracy", "confusion", "matrix", "roc", "auc", "pr", "precision", "recall",
        "benchmark", "ablation", "metric", "metrics", "heatmap", "hist", "scatter",
        "tsne", "umap", "attention", "saliency",
    }

    SAVE_CALL_PATTERNS = [
        re.compile(r"savefig\s*\(", re.IGNORECASE),
        re.compile(r"imwrite\s*\(", re.IGNORECASE),
        re.compile(r"write_image\s*\(", re.IGNORECASE),
        re.compile(r"save_image\s*\(", re.IGNORECASE),
        re.compile(r"export\s*\(", re.IGNORECASE),
    ]

    IMAGE_NAME_PATTERN = re.compile(
        r"([\w./\\-]+\.(?:png|jpg|jpeg|gif|bmp|svg|webp|tif|tiff))",
        re.IGNORECASE,
    )

    def catalog_images(
        self,
        repo_path: Path,
        source_files: Sequence[Path],
        output_images_dir: Path,
    ) -> List[Dict[str, object]]:
        """Discover and copy image artifacts, then write metadata manifests.

        Args:
            repo_path: Root of the cloned repository.
            source_files: Candidate text/code files used for hint extraction.
            output_images_dir: Destination folder (typically ``.../images``).

        Returns:
            List of image metadata dictionaries.
        """
        output_images_dir.mkdir(parents=True, exist_ok=True)
        image_files = self._discover_images(repo_path)

        if not image_files:
            self._write_manifest([], output_images_dir)
            logger.info("Image catalog: no images found.")
            return []

        source_hints = self._index_source_hints(source_files, repo_path)
        assets_dir = output_images_dir / "assets"

        entries: List[Dict[str, object]] = []
        for image_path in image_files:
            relative = image_path.relative_to(repo_path)
            rel_key_name = relative.name.lower()
            rel_key_stem = image_path.stem.lower()

            hints = source_hints.get(rel_key_name, []) + source_hints.get(rel_key_stem, [])
            hint_text = "\n".join(hints[:4])

            description = self._describe_image(relative, hint_text)
            likely_generated = self._is_likely_generated(relative, hint_text)

            dest = assets_dir / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(image_path, dest)

            stored_relative = (Path("images") / "assets" / relative).as_posix()
            entries.append(
                {
                    "relative_path": relative.as_posix(),
                    "stored_path": stored_relative,
                    "description": description,
                    "likely_generated": likely_generated,
                    "evidence": hints[:3],
                }
            )

        self._write_manifest(entries, output_images_dir)
        logger.info("Image catalog: %d image(s) indexed.", len(entries))
        return entries

    def _discover_images(self, repo_path: Path) -> List[Path]:
        images: List[Path] = []
        for path in sorted(repo_path.rglob("*")):
            if not path.is_file():
                continue
            rel_parts = {p.lower() for p in path.relative_to(repo_path).parts[:-1]}
            if rel_parts & self.EXCLUDED_DIRS:
                continue
            if path.suffix.lower() in self.IMAGE_EXTENSIONS:
                images.append(path)
        return images

    def _index_source_hints(
        self,
        source_files: Sequence[Path],
        repo_path: Path,
    ) -> Dict[str, List[str]]:
        """Build an index: image filename/stem -> nearby code hints."""
        index: Dict[str, List[str]] = {}
        for file_path in source_files:
            if not file_path.exists() or not file_path.is_file():
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            lines = content.splitlines()
            rel = file_path.relative_to(repo_path).as_posix()
            for i, line in enumerate(lines):
                lower_line = line.lower()
                has_image_name = bool(self.IMAGE_NAME_PATTERN.search(lower_line))
                has_save_call = any(p.search(lower_line) for p in self.SAVE_CALL_PATTERNS)
                if not has_image_name and not has_save_call:
                    continue

                context = self._context_window(lines, i)
                hint = f"{rel}:{i + 1}: {context.strip()}"

                matches = self.IMAGE_NAME_PATTERN.findall(lower_line)
                for match in matches:
                    name = Path(match).name.lower()
                    stem = Path(match).stem.lower()
                    index.setdefault(name, []).append(hint)
                    index.setdefault(stem, []).append(hint)

        return index

    @staticmethod
    def _context_window(lines: List[str], idx: int, radius: int = 1) -> str:
        start = max(0, idx - radius)
        end = min(len(lines), idx + radius + 1)
        return " ".join(line.strip() for line in lines[start:end] if line.strip())

    def _is_likely_generated(self, relative_path: Path, hint_text: str) -> bool:
        parts = {p.lower() for p in relative_path.parts}
        filename_tokens = self._tokens(relative_path.stem)
        if parts & self.GENERATED_DIR_HINTS:
            return True
        if filename_tokens & self.GENERATED_NAME_HINTS:
            return True
        if "savefig" in hint_text.lower() or "imwrite" in hint_text.lower():
            return True
        return False

    def _describe_image(self, relative_path: Path, hint_text: str) -> str:
        tokens = self._tokens(relative_path.stem)
        hint_lower = hint_text.lower()

        if {"loss", "accuracy"}.issubset(tokens) or ("loss" in tokens and "acc" in tokens):
            return "Training and validation learning-curve plot (loss/accuracy over epochs)."
        if "confusion" in tokens and "matrix" in tokens:
            return "Confusion matrix evaluation plot summarizing class-level prediction outcomes."
        if "roc" in tokens or "auc" in tokens:
            return "ROC/AUC evaluation curve used to assess classifier discrimination performance."
        if "precision" in tokens or "recall" in tokens or tokens == {"pr"}:
            return "Precision-Recall evaluation curve showing performance across decision thresholds."
        if "ablation" in tokens:
            return "Ablation-study figure comparing performance across model variants or settings."
        if "architecture" in tokens or "pipeline" in tokens:
            return "System architecture/pipeline diagram describing model or workflow components."
        if "heatmap" in tokens or "attention" in tokens:
            return "Heatmap-style visualization highlighting feature importance or attention patterns."
        if "tsne" in tokens or "umap" in tokens:
            return "Low-dimensional embedding projection used to visualize representation clusters."

        if "savefig" in hint_lower or "imwrite" in hint_lower:
            if "train" in hint_lower or "epoch" in hint_lower:
                return "Code-generated training/evaluation plot saved from experiment workflow."
            if "benchmark" in hint_lower or "metric" in hint_lower:
                return "Code-generated benchmark metrics figure saved during evaluation."
            return "Code-generated evaluation figure saved by plotting/image export routines."

        if tokens & self.GENERATED_NAME_HINTS:
            return "Likely evaluation or experimental figure inferred from filename semantics."

        return (
            "Repository image asset; exact semantic role is not explicit, but it may be reusable "
            "as supporting figure material in the paper drafting phase."
        )

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return {t for t in re.split(r"[^a-z0-9]+", text.lower()) if t}

    def _write_manifest(self, entries: List[Dict[str, object]], output_images_dir: Path) -> None:
        json_path = output_images_dir / "image_manifest.json"
        md_path = output_images_dir / "image_manifest.md"

        json_path.write_text(json.dumps(entries, indent=2), encoding="utf-8")

        if not entries:
            md_path.write_text(
                "# Image Manifest\n\nNo image artifacts were discovered in this repository.\n",
                encoding="utf-8",
            )
            return

        lines = [
            "# Image Manifest",
            "",
            "| Image | Stored Path | Likely Generated | Description |",
            "|---|---|---|---|",
        ]
        for entry in entries:
            image = str(entry.get("relative_path", "")).replace("|", "\\|")
            stored = str(entry.get("stored_path", "")).replace("|", "\\|")
            generated = "Yes" if entry.get("likely_generated") else "No"
            description = str(entry.get("description", "")).replace("|", "\\|")
            lines.append(f"| {image} | {stored} | {generated} | {description} |")

        lines.append("")
        lines.append("## Evidence Snippets")
        lines.append("")
        for entry in entries:
            evidence = entry.get("evidence", []) or []
            if not evidence:
                continue
            lines.append(f"- **{entry.get('relative_path', '')}**")
            for ev in evidence:
                lines.append(f"  - {ev}")

        md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
