"""
Advanced LaTeX Writing Agent
==============================
Generates journal-ready LaTeX papers with proper templates and structure.
"""

import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import asyncio

logger = logging.getLogger(__name__)


class LaTeXWritingAgent:
    """
    Agent for generating LaTeX academic papers.

    Features:
    - Multiple journal templates (IEEE, Springer, ACM)
    - Structured section filling
    - Reference management
    - Template-safe generation
    """

    TEMPLATES = {
        "IEEE": "ieee_template.tex",
        "Springer": "springer_template.tex",
        "ACM": "acm_template.tex"
    }

    def __init__(
        self,
        templates_dir: str = "multi_agent/Latex_engine/templates",
        workspace_dir: str = "multi_agent/Latex_engine/workspace"
    ):
        """
        Initialize LaTeX writing agent.

        Args:
            templates_dir: Directory containing LaTeX templates
            workspace_dir: Working directory for LaTeX compilation
        """
        self.templates_dir = Path(templates_dir)
        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

    async def generate_paper(
        self,
        paper_data: Dict[str, Any],
        template_type: str = "IEEE",
        output_name: str = "paper"
    ) -> Dict[str, Any]:
        """
        Generate LaTeX paper from structured data.

        Args:
            paper_data: Dictionary containing paper sections
            template_type: Template to use (IEEE, Springer, ACM)
            output_name: Output filename (without extension)

        Returns:
            Generation result with file paths
        """
        try:
            if template_type not in self.TEMPLATES:
                return {
                    "success": False,
                    "error": f"Unknown template: {template_type}"
                }

            # Load template
            template_file = self.templates_dir / self.TEMPLATES[template_type]

            if not template_file.exists():
                return {
                    "success": False,
                    "error": f"Template not found: {template_file}"
                }

            async with asyncio.to_thread(open, template_file, 'r', encoding='utf-8') as f:
                template_content = await asyncio.to_thread(f.read)

            # Fill template placeholders
            latex_content = self._fill_template(template_content, paper_data)

            # Generate BibTeX file
            bibtex_content = self._generate_bibtex(paper_data.get("citations", []))

            # Save files to workspace
            tex_file = self.workspace_dir / f"{output_name}.tex"
            bib_file = self.workspace_dir / "references.bib"

            async with asyncio.to_thread(open, tex_file, 'w', encoding='utf-8') as f:
                await asyncio.to_thread(f.write, latex_content)

            async with asyncio.to_thread(open, bib_file, 'w', encoding='utf-8') as f:
                await asyncio.to_thread(f.write, bibtex_content)

            return {
                "success": True,
                "tex_file": str(tex_file),
                "bib_file": str(bib_file),
                "template_type": template_type,
                "message": f"LaTeX paper generated: {tex_file}"
            }

        except Exception as e:
            logger.error(f"Error generating LaTeX paper: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _fill_template(self, template: str, data: Dict[str, Any]) -> str:
        """
        Fill template placeholders with paper data.

        Args:
            template: Template content
            data: Paper data

        Returns:
            Filled template
        """
        # Define placeholders and their values
        replacements = {
            "{{TITLE}}": data.get("title", "Untitled Research Paper"),
            "{{AUTHORS}}": data.get("authors", "Anonymous"),
            "{{SHORT_AUTHORS}}": data.get("short_authors", "Anonymous et al."),
            "{{AFFILIATION}}": data.get("affiliation", "Research Institution"),
            "{{EMAIL}}": data.get("email", "contact@example.com"),
            "{{ABSTRACT}}": self._escape_latex(data.get("abstract", "")),
            "{{KEYWORDS}}": data.get("keywords", "research, AI, automation"),
            "{{INTRODUCTION}}": self._escape_latex(data.get("introduction", "")),
            "{{LITERATURE_REVIEW}}": self._escape_latex(data.get("literature_review", "")),
            "{{METHODOLOGY}}": self._escape_latex(data.get("methodology", "")),
            "{{RESULTS}}": self._escape_latex(data.get("results", "")),
            "{{CONCLUSION}}": self._escape_latex(data.get("conclusion", "")),
        }

        # Replace placeholders
        content = template
        for placeholder, value in replacements.items():
            content = content.replace(placeholder, value)

        return content

    @staticmethod
    def _escape_latex(text: str) -> str:
        """
        Escape special LaTeX characters in text.

        Args:
            text: Plain text

        Returns:
            LaTeX-safe text
        """
        if not text:
            return ""

        # Special characters that need escaping
        escape_chars = {
            '&': r'\&',
            '%': r'\%',
            '$': r'\$',
            '#': r'\#',
            '_': r'\_',
            '{': r'\{',
            '}': r'\}',
            '~': r'\textasciitilde{}',
            '^': r'\textasciicircum{}',
        }

        for char, escaped in escape_chars.items():
            text = text.replace(char, escaped)

        return text

    def _generate_bibtex(self, citations: List[Dict[str, Any]]) -> str:
        """
        Generate BibTeX file from citations.

        Args:
            citations: List of citation dictionaries

        Returns:
            BibTeX content
        """
        if not citations:
            return ""

        bibtex_entries = []

        for idx, citation in enumerate(citations, 1):
            # Generate citation key
            key = citation.get("citation_key", f"ref{idx}")

            # Determine entry type
            entry_type = citation.get("bibtex_type", "article")

            # Build entry
            entry_lines = [f"@{entry_type}{{{key},"]

            # Add fields
            if citation.get("title"):
                entry_lines.append(f'  title = {{{citation["title"]}}},')

            if citation.get("authors"):
                authors = citation["authors"]
                if isinstance(authors, list):
                    authors = " and ".join(authors)
                entry_lines.append(f'  author = {{{authors}}},')

            if citation.get("year"):
                entry_lines.append(f'  year = {{{citation["year"]}}},')

            if citation.get("source"):
                if entry_type == "article":
                    entry_lines.append(f'  journal = {{{citation["source"]}}},')
                elif entry_type == "inproceedings":
                    entry_lines.append(f'  booktitle = {{{citation["source"]}}},')

            if citation.get("volume"):
                entry_lines.append(f'  volume = {{{citation["volume"]}}},')

            if citation.get("issue"):
                entry_lines.append(f'  number = {{{citation["issue"]}}},')

            if citation.get("pages"):
                entry_lines.append(f'  pages = {{{citation["pages"]}}},')

            if citation.get("doi"):
                entry_lines.append(f'  doi = {{{citation["doi"]}}},')

            if citation.get("url"):
                entry_lines.append(f'  url = {{{citation["url"]}}},')

            entry_lines.append("}")
            bibtex_entries.append("\n".join(entry_lines))

        return "\n\n".join(bibtex_entries)

    async def generate_section(
        self,
        section_name: str,
        content: str,
        citations: List[Dict[str, Any]],
        style: str = "academic"
    ) -> str:
        """
        Generate a formatted section with citations.

        Args:
            section_name: Section name
            content: Section content
            citations: Citations to include
            style: Writing style

        Returns:
            Formatted section content
        """
        # Add citations inline
        formatted_content = content

        # Replace citation markers with LaTeX \cite{} commands
        for idx, citation in enumerate(citations, 1):
            key = citation.get("citation_key", f"ref{idx}")
            # Look for citation markers like [1], [2], etc.
            formatted_content = re.sub(
                rf'\[{idx}\]',
                rf'\\cite{{{key}}}',
                formatted_content
            )

        return formatted_content
