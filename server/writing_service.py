"""
Writing Service
===============
Integrates WriterAgent (markdown report → structured sections) and
LaTeXWriterAgent (LaTeX assembly) with the LaTeX Engine compiler.

Pipeline:
  research_result  →  _build_latex_doc()  →  .tex file
                                           →  pdflatex (local / Docker)  →  .pdf file
"""

import logging
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Ensure project root is on sys.path so local packages (multi_agent, researcher) are found
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from multi_agent.agents.latex_writer import (       # noqa: E402
    LaTeXDocument,
    LaTeXSection,
    LaTeXWriterAgent,
)
from multi_agent.Latex_engine.compiler.compile import LaTeXCompiler  # noqa: E402
from multi_agent.Latex_engine.compiler.error_parser import parse_latex_log  # noqa: E402


# ---------------------------------------------------------------------------
# Local pdflatex compiler (no Docker required)
# ---------------------------------------------------------------------------

class LocalLaTeXCompiler:
    """
    Compile .tex → .pdf using a locally installed pdflatex binary.
    Falls back gracefully if pdflatex is not available.
    """

    def __init__(self, timeout: int = 120):
        self.timeout = timeout
        self._has_pdflatex: Optional[bool] = None

    def _check_pdflatex(self) -> bool:
        if self._has_pdflatex is None:
            self._has_pdflatex = (
                subprocess.run(
                    ["which", "pdflatex"],
                    capture_output=True
                ).returncode == 0
            )
        return self._has_pdflatex

    def compile(
        self,
        tex_file: str,
        workspace_path: str,
        bibtex: bool = False,
    ) -> Dict[str, Any]:
        """
        Compile a .tex file.  Returns the same dict shape as LaTeXCompiler.
        Tries local pdflatex first; falls back to Docker LaTeXCompiler.
        """
        if self._check_pdflatex():
            return self._compile_local(tex_file, workspace_path, bibtex)

        # Try Docker-based compiler
        logger.info("pdflatex not found locally; trying Docker compiler…")
        try:
            docker_compiler = LaTeXCompiler(timeout=self.timeout)
            return docker_compiler.compile(tex_file, workspace_path, bibtex=bibtex)
        except Exception as exc:
            return {
                "success": False,
                "pdf_path": None,
                "errors": [
                    f"pdflatex is not installed and Docker compilation failed: {exc}",
                    "Install TeX Live:  sudo apt install texlive-full",
                ],
                "warnings": [],
                "log": "",
            }

    def _compile_local(
        self,
        tex_file: str,
        workspace_path: str,
        bibtex: bool,
    ) -> Dict[str, Any]:
        base = os.path.splitext(tex_file)[0]
        pdf_path = os.path.join(workspace_path, f"{base}.pdf")
        log_path = os.path.join(workspace_path, f"{base}.log")

        def _run(cmd: List[str]) -> subprocess.CompletedProcess:
            return subprocess.run(
                cmd,
                cwd=workspace_path,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

        try:
            base_cmd = [
                "pdflatex",
                "-interaction=nonstopmode",
                "-halt-on-error",
                tex_file,
            ]
            _run(base_cmd)    # first pass

            if bibtex and list(Path(workspace_path).glob("*.bib")):
                _run(["bibtex", base])
                _run(base_cmd)    # second pass

            result = _run(base_cmd)  # final pass

            log_content = ""
            errors: List[str] = []
            warnings: List[str] = []

            if os.path.exists(log_path):
                with open(log_path, "r", encoding="utf-8", errors="ignore") as fh:
                    log_content = fh.read()
                parsed = parse_latex_log(log_content)
                errors = parsed["errors"]
                warnings = parsed["warnings"]

            # If return code is 0 and pdf exists → success
            success = result.returncode == 0 and os.path.exists(pdf_path)

            return {
                "success": success,
                "pdf_path": pdf_path if os.path.exists(pdf_path) else None,
                "errors": errors,
                "warnings": warnings,
                "log": log_content,
                "raw_output": result.stdout + result.stderr,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "pdf_path": None,
                "errors": [f"Compilation timed out after {self.timeout}s"],
                "warnings": [],
                "log": "",
            }
        except Exception as exc:
            return {
                "success": False,
                "pdf_path": None,
                "errors": [f"Compilation error: {exc}"],
                "warnings": [],
                "log": "",
            }


# ---------------------------------------------------------------------------
# Writing Service
# ---------------------------------------------------------------------------

class WritingService:
    """
    End-to-end service that turns a research result dict into:
      • A structured LaTeX document (.tex)
      • An optionally compiled PDF (.pdf)

    Usage::

        svc = WritingService(output_dir="outputs")
        result = await svc.write(research_result, session_id="abc123")
        # result["tex_path"], result["pdf_path"]
    """

    def __init__(self, output_dir: str = "outputs", docker_timeout: int = 300):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.latex_agent = LaTeXWriterAgent()
        # Prefer local pdflatex when available; otherwise fall back to Docker.
        self.compiler = LocalLaTeXCompiler(timeout=docker_timeout)

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def write(
        self,
        research_result: Dict[str, Any],
        session_id: str,
        compile_pdf: bool = True,
        template: str = "article",
        author: str = "Yukti Research AI",
    ) -> Dict[str, Any]:
        """
        Generate .tex (and optionally .pdf) from a research_result dict.

        Expected keys in research_result:
            title, report (markdown string), abstract, sections, citations
        """
        title = research_result.get("title", "Research Report")
        abstract = research_result.get("abstract", "")
        report_md = research_result.get("report", "")
        sections_data = research_result.get("sections", [])
        citations = research_result.get("citations", {})

        logger.info(f"[WritingService] Building LaTeX for session {session_id}")

        # Build LaTeX document
        doc = self._build_latex_doc(
            title=title,
            author=author,
            abstract=abstract,
            report_md=report_md,
            sections_data=sections_data,
            citations=citations,
            template=template,
        )

        tex_content = self.latex_agent.assemble_document(doc)
        tex_content = self._normalize_latex_text(tex_content)

        # Write .tex file
        tex_path = self.output_dir / f"{session_id}_report.tex"
        tex_path.write_text(tex_content, encoding="utf-8")
        logger.info(f"[WritingService] .tex saved → {tex_path}")

        result: Dict[str, Any] = {
            "session_id": session_id,
            "tex_path": str(tex_path),
            "pdf_path": None,
            "pdf_success": False,
            "compile_errors": [],
            "compile_warnings": [],
        }

        if compile_pdf:
            with tempfile.TemporaryDirectory(prefix="yukti_latex_") as tmpdir:
                # Copy .tex (and any .bib if present) into the temp workspace
                tmp_tex = Path(tmpdir) / f"{session_id}_report.tex"
                tmp_tex.write_text(tex_content, encoding="utf-8")

                # Copy bibliography if it exists alongside the tex
                bib_src = self.output_dir / f"{session_id}.bib"
                if bib_src.exists():
                    import shutil
                    shutil.copy(str(bib_src), tmpdir)

                compile_result = self.compiler.compile(
                    tex_file=tmp_tex.name,
                    workspace_path=tmpdir,
                    bibtex=bib_src.exists(),
                )

                result["compile_errors"] = compile_result.get("errors", [])
                result["compile_warnings"] = compile_result.get("warnings", [])
                result["pdf_success"] = compile_result.get("success", False)

                if compile_result.get("pdf_path") and Path(compile_result["pdf_path"]).exists():
                    pdf_dest = self.output_dir / f"{session_id}_report.pdf"
                    self._safe_replace_file(compile_result["pdf_path"], str(pdf_dest))
                    result["pdf_path"] = str(pdf_dest)
                    logger.info(f"[WritingService] .pdf saved → {pdf_dest}")
                else:
                    logger.warning(
                        f"[WritingService] PDF compilation failed: "
                        f"{compile_result.get('errors', [])}"
                    )

        if compile_pdf and not result["pdf_success"]:
            try:
                fallback_pdf = self.output_dir / f"{session_id}_report.pdf"
                self._generate_fallback_pdf(
                    title=title,
                    abstract=abstract,
                    sections_data=sections_data,
                    report_md=report_md,
                    citations=citations,
                    output_path=fallback_pdf,
                )
                result["pdf_success"] = True
                result["pdf_path"] = str(fallback_pdf)
                result["compile_warnings"].append(
                    "LaTeX compilation failed or was unavailable; generated fallback PDF output."
                )
                logger.info("[WritingService] Fallback PDF saved -> %s", fallback_pdf)
            except Exception as exc:
                result["compile_errors"].append(f"Fallback PDF generation failed: {exc}")
                logger.error("[WritingService] Fallback PDF generation error: %s", exc, exc_info=True)

        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_latex_doc(
        self,
        title: str,
        author: str,
        abstract: str,
        report_md: str,
        sections_data: List[Dict],
        citations: Dict[str, Any],
        template: str,
    ) -> LaTeXDocument:
        """Convert research data into a LaTeXDocument."""

        agent = self.latex_agent
        sections: List[LaTeXSection] = []

        if sections_data:
            for sec in sections_data:
                sec_title = sec.get("title", "Section")
                sec_body = sec.get("content", sec.get("body", ""))
                if not sec_body:
                    continue
                latex_body = agent.markdown_to_latex(sec_body)
                sections.append(
                    agent.create_section(sec_title, latex_body, level=1)
                )
        elif report_md:
            # Parse markdown headings to split into sections
            sections = self._parse_markdown_sections(report_md, agent)

        # Append references section if citations exist
        refs_latex = self._build_references_section(citations)
        has_references_section = any(
            (s.title or "").strip().lower() == "references" for s in sections
        )
        if refs_latex and not has_references_section:
            sections.append(
                agent.create_section(
                    title="References",
                    content=refs_latex,
                    level=1,
                )
            )

        doc = LaTeXDocument(
            title=self._escape_latex(title),
            author=author,
            abstract=agent.markdown_to_latex(abstract) if abstract else "",
            sections=sections,
            document_class=template,
        )
        return doc

    def _parse_markdown_sections(
        self, md: str, agent: LaTeXWriterAgent
    ) -> List[LaTeXSection]:
        """Split a markdown string on `## Heading` boundaries into LaTeXSections."""
        sections: List[LaTeXSection] = []
        # Pattern: lines starting with #, ##, or ###
        pattern = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
        matches = list(pattern.finditer(md))

        if not matches:
            # Whole report as one section
            latex_body = agent.markdown_to_latex(md)
            sections.append(agent.create_section("Report", latex_body, level=1))
            return sections

        # Add any text that comes before the first header as "Overview"
        preamble = md[: matches[0].start()].strip()
        if preamble:
            sections.append(
                agent.create_section("Overview", agent.markdown_to_latex(preamble), level=1)
            )

        for i, match in enumerate(matches):
            hashes, heading = match.group(1), match.group(2)
            level = len(hashes)
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(md)
            body = md[start:end].strip()
            latex_body = agent.markdown_to_latex(body) if body else ""
            sections.append(agent.create_section(heading, latex_body, level=level))

        return sections

    def _build_references_section(self, citations: Dict[str, Any]) -> str:
        """Build a plain LaTeX reference list from citations dict."""
        formatted = citations.get("formatted", [])
        if not formatted:
            return ""

        lines = ["\\begin{enumerate}"]
        for ref in formatted:
            if isinstance(ref, dict):
                text = ref.get("citation", ref.get("text", str(ref)))
            else:
                text = str(ref)
            # Escape special chars for LaTeX
            text = self._escape_latex(text)
            lines.append(f"  \\item {text}")
        lines.append("\\end{enumerate}")
        return "\n".join(lines)

    @staticmethod
    def _escape_latex(text: str) -> str:
        """Escape characters that are special in LaTeX (outside math mode)."""
        replacements = [
            ("\\", r"\textbackslash{}"),
            ("&", r"\&"),
            ("%", r"\%"),
            ("#", r"\#"),
            ("_", r"\_"),
            ("{", r"\{"),
            ("}", r"\}"),
            ("~", r"\textasciitilde{}"),
            ("^", r"\^{}"),
        ]
        for src, dst in replacements:
            text = text.replace(src, dst)
        return text

    @staticmethod
    def _normalize_latex_text(text: str) -> str:
        """Normalize problematic Unicode/entities that can break pdflatex."""
        if not text:
            return ""

        normalized = html.unescape(text)
        replacements = {
            "\u00a0": " ",      # non-breaking space
            "\u202f": " ",      # narrow non-breaking space
            "\u2011": "-",      # non-breaking hyphen
            "\u2013": "-",      # en dash
            "\u2014": "--",     # em dash
            "\u2018": "'",
            "\u2019": "'",
            "\u201c": '"',
            "\u201d": '"',
            "\u03b1": "alpha",  # Greek alpha
            "\u03b2": "beta",
            "\u03b3": "gamma",
            "\u03bb": "lambda",
            "\u03bc": "mu",
            "\u03c3": "sigma",
            "\ufeff": "",       # BOM
        }
        for src, dst in replacements.items():
            normalized = normalized.replace(src, dst)
        return normalized

    @staticmethod
    def _safe_replace_file(src_path: str, dst_path: str) -> None:
        """Atomically replace destination file, even if an older file is read-only."""
        src = Path(src_path)
        dst = Path(dst_path)
        tmp_dst = dst.with_suffix(dst.suffix + ".tmp")

        if tmp_dst.exists():
            tmp_dst.unlink(missing_ok=True)

        shutil.copy2(str(src), str(tmp_dst))

        try:
            os.replace(str(tmp_dst), str(dst))
        except PermissionError:
            # If a stale file exists with restrictive mode/ownership, remove it and retry.
            if dst.exists():
                dst.unlink(missing_ok=True)
            os.replace(str(tmp_dst), str(dst))

    def _generate_fallback_pdf(
        self,
        title: str,
        abstract: str,
        sections_data: List[Dict[str, Any]],
        report_md: str,
        citations: Dict[str, Any],
        output_path: Path,
    ) -> None:
        """Generate a plain-text PDF when LaTeX compilation is unavailable."""
        from fpdf import FPDF

        class FallbackPDF(FPDF):
            def header(self):
                self.set_font("helvetica", "I", 8)
                self.set_text_color(120)
                self.cell(0, 8, "Yukti Research AI - Fallback PDF", 0, 0, "R")
                self.ln(10)

            def footer(self):
                self.set_y(-12)
                self.set_font("helvetica", "I", 8)
                self.set_text_color(120)
                self.cell(0, 8, f"Page {self.page_no()}", 0, 0, "C")

        plain_text = self._fallback_plain_text(title, abstract, sections_data, report_md, citations)
        plain_text = plain_text.encode("latin-1", "replace").decode("latin-1")

        pdf = FallbackPDF()
        pdf.set_auto_page_break(auto=True, margin=14)
        pdf.add_page()

        pdf.set_font("helvetica", "B", 16)
        pdf.set_text_color(20, 20, 20)
        pdf.multi_cell(0, 8, title or "Research Report")
        pdf.ln(2)

        pdf.set_font("helvetica", "", 10)
        pdf.set_text_color(40, 40, 40)
        for para in [p.strip() for p in plain_text.split("\n\n") if p.strip()]:
            pdf.multi_cell(0, 6, para)
            pdf.ln(1)

        pdf.output(str(output_path))

    @staticmethod
    def _fallback_plain_text(
        title: str,
        abstract: str,
        sections_data: List[Dict[str, Any]],
        report_md: str,
        citations: Dict[str, Any],
    ) -> str:
        """Build plain text payload for fallback PDF output."""
        lines: List[str] = [title or "Research Report", ""]

        if abstract:
            lines.extend(["Abstract", abstract, ""])

        if sections_data:
            for sec in sections_data:
                sec_title = str(sec.get("title", "Section")).strip() or "Section"
                sec_content = str(sec.get("content", sec.get("body", ""))).strip()
                if not sec_content:
                    continue
                lines.extend([sec_title, sec_content, ""])
        elif report_md:
            lines.extend(["Report", report_md, ""])

        formatted_refs = str(citations.get("formatted_text", "")).strip() if isinstance(citations, dict) else ""
        if formatted_refs:
            lines.extend(["References", formatted_refs, ""])

        text = "\n".join(lines)
        # Lightweight markdown cleanup for readable fallback output.
        text = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1 (\2)", text)
        text = text.replace("## ", "\n").replace("# ", "\n")
        text = text.replace("**", "").replace("`", "")
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
