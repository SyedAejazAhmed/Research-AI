"""Regression tests for LaTeX safety in PDF generation."""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from multi_agent.agents.latex_writer import LaTeXDocument, LaTeXWriterAgent, LaTeXSection
from server.writing_service import WritingService


def test_markdown_to_latex_escapes_underscore_in_doi() -> None:
    agent = LaTeXWriterAgent()
    md = "doi: 10.1007/978-3-030-86271-8_47"
    out = agent.markdown_to_latex(md)
    assert "10.1007/978-3-030-86271-8\\_47" in out


def test_section_title_escapes_ampersand() -> None:
    sec = LaTeXSection(title="Result & Discussion", content="Body")
    latex = sec.to_latex()
    assert "\\section{Result \\& Discussion}" in latex


def test_normalize_latex_text_replaces_problem_unicode() -> None:
    raw = "alpha=α and narrow space\u202fhere and dash\u2011ok"
    normalized = WritingService._normalize_latex_text(raw)
    assert "α" not in normalized
    assert "\u202f" not in normalized
    assert "\u2011" not in normalized
    assert "alpha" in normalized


def test_assemble_document_ieee_template_uses_ieeetran() -> None:
    agent = LaTeXWriterAgent()
    doc = LaTeXDocument(
        title="IEEE Template Test",
        author="Yukti Research AI",
        abstract="Short abstract.",
        sections=[LaTeXSection(title="Introduction", content="Body text")],
        document_class="ieee",
    )

    latex = agent.assemble_document(doc)
    assert "\\documentclass[conference]{IEEEtran}" in latex
    assert "\\begin{IEEEkeywords}" in latex
