"""Regression tests for LaTeX safety in PDF generation."""

from __future__ import annotations

import asyncio
import re
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agents.keyword_agent import KeywordAgent
from app.agents.publisher import PublisherAgent
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
    raw = "alpha=α and narrow space\u202fhere and dash\u2011ok by 张晋明"
    normalized = WritingService._normalize_latex_text(raw)
    assert "α" not in normalized
    assert "\u202f" not in normalized
    assert "\u2011" not in normalized
    assert "张" not in normalized
    assert "晋" not in normalized
    assert "明" not in normalized
    assert "alpha" in normalized


def test_publisher_escape_bibliography_text_strips_unsupported_unicode() -> None:
    escaped = PublisherAgent._escape_bibliography_text("J. Doe and 张晋明, Study on Vision, 2025.")
    assert "张" not in escaped
    assert "晋" not in escaped
    assert "明" not in escaped


def test_assemble_document_ieee_template_uses_ieeetran() -> None:
    agent = LaTeXWriterAgent()
    doc = LaTeXDocument(
        title="IEEE Template Test",
        author="Yukti Research AI",
        abstract="Short abstract.",
        keywords=["Underwater Enhancement", "Maritime Security", "Image Processing"],
        sections=[LaTeXSection(title="Introduction", content="Body text")],
        document_class="ieee",
    )

    latex = agent.assemble_document(doc)
    assert "\\documentclass[conference]{IEEEtran}" in latex
    assert "\\begin{IEEEkeywords}" not in latex
    assert "\\textbf{Keywords:}" in latex


def test_writing_service_humanizes_and_injects_ieee_bibliography(tmp_path: Path) -> None:
    svc = WritingService(output_dir=str(tmp_path))
    research_result = {
        "title": "Humanizer IEEE Test",
        "abstract": "This study presents a test abstract.",
        "report": "",
        "sections": [
            {
                "key": "introduction",
                "title": "Introduction",
                "content": "It is important to note that this section discusses the baseline and this section discusses the baseline.",
            },
            {
                "key": "references",
                "title": "References",
                "content": "[1] J. Doe, \"Test Paper,\" IEEE Access, 2025.",
            },
        ],
        "citations": {},
    }

    result = asyncio.run(
        svc.write(
            research_result=research_result,
            session_id="humanize01",
            compile_pdf=False,
            template="ieee",
        )
    )

    tex_text = Path(result["tex_path"]).read_text(encoding="utf-8")

    assert result["humanizer"]["applied"] is True
    assert "This study examines" in tex_text
    assert "It is important to note that" not in tex_text
    assert "\\begin{thebibliography}{99}" in tex_text
    assert "\\bibitem{ref1}" in tex_text
    assert "\\section{References}" not in tex_text


def test_writing_service_renders_from_default_ieee_template_file(tmp_path: Path) -> None:
    svc = WritingService(output_dir=str(tmp_path))
    research_result = {
        "title": "Template Runtime Render",
        "abstract": "Short abstract for template rendering.",
        "report": "",
        "sections": [
            {
                "key": "introduction",
                "title": "Introduction",
                "content": "Template content injection check.",
            }
        ],
        "citations": {},
    }

    result = asyncio.run(
        svc.write(
            research_result=research_result,
            session_id="template_render01",
            compile_pdf=False,
            template="ieee",
        )
    )

    tex_text = Path(result["tex_path"]).read_text(encoding="utf-8")
    template_text = Path(WritingService._IEEE_TEMPLATE_PATH).read_text(encoding="utf-8")
    class_match = re.search(r"\\documentclass\[[^\]]+\]\{IEEEtran\}", template_text)
    assert class_match is not None
    assert class_match.group(0) in tex_text
    assert "\\begin{IEEEkeywords}" not in tex_text
    assert "\\textbf{Keywords:}" in tex_text
    assert "\\section*{Acknowledgment}" not in tex_text
    assert "\\begin{appendices}" not in tex_text
    assert "This document is a model and instructions for" not in tex_text
    assert "Yukti Research AI" not in tex_text


def test_writing_service_abstract_block_contains_blank_line_and_keywords(tmp_path: Path) -> None:
    svc = WritingService(output_dir=str(tmp_path))
    research_result = {
        "title": "Abstract Keyword Layout",
        "abstract": "Abstract—This paper studies robust underwater enhancement.\n\nIndex Terms—foo, bar",
        "report": "",
        "sections": [
            {
                "key": "introduction",
                "title": "Introduction",
                "content": "The pipeline is evaluated on maritime image datasets.",
            }
        ],
        "citations": {},
    }

    result = asyncio.run(
        svc.write(
            research_result=research_result,
            session_id="abstract_layout01",
            compile_pdf=False,
            template="ieee",
        )
    )

    tex_text = Path(result["tex_path"]).read_text(encoding="utf-8")
    abstract_match = re.search(r"\\begin\{abstract\}([\s\S]*?)\\end\{abstract\}", tex_text)
    assert abstract_match is not None
    abstract_body = abstract_match.group(1)
    assert "Index Terms" not in abstract_body
    assert "Repository context summary" not in abstract_body
    assert "\n\n\\textbf{Keywords:}" in abstract_body


def test_writing_service_keeps_existing_intro_when_writer_model_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("WRITER_MODEL", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)

    svc = WritingService(output_dir=str(tmp_path))
    research_result = {
        "title": "Intro Preservation Test",
        "abstract": "Short abstract.",
        "report": "",
        "sections": [
            {
                "key": "introduction",
                "title": "Introduction",
                "content": "Custom introduction from synthesizer should remain unchanged.",
            },
            {
                "key": "conclusion",
                "title": "Conclusion",
                "content": "Custom conclusion from synthesizer should remain unchanged.",
            },
        ],
        "citations": {},
    }

    result = asyncio.run(
        svc.write(
            research_result=research_result,
            session_id="writer_skip01",
            compile_pdf=False,
            template="ieee",
            use_multi_agent_writer=True,
        )
    )

    tex_text = Path(result["tex_path"]).read_text(encoding="utf-8")
    assert result["writer_agent"]["status"] == "skipped_no_model"
    assert "Custom introduction from synthesizer should remain unchanged." in tex_text
    assert "Custom conclusion from synthesizer should remain unchanged." in tex_text


def test_keyword_agent_extracts_from_abstract() -> None:
    agent = KeywordAgent()
    keywords = agent.extract_keywords(
        title="Underwater Enhancement for Maritime Security",
        abstract=(
            "We propose an underwater image enhancement pipeline using diffusion models "
            "for low-light maritime scenes and robust vessel surveillance."
        ),
        provided=[],
    )

    assert 3 <= len(keywords) <= 4
    assert any("Underwater" in kw or "Maritime" in kw for kw in keywords)


def test_writing_service_rejects_non_ieee_templates(tmp_path: Path) -> None:
    svc = WritingService(output_dir=str(tmp_path))
    research_result = {
        "title": "Template Validation",
        "abstract": "Short abstract.",
        "report": "",
        "sections": [],
        "citations": {},
    }

    with pytest.raises(ValueError, match="Unsupported template"):
        asyncio.run(
            svc.write(
                research_result=research_result,
                session_id="template01",
                compile_pdf=False,
                template="springer",
            )
        )

    with pytest.raises(ValueError, match="Unsupported template"):
        asyncio.run(
            svc.write(
                research_result=research_result,
                session_id="template02",
                compile_pdf=False,
                template="acm",
            )
        )


def test_writing_service_ieee_bibliography_wraps_urls() -> None:
    svc = WritingService(output_dir="outputs")
    long_url = "https://example.org/research/path/" + ("very-long-segment-" * 12)

    block = svc._build_ieee_bibliography(
        citations={"formatted": [f"[1] J. Doe, \"Long URL Study,\" IEEE Access, 2025. {long_url}"]},
        inline_entries=[],
    )

    assert "\\url{https://example.org/research/path/" in block


def test_writing_service_removes_ack_and_keeps_heading_without_placeholder(tmp_path: Path) -> None:
    svc = WritingService(output_dir=str(tmp_path))
    research_result = {
        "title": "Heading Only Test",
        "abstract": "Short abstract.",
        "report": "",
        "sections": [
            {
                "key": "methodology",
                "title": "Methodology",
                "content": "",
            }
        ],
        "citations": {},
    }

    result = asyncio.run(
        svc.write(
            research_result=research_result,
            session_id="heading_only01",
            compile_pdf=False,
            template="ieee",
            use_multi_agent_writer=False,
        )
    )

    tex_text = Path(result["tex_path"]).read_text(encoding="utf-8")
    assert "\\section*{Acknowledgment}" not in tex_text
    assert "No content available." not in tex_text
    assert "\\section{Methodology}" in tex_text


def test_extract_reference_lines_handles_heading_and_wrapped_entries() -> None:
    raw = """REFERENCES
REFERENCES
[1] U. Author, \"A Long Reference Title,
continued part with year 2024 and doi: 10.1000/example.1.
[2] P. Author, \"Second Ref,\" IEEE Access, 2025.
"""

    refs = WritingService._extract_reference_lines(raw)

    assert len(refs) == 2
    assert refs[0].startswith("[1] U. Author")
    assert "continued part with year 2024" in refs[0]
    assert refs[1].startswith("[2] P. Author")


def test_writing_service_bibliography_ignores_duplicate_reference_heading() -> None:
    svc = WritingService(output_dir="outputs")
    block = svc._build_ieee_bibliography(
        citations={},
        inline_entries=[
            "REFERENCES",
            "[1] A. Author, \"Paper One,\" IEEE Access, 2024. doi: 10.1000/a1.",
            "[2] B. Author, \"Paper Two,\" IEEE Access, 2025.",
        ],
    )

    assert "\\bibitem{ref1}" in block
    assert "\\bibitem{ref2}" in block
    assert "REFERENCES" not in block


def test_ieee_writer_skips_explicit_references_section_when_bibliography_present() -> None:
    agent = LaTeXWriterAgent()
    doc = LaTeXDocument(
        title="No Duplicate References",
        author="Yukti",
        abstract="Test abstract.",
        sections=[
            LaTeXSection(title="Introduction", content="Body."),
            LaTeXSection(title="References", content="Should not render as section."),
        ],
        bibliography=["dummy"],
        document_class="ieee",
    )

    latex = agent.assemble_document(doc)
    assert "\\section{References}" not in latex
    assert "\\bibliography{references}" in latex


def test_writing_service_verifies_citations_before_writing(tmp_path: Path) -> None:
    svc = WritingService(output_dir=str(tmp_path))
    research_result = {
        "title": "Citation Verification Before Writing",
        "abstract": "Short abstract.",
        "report": "",
        "sections": [
            {
                "key": "introduction",
                "title": "Introduction",
                "content": "This section validates reference filtering.",
            }
        ],
        "citations": {
            "citations": [
                {
                    "number": 1,
                    "formatted": "[1] Blog Note, random blog post, 2025.",
                    "verified": False,
                    "paper": {
                        "title": "AI",
                        "authors": [],
                        "year": "2025",
                        "url": "https://example.com/blog",
                        "source": "Blog",
                    },
                },
                {
                    "number": 2,
                    "formatted": "[2] J. Doe, \"Underwater Image Enhancement for Maritime Security\", IEEE Access, 2025. doi: 10.1000/valid.1.",
                    "paper": {
                        "title": "Underwater Image Enhancement for Maritime Security",
                        "authors": ["Jane Doe"],
                        "year": "2025",
                        "url": "https://ieeexplore.ieee.org/document/1234567",
                        "doi": "10.1000/valid.1",
                        "source": "IEEE Access",
                    },
                },
            ]
        },
    }

    result = asyncio.run(
        svc.write(
            research_result=research_result,
            session_id="citation_verify01",
            compile_pdf=False,
            template="ieee",
        )
    )

    tex_text = Path(result["tex_path"]).read_text(encoding="utf-8")
    assert "random blog post" not in tex_text
    assert "Underwater Image Enhancement for Maritime Security" in tex_text
    assert result["citation_verification"]["verified_kept"] == 1
    assert result["citation_verification"]["filtered_out"] >= 1
