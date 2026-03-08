"""
title_generator.py

Generates or improves a research-style title for a GitHub repository
using the Gemini LLM.
"""

import logging
from pathlib import Path
from typing import Optional

import google.generativeai as genai

logger = logging.getLogger(__name__)


class TitleGenerator:
    """Produces an academically styled title for a repository."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.0-flash",
    ) -> None:
        """Configure the Gemini model for title generation.

        Args:
            api_key: Google AI / Gemini API key.
            model_name: Model identifier.
        """
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=genai.GenerationConfig(temperature=0.2),
        )

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def generate_title(
        self,
        summary: str,
        repo_name: str,
        existing_title: Optional[str] = None,
    ) -> str:
        """Generate or refine a research-style title.

        If *existing_title* is provided, the title is improved for clarity
        while preserving core meaning. Otherwise a new title is synthesised.

        Args:
            summary: Repository summary text (may be large; first 3000 chars used).
            repo_name: Repository name string.
            existing_title: Optional user-supplied title to refine.

        Returns:
            A 10–18 word academic title string.
        """
        context = summary[:3000]

        if existing_title:
            prompt = (
                "Improve the following research paper title for clarity "
                "and academic precision.\n\n"
                f"**Original title:** {existing_title}\n\n"
                f"**Repository context (summary excerpt):**\n{context}\n\n"
                "Rules:\n"
                "1. Maintain the core meaning of the original title.\n"
                "2. Make it academically precise and specific.\n"
                "3. Length: 10–18 words.\n"
                "4. No vague phrases or buzzwords.\n"
                '5. Do NOT use generic patterns like "A System for …".\n'
                "6. Return ONLY the improved title — no explanation, no quotes."
            )
        else:
            prompt = (
                "Generate a research-style title for a software repository.\n\n"
                f"**Repository name:** {repo_name}\n\n"
                f"**Repository context (summary excerpt):**\n{context}\n\n"
                "Rules:\n"
                "1. Follow this pattern: "
                "[Primary Method / System Type] for [Problem Domain] "
                "Using [Key Technology].\n"
                "2. Length: 10–18 words.\n"
                "3. Academically precise and specific.\n"
                "4. No vague phrases or buzzwords.\n"
                '5. Do NOT use generic patterns like "A System for …".\n'
                "6. Return ONLY the title — no explanation, no quotes."
            )

        try:
            logger.info("Generating title via LLM …")
            response = self._model.generate_content(prompt)
            title = response.text.strip().strip('"').strip("'").strip()
            logger.info("Generated title: %s", title)
            return title
        except Exception as exc:
            logger.error("LLM error during title generation: %s", exc)
            return self._fallback_title(repo_name)

    # ------------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------------

    @staticmethod
    def _fallback_title(repo_name: str) -> str:
        """Produce a deterministic fallback title when the LLM is unavailable.

        Args:
            repo_name: Repository name.

        Returns:
            A generic but descriptive title string.
        """
        clean = repo_name.replace("-", " ").replace("_", " ").title()
        return (
            f"Technical Architecture and Implementation Analysis of "
            f"the {clean} Software Repository"
        )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @staticmethod
    def save_title(title: str, output_path: Path) -> None:
        """Write the generated title to *output_path*.

        Args:
            title: Title string.
            output_path: Destination file path.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(title, encoding="utf-8")
        logger.info("Title saved to: %s", output_path)
