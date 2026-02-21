"""
summarizer.py

Reads relevant repository files and generates a structured Markdown
technical summary using the Gemini LLM, with hierarchical summarisation
for large repositories.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

import google.generativeai as genai

logger = logging.getLogger(__name__)


# ======================================================================
# Constants
# ======================================================================

REQUIRED_SECTIONS: List[str] = [
    "# Project Overview",
    "# Problem Statement",
    "# Objectives",
    "# System Architecture",
    "# Core Components",
    "# Technologies Used",
    "# Data Flow / Execution Flow",
    "# Key Algorithms / Models",
    "# Configuration & Dependencies",
    "# Deployment / Running Instructions",
    "# Limitations",
    "# Future Scope",
]

# Thresholds (characters)
_DIRECT_CHAR_LIMIT: int = 400_000       # ≈100 K tokens — pack everything
_BATCH_CHAR_LIMIT: int = 40_000         # max chars per file for reading
_SUMMARY_CONTEXT_CAP: int = 800_000     # hard cap on combined summaries sent to final prompt


# ======================================================================
# Summariser class
# ======================================================================

class Summarizer:
    """Generates a structured technical summary from repository source code."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.0-flash",
    ) -> None:
        """Configure the Gemini model for summarisation.

        Args:
            api_key: Google AI / Gemini API key.
            model_name: Model identifier.
        """
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=genai.GenerationConfig(temperature=0.2),
        )
        self._model_name = model_name

    # ------------------------------------------------------------------
    # File reading helpers
    # ------------------------------------------------------------------

    @staticmethod
    def read_file_content(file_path: Path, max_chars: int = _BATCH_CHAR_LIMIT) -> str:
        """Read file content safely with a character cap.

        Args:
            file_path: Absolute path to the file.
            max_chars: Maximum characters to read.

        Returns:
            File content string (may be truncated).
        """
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            if len(content) > max_chars:
                content = content[:max_chars] + "\n\n... [TRUNCATED — file exceeds size limit]"
            return content
        except Exception as exc:
            logger.warning("Could not read %s: %s", file_path, exc)
            return ""

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Rough token estimate (~4 characters per token)."""
        return len(text) // 4

    # ------------------------------------------------------------------
    # Per-file and per-module summarisation
    # ------------------------------------------------------------------

    def _llm_call(self, prompt: str, label: str = "LLM") -> str:
        """Execute a single LLM call with error handling.

        Args:
            prompt: The full prompt string.
            label: A human-readable label for logging.

        Returns:
            Model response text, or an error placeholder.
        """
        try:
            logger.info("LLM call: %s (prompt length %d chars)", label, len(prompt))
            response = self._model.generate_content(prompt)
            return response.text.strip()
        except Exception as exc:
            logger.error("LLM error [%s]: %s", label, exc)
            return f"[Summary generation failed: {exc}]"

    def summarize_file(self, file_path: Path, repo_path: Path) -> str:
        """Generate a concise summary for a single source file.

        Args:
            file_path: Absolute path to the file.
            repo_path: Repository root (used for relative path display).

        Returns:
            Formatted per-file summary string.
        """
        relative = file_path.relative_to(repo_path)
        content = self.read_file_content(file_path)
        if not content.strip():
            return f"**{relative}**: Empty or unreadable file."

        prompt = (
            "Summarise this source file in 2–5 sentences. "
            "State its purpose, key functions/classes, and role in the project. "
            "Use ONLY information present in the code — do NOT fabricate anything.\n\n"
            f"File: {relative}\n\n```\n{content}\n```"
        )
        result = self._llm_call(prompt, label=str(relative))
        return f"**{relative}**: {result}"

    # ------------------------------------------------------------------
    # Batch strategies
    # ------------------------------------------------------------------

    def summarize_files_batch(
        self, files: List[Path], repo_path: Path
    ) -> List[str]:
        """Summarise a list of files, choosing direct or hierarchical strategy.

        Args:
            files: Filtered list of meaningful files.
            repo_path: Repository root path.

        Returns:
            List of summary strings (one per file or per module).
        """
        total_chars = sum(
            len(self.read_file_content(f)) for f in files
        )
        estimated_tokens = total_chars // 4
        logger.info(
            "Total content: %d chars ≈ %d tokens across %d files.",
            total_chars, estimated_tokens, len(files),
        )

        if total_chars <= _DIRECT_CHAR_LIMIT:
            logger.info("Using DIRECT summarisation strategy.")
            return self._direct_summarisation(files, repo_path)
        else:
            logger.info("Using HIERARCHICAL summarisation strategy.")
            return self._hierarchical_summarisation(files, repo_path)

    def _direct_summarisation(
        self, files: List[Path], repo_path: Path
    ) -> List[str]:
        """Summarise each file individually (small-repo path)."""
        summaries: List[str] = []
        for f in files:
            summaries.append(self.summarize_file(f, repo_path))
        return summaries

    def _hierarchical_summarisation(
        self, files: List[Path], repo_path: Path
    ) -> List[str]:
        """Group files by top-level directory, summarise per module."""
        groups: Dict[str, List[Path]] = {}
        for f in files:
            relative = f.relative_to(repo_path)
            top = relative.parts[0] if len(relative.parts) > 1 else "_root"
            groups.setdefault(top, []).append(f)

        module_summaries: List[str] = []
        for group_name, group_files in groups.items():
            # Summarise each file
            file_sums: List[str] = []
            for f in group_files:
                file_sums.append(self.summarize_file(f, repo_path))

            # Aggregate into module-level summary
            combined = "\n\n".join(file_sums)
            if len(combined) > _SUMMARY_CONTEXT_CAP:
                combined = combined[:_SUMMARY_CONTEXT_CAP] + "\n... [TRUNCATED]"

            prompt = (
                f"Based on the following individual file summaries from the "
                f"'{group_name}' module/directory, provide a concise module-level "
                f"summary (3–8 sentences). Only state what is explicitly present.\n\n"
                f"{combined}"
            )
            result = self._llm_call(prompt, label=f"module:{group_name}")
            module_summaries.append(f"## Module: {group_name}\n{result}")

        return module_summaries

    # ------------------------------------------------------------------
    # Final structured summary
    # ------------------------------------------------------------------

    def generate_summary(
        self,
        file_summaries: List[str],
        repo_name: str,
        tree: str,
    ) -> str:
        """Generate the final Markdown summary following the required schema.

        Args:
            file_summaries: Per-file or per-module summaries.
            repo_name: Repository name.
            tree: Directory tree string.

        Returns:
            Complete Markdown summary.
        """
        combined = "\n\n".join(file_summaries)
        if len(combined) > _SUMMARY_CONTEXT_CAP:
            combined = combined[:_SUMMARY_CONTEXT_CAP] + "\n\n... [TRUNCATED]"

        sections_list = "\n".join(REQUIRED_SECTIONS)

        prompt = (
            "You are a technical documentation expert. Based on the repository "
            "analysis below, generate a **structured technical summary** in "
            "Markdown.\n\n"
            f"**Repository:** {repo_name}\n\n"
            f"**Directory Structure:**\n```\n{tree}\n```\n\n"
            f"**File / Module Summaries:**\n{combined}\n\n"
            "---\n\n"
            "Generate the summary using these **exact** section headings "
            "(in this order):\n\n"
            f"{sections_list}\n\n"
            "**Rules (non-negotiable):**\n"
            "1. Use ONLY information explicitly present in the repository.\n"
            "2. If information for a section is not available, write exactly: "
            '"Not explicitly defined in repository."\n'
            "3. Do NOT fabricate datasets, metrics, or research claims.\n"
            "4. Do NOT assume or hallucinate any information.\n"
            "5. Be specific and technical — reference actual file names and "
            "code structures where relevant.\n"
        )

        result = self._llm_call(prompt, label="final_summary")

        # Quick sanity check — ensure all sections are present
        for section in REQUIRED_SECTIONS:
            if section not in result:
                logger.warning("Missing section in generated summary: %s", section)

        return result

    # ------------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------------

    @staticmethod
    def fallback_summary(repo_name: str) -> str:
        """Return a skeleton summary when LLM calls are unavailable.

        Args:
            repo_name: Repository name.

        Returns:
            Markdown string with all required sections.
        """
        header = f"# Summary for {repo_name}\n\n"
        body = "\n\n".join(
            f"{section}\nNot explicitly defined in repository."
            for section in REQUIRED_SECTIONS
        )
        return header + body

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @staticmethod
    def save_summary(summary: str, output_path: Path) -> None:
        """Write the summary to *output_path*.

        Args:
            summary: Markdown summary string.
            output_path: Destination file path.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(summary, encoding="utf-8")
        logger.info("Summary saved to: %s", output_path)
