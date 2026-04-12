"""
Writing Service
===============
Integrates WriterAgent (markdown report → structured sections) and
LaTeXWriterAgent (markdown → LaTeX section conversion) with the LaTeX Engine compiler.

Pipeline:
    research_result  →  _render_ieee_template_document()  →  .tex file
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
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

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
from app.agents.keyword_agent import KeywordAgent  # noqa: E402
from app.utils.humanizer import BasicAcademicHumanizer  # noqa: E402
from app.utils.references import is_verified_academic_paper, pyzotero_capabilities  # noqa: E402


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

    _TEMPLATE_ALIASES = {
        "ieee": "ieee",
        "ieeetran": "ieee",
        "ieee-tran": "ieee",
        "ieee_tran": "ieee",
    }
    _IEEE_TEMPLATE_PATH = _ROOT / "multi_agent" / "Latex_engine" / "templates" / "ieee.tex"

    def __init__(self, output_dir: str = "outputs", docker_timeout: int = 300):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.latex_agent = LaTeXWriterAgent()
        self.keyword_agent = KeywordAgent()
        self.humanizer = BasicAcademicHumanizer()
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
        template: str = "ieee",
        author: str = "",
        use_multi_agent_writer: bool = False,
        allow_fallback_pdf: bool = False,
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
        keyword_terms = research_result.get("keywords", [])
        template_name = self._normalize_template(template)

        citations, citation_verification = self._verify_citations_for_writing(citations)

        logger.info(f"[WritingService] Building LaTeX for session {session_id}")

        writer_meta = {
            "enabled": bool(use_multi_agent_writer),
            "applied": False,
            "status": "disabled",
            "error": None,
        }

        if use_multi_agent_writer:
            writer_result = await self._compose_with_multi_agent_writer(
                title=title,
                sections_data=sections_data,
                citations=citations,
                template=template_name,
            )
            sections_data = writer_result["sections_data"]
            writer_meta = writer_result["metadata"]

        humanized = self._humanize_for_writing(
            abstract=abstract,
            sections_data=sections_data,
            report_md=report_md,
        )

        # Render runtime .tex from the default IEEE template file.
        tex_content = self._render_ieee_template_document(
            title=title,
            author=author,
            abstract=humanized["abstract"],
            report_md=humanized["report_md"],
            sections_data=humanized["sections_data"],
            citations=citations,
            keyword_terms=keyword_terms,
        )
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
            "fallback_pdf_used": False,
            "compile_errors": [],
            "compile_warnings": [],
            "humanizer": {
                "enabled": True,
                "name": "basic_academic_v1",
                "applied": humanized["applied"],
            },
            "writer_agent": writer_meta,
            "template": template_name,
            "citation_verification": citation_verification,
        }

        if citation_verification.get("filtered_out", 0) > 0:
            result["compile_warnings"].append(
                f"Filtered {citation_verification['filtered_out']} unverified or malformed citation(s) before writing."
            )

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

        if compile_pdf and not result["pdf_success"] and allow_fallback_pdf:
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
                result["fallback_pdf_used"] = True
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

    def _render_ieee_template_document(
        self,
        title: str,
        author: str,
        abstract: str,
        report_md: str,
        sections_data: List[Dict[str, Any]],
        citations: Dict[str, Any],
        keyword_terms: Optional[List[str]] = None,
    ) -> str:
        """Fill the default IEEE template file with runtime content."""
        template_text = self._load_ieee_template_text()

        section_block, inline_reference_entries = self._build_ieee_sections_block(
            sections_data=sections_data,
            report_md=report_md,
        )
        bibliography_block = self._build_ieee_bibliography(
            citations=citations,
            inline_entries=inline_reference_entries,
        )

        cleaned_abstract = self._clean_generated_abstract(abstract)

        keywords = self.keyword_agent.extract_keywords(
            title=title,
            abstract=cleaned_abstract,
            provided=keyword_terms,
            limit=3,
        )
        if len(keywords) < 2:
            for fallback in ["Underwater Imaging", "Image Enhancement", "Maritime Security"]:
                if fallback.lower() not in {k.lower() for k in keywords}:
                    keywords.append(fallback)
                if len(keywords) >= 2:
                    break
        keywords_text = self._escape_latex(", ".join(keywords[:3]))

        latex_abstract = self.latex_agent.markdown_to_latex(cleaned_abstract).strip() if cleaned_abstract else ""
        latex_abstract = latex_abstract or "No abstract provided."
        abstract_block = f"{latex_abstract}\n\n\\textbf{{Keywords:}} {keywords_text}"

        rendered = template_text
        rendered = self._replace_command_argument(
            rendered,
            command="title",
            replacement_argument=self._escape_latex(title),
        )
        rendered = self._replace_command_argument(
            rendered,
            command="author",
            replacement_argument=self._build_ieee_author_block(author),
        )
        rendered = self._replace_environment_content(
            rendered,
            env_name="abstract",
            replacement_content=abstract_block,
        )
        sections_replaced = self._replace_between_markers(
            rendered,
            start_marker="\\end{abstract}",
            end_marker="\\section*{Acknowledgment}",
            replacement=("\n\n" + section_block.strip() + "\n\n"),
        )
        if sections_replaced == rendered:
            sections_replaced = self._replace_between_markers(
                rendered,
                start_marker="\\end{abstract}",
                end_marker="\\section*{References}",
                replacement=("\n\n" + section_block.strip() + "\n\n"),
            )
        if sections_replaced == rendered:
            sections_replaced = self._replace_between_markers(
                rendered,
                start_marker="\\end{IEEEkeywords}",
                end_marker="\\section*{Acknowledgment}",
                replacement=("\n\n" + section_block.strip() + "\n\n"),
            )
        if sections_replaced == rendered:
            sections_replaced = self._replace_between_markers(
                rendered,
                start_marker="\\end{IEEEkeywords}",
                end_marker="\\section*{References}",
                replacement=("\n\n" + section_block.strip() + "\n\n"),
            )
        rendered = sections_replaced
        rendered = self._remove_environment(rendered, "IEEEkeywords")
        rendered = self._remove_acknowledgment_region(rendered)
        rendered = self._replace_references_region(rendered, bibliography_block)
        rendered = self._remove_appendices_region(rendered)
        rendered = self._ensure_ieee_runtime_packages(rendered)

        return rendered

    @classmethod
    def _load_ieee_template_text(cls) -> str:
        if not cls._IEEE_TEMPLATE_PATH.exists():
            raise FileNotFoundError(f"IEEE template file not found: {cls._IEEE_TEMPLATE_PATH}")
        return cls._IEEE_TEMPLATE_PATH.read_text(encoding="utf-8")

    def _build_ieee_sections_block(
        self,
        sections_data: List[Dict[str, Any]],
        report_md: str,
    ) -> Tuple[str, List[str]]:
        """Build body sections LaTeX and collect inline references."""
        sections: List[str] = []
        inline_reference_entries: List[str] = []

        if sections_data:
            for sec in sections_data:
                sec_title = str(sec.get("title", "Section")).strip() or "Section"
                sec_body = str(sec.get("content", sec.get("body", ""))).strip()

                sec_key = str(sec.get("key", "")).strip().lower()
                is_references = sec_key == "references" or sec_title.lower() == "references"
                if is_references:
                    inline_reference_entries.extend(self._extract_reference_lines(sec_body))
                    continue

                latex_body = self.latex_agent.markdown_to_latex(sec_body).strip() if sec_body else ""
                section_head = f"\\section{{{self._escape_latex(sec_title)}}}"
                sections.append(f"{section_head}\n{latex_body}" if latex_body else section_head)
        elif report_md:
            parsed_sections = self._parse_markdown_sections(report_md, self.latex_agent)
            for section in parsed_sections:
                title_norm = (section.title or "").strip().lower()
                if title_norm == "references":
                    inline_reference_entries.extend(self._extract_reference_lines(section.content or ""))
                    continue
                sections.append(section.to_latex().strip())

        return "\n\n".join(sections), inline_reference_entries

    def _build_ieee_author_block(self, author: str) -> str:
        clean_author = self._escape_latex((author or "").strip())
        # Keep author optional: an empty block avoids hardcoded branding in output.
        return clean_author if clean_author else " "

    @staticmethod
    def _replace_command_argument(latex_text: str, command: str, replacement_argument: str) -> str:
        token = f"\\{command}"
        cmd_idx = latex_text.find(token)
        if cmd_idx == -1:
            return latex_text

        brace_start = latex_text.find("{", cmd_idx + len(token))
        if brace_start == -1:
            return latex_text

        depth = 0
        brace_end = -1
        for i in range(brace_start, len(latex_text)):
            char = latex_text[i]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    brace_end = i
                    break

        if brace_end == -1:
            return latex_text

        replacement = f"\\{command}{{{replacement_argument}}}"
        return latex_text[:cmd_idx] + replacement + latex_text[brace_end + 1:]

    @staticmethod
    def _replace_environment_content(latex_text: str, env_name: str, replacement_content: str) -> str:
        pattern = re.compile(
            rf"\\begin\{{{re.escape(env_name)}\}}.*?\\end\{{{re.escape(env_name)}\}}",
            re.DOTALL,
        )
        block = f"\\begin{{{env_name}}}\n{replacement_content.strip()}\n\\end{{{env_name}}}"
        # Use a callable replacement to avoid regex template escaping of LaTeX backslashes.
        return pattern.sub(lambda _match: block, latex_text, count=1)

    @staticmethod
    def _remove_environment(latex_text: str, env_name: str) -> str:
        pattern = re.compile(
            rf"\\n?\\begin\{{{re.escape(env_name)}\}}[\s\S]*?\\end\{{{re.escape(env_name)}\}}\\n?",
            re.DOTALL,
        )
        return pattern.sub("\n", latex_text, count=1)

    @staticmethod
    def _clean_generated_abstract(abstract: str) -> str:
        """Drop prompt/meta noise from abstract text before LaTeX insertion."""
        cleaned = str(abstract or "").replace("\r\n", "\n").replace("\r", "\n").strip()
        if not cleaned:
            return ""

        cleaned = re.sub(r"^\s*Abstract\s*[—:\-]\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^\s*Index\s+Terms?\s*[—:\-].*$", "", cleaned, flags=re.IGNORECASE | re.MULTILINE)

        lower = cleaned.lower()
        cut_markers = [
            "repository context summary",
            "##analysis",
            "analysis stats",
            "structure preview",
        ]
        cut_points = [idx for idx in (lower.find(marker) for marker in cut_markers) if idx != -1]
        if cut_points:
            cleaned = cleaned[: min(cut_points)].strip()

        lines: List[str] = []
        for line in cleaned.split("\n"):
            stripped = line.strip()
            if not stripped:
                lines.append("")
                continue

            lowered = stripped.lower()
            if lowered.startswith("`") and lowered.endswith("`"):
                continue
            if lowered.startswith("don't let ai write"):
                continue
            if lowered.startswith("we don't need repository context summary"):
                continue

            lines.append(stripped)

        compact = "\n".join(lines)
        compact = re.sub(r"\n{3,}", "\n\n", compact)
        return compact.strip()

    @staticmethod
    def _replace_between_markers(
        latex_text: str,
        start_marker: str,
        end_marker: str,
        replacement: str,
    ) -> str:
        start = latex_text.find(start_marker)
        if start == -1:
            return latex_text

        search_from = start + len(start_marker)
        end = latex_text.find(end_marker, search_from)
        if end == -1:
            return latex_text

        return latex_text[:search_from] + replacement + latex_text[end:]

    def _replace_references_region(self, latex_text: str, bibliography_block: str) -> str:
        refs_marker = "\\section*{References}"
        start = latex_text.find(refs_marker)
        if start == -1:
            references = refs_marker + "\n\n" + (bibliography_block or self._fallback_bibliography_block())
            return self._inject_before_end_document(latex_text, references)

        appendix_start = latex_text.find("\\begin{appendices}", start)
        end_document = latex_text.find("\\end{document}", start)

        if appendix_start != -1:
            region_end = appendix_start
        elif end_document != -1:
            region_end = end_document
        else:
            region_end = len(latex_text)

        references = refs_marker + "\n\n" + (bibliography_block or self._fallback_bibliography_block()) + "\n\n"
        return latex_text[:start] + references + latex_text[region_end:]

    @staticmethod
    def _remove_appendices_region(latex_text: str) -> str:
        return re.sub(r"\\begin\{appendices\}[\s\S]*?\\end\{appendices\}\s*", "", latex_text)

    @staticmethod
    def _remove_acknowledgment_region(latex_text: str) -> str:
        """Remove template acknowledgment section content from runtime output."""
        pattern = re.compile(
            r"\\section\*\{Acknowledg(?:e)?ment[s]?\}[\s\S]*?(?=\\section\*\{References\}|\\begin\{appendices\}|\\end\{document\})",
            re.IGNORECASE,
        )
        return pattern.sub("", latex_text, count=1)

    @staticmethod
    def _ensure_ieee_runtime_packages(latex_text: str) -> str:
        # Ensure URL commands in bibliography always compile and line-wrap.
        if "\\usepackage{url}" in latex_text:
            return latex_text

        insertion = "\\usepackage{url}"
        marker = "\\usepackage{textcomp}"
        idx = latex_text.find(marker)
        if idx == -1:
            begin_doc = latex_text.find("\\begin{document}")
            if begin_doc == -1:
                return insertion + "\n" + latex_text
            return latex_text[:begin_doc] + insertion + "\n" + latex_text[begin_doc:]

        insert_at = idx + len(marker)
        return latex_text[:insert_at] + "\n" + insertion + latex_text[insert_at:]

    @staticmethod
    def _fallback_bibliography_block() -> str:
        return "\\begin{thebibliography}{99}\n\\bibitem{ref1} No references available.\n\\end{thebibliography}"

    def _build_latex_doc(
        self,
        title: str,
        author: str,
        abstract: str,
        report_md: str,
        sections_data: List[Dict],
        citations: Dict[str, Any],
        template: str,
        keyword_terms: Optional[List[str]] = None,
    ) -> Tuple[LaTeXDocument, str]:
        """Convert research data into a LaTeXDocument."""

        agent = self.latex_agent
        sections: List[LaTeXSection] = []
        inline_reference_entries: List[str] = []
        normalized_template = self._normalize_template(template)
        use_ieee = normalized_template == "ieee"

        if sections_data:
            for sec in sections_data:
                sec_title = sec.get("title", "Section")
                sec_body = sec.get("content", sec.get("body", ""))
                if not sec_body:
                    continue

                sec_key = str(sec.get("key", "")).strip().lower()
                is_references = sec_key == "references" or str(sec_title).strip().lower() == "references"
                if use_ieee and is_references:
                    inline_reference_entries.extend(self._extract_reference_lines(sec_body))
                    continue

                latex_body = agent.markdown_to_latex(sec_body)
                sections.append(
                    agent.create_section(sec_title, latex_body, level=1)
                )
        elif report_md:
            # Parse markdown headings to split into sections
            sections = self._parse_markdown_sections(report_md, agent)

        ieee_bibliography_block = ""
        if use_ieee:
            ieee_bibliography_block = self._build_ieee_bibliography(
                citations=citations,
                inline_entries=inline_reference_entries,
            )
        else:
            # Append references section for non-IEEE templates.
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
            document_class=normalized_template,
            keywords=self.keyword_agent.extract_keywords(
                title=title,
                abstract=abstract,
                provided=keyword_terms,
            ),
        )
        return doc, ieee_bibliography_block

    @classmethod
    def _normalize_template(cls, template: str) -> str:
        raw = str(template or "").strip().lower()
        normalized = cls._TEMPLATE_ALIASES.get(raw)
        if normalized:
            return normalized
        raise ValueError("Unsupported template. Allowed values: 'ieee'.")

    async def _compose_with_multi_agent_writer(
        self,
        title: str,
        sections_data: List[Dict[str, Any]],
        citations: Dict[str, Any],
        template: str,
    ) -> Dict[str, Any]:
        """Use multi_agent WriterAgent to shape intro/conclusion/reference layout."""
        metadata = {
            "enabled": True,
            "applied": False,
            "status": "fallback",
            "error": None,
        }

        try:
            from multi_agent.agents.writer import WriterAgent
        except Exception as exc:
            metadata["error"] = f"multi_agent writer import failed: {exc}"
            return {"sections_data": sections_data, "metadata": metadata}

        try:
            style = "IEEE"
            guidelines = (
                "Use IEEE style academic writing. Keep formal third-person tone. "
                "References must use numeric IEEE style like [1], [2]."
            )
            writer_task = {
                "model": os.environ.get("WRITER_MODEL") or os.environ.get("OLLAMA_MODEL"),
                "follow_guidelines": True,
                "guidelines": guidelines,
                "citation_style": style,
                "verbose": False,
            }

            if not writer_task["model"]:
                metadata["status"] = "skipped_no_model"
                return {"sections_data": sections_data, "metadata": metadata}

            writer_state = {
                "title": title,
                "research_data": self._sections_to_writer_data(sections_data),
                "task": writer_task,
            }

            payload = await WriterAgent().run(writer_state)
            if str(payload.get("_writer_mode", "")).strip().lower() != "model":
                metadata["status"] = "fallback_skipped"
                return {"sections_data": sections_data, "metadata": metadata}

            merged_sections, applied = self._merge_writer_payload(
                sections_data=sections_data,
                payload=payload,
                citations=citations,
            )

            metadata["applied"] = applied
            metadata["status"] = "applied" if applied else "no_change"
            return {"sections_data": merged_sections, "metadata": metadata}

        except Exception as exc:
            logger.warning("multi_agent writer composition failed; keeping original sections: %s", exc)
            metadata["error"] = str(exc)
            metadata["status"] = "fallback"
            return {"sections_data": sections_data, "metadata": metadata}

    @staticmethod
    def _sections_to_writer_data(sections_data: List[Dict[str, Any]]) -> List[str]:
        """Convert section dicts to writer-friendly list blocks."""
        out: List[str] = []
        for section in sections_data or []:
            title = str(section.get("title", "Section")).strip()
            key = str(section.get("key", "")).strip().lower()
            body = str(section.get("content", section.get("body", ""))).strip()
            if not body:
                continue
            if key == "references" or title.lower() == "references":
                continue
            out.append(f"### {title}\n{body}")
        return out

    def _merge_writer_payload(
        self,
        sections_data: List[Dict[str, Any]],
        payload: Any,
        citations: Dict[str, Any],
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """Merge WriterAgent payload into section list without dropping existing content."""
        if not isinstance(payload, dict):
            return sections_data, False

        intro = str(payload.get("introduction", "")).strip()
        conclusion = str(payload.get("conclusion", "")).strip()
        sources = payload.get("sources", [])

        merged = [dict(s) for s in (sections_data or [])]
        changed = False

        def _upsert(section_key: str, section_title: str, section_content: str) -> None:
            nonlocal changed
            if not section_content:
                return
            for section in merged:
                key = str(section.get("key", "")).strip().lower()
                title = str(section.get("title", "")).strip().lower()
                if key == section_key or title == section_title.lower():
                    if str(section.get("content", "")).strip() != section_content:
                        section["content"] = section_content
                        section["key"] = section_key
                        section["title"] = section_title
                        changed = True
                    return
            merged.append({"key": section_key, "title": section_title, "content": section_content})
            changed = True

        _upsert("introduction", "Introduction", intro)
        _upsert("conclusion", "Conclusion", conclusion)

        if isinstance(sources, list) and sources:
            refs_text = "\n".join(str(s).strip() for s in sources if str(s).strip())
            if refs_text:
                has_formatted = bool((citations or {}).get("formatted") or (citations or {}).get("formatted_text"))
                if not has_formatted:
                    _upsert("references", "References", refs_text)

        return merged, changed

    def _humanize_for_writing(
        self,
        abstract: str,
        sections_data: List[Dict[str, Any]],
        report_md: str,
    ) -> Dict[str, Any]:
        """Apply lightweight text humanization before LaTeX conversion."""
        applied = False

        new_abstract = self.humanizer.humanize(abstract) if abstract else abstract
        if new_abstract != abstract:
            applied = True

        new_sections: List[Dict[str, Any]] = []
        for section in sections_data or []:
            clone = dict(section)
            sec_title = str(clone.get("title", "")).strip().lower()
            sec_key = str(clone.get("key", "")).strip().lower()
            is_references = sec_key == "references" or sec_title == "references"

            body_key = "content" if "content" in clone else "body"
            body = str(clone.get(body_key, ""))

            if body and not is_references:
                humanized = self.humanizer.humanize(body)
                if humanized != body:
                    applied = True
                clone[body_key] = humanized

            new_sections.append(clone)

        return {
            "abstract": new_abstract,
            "sections_data": new_sections,
            # Keep report_md unchanged to avoid accidental citation mutations when
            # section-level content is unavailable.
            "report_md": report_md,
            "applied": applied,
        }

    @staticmethod
    def _extract_year_from_text(text: str) -> str:
        match = re.search(r"\b(19|20)\d{2}\b", str(text or ""))
        return match.group(0) if match else ""

    @staticmethod
    def _extract_doi_from_text(text: str) -> str:
        match = re.search(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b", str(text or ""))
        return match.group(0) if match else ""

    def _verify_citations_for_writing(self, citations: Any) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Filter citation payload down to verified scholarly entries before LaTeX writing."""
        source = citations if isinstance(citations, dict) else {}
        out = dict(source)

        raw_citations = source.get("citations", []) if isinstance(source.get("citations", []), list) else []
        verified_entries: List[Dict[str, Any]] = []
        filtered_out = 0
        seen = set()

        for item in raw_citations:
            if not isinstance(item, dict):
                filtered_out += 1
                continue

            paper_raw = item.get("paper", {})
            paper = paper_raw if isinstance(paper_raw, dict) else {}

            formatted = str(item.get("formatted") or item.get("citation") or item.get("text") or "").strip()
            title = str(paper.get("title") or "").strip()
            if not title and formatted:
                quoted = re.search(r'"([^"\n]{8,})"', formatted)
                title = (quoted.group(1).strip() if quoted else re.sub(r"^(\[\d+\]|\d+\.)\s*", "", formatted).strip())[:220]

            authors_raw = paper.get("authors") or []
            authors = [str(a).strip() for a in authors_raw if str(a).strip()]
            year = str(paper.get("year") or self._extract_year_from_text(formatted)).strip()
            doi = str(item.get("doi") or paper.get("doi") or self._extract_doi_from_text(formatted)).strip()
            url = str(paper.get("url") or "").strip()
            source_name = str(paper.get("source") or "").strip()

            verification = is_verified_academic_paper(
                {
                    "title": title,
                    "url": url,
                    "doi": doi,
                    "year": year,
                    "source": source_name,
                    "authors": authors,
                }
            )

            explicitly_verified = bool(item.get("verified"))
            if not (explicitly_verified or verification.get("is_academic_paper", False)):
                filtered_out += 1
                continue

            sanitized = self._sanitize_reference_entry(formatted)
            if not sanitized and title:
                fallback = f'{title}, {source_name}, {year}.' if source_name or year else title
                if doi:
                    fallback += f" doi: {doi}."
                sanitized = self._sanitize_reference_entry(fallback)

            if not sanitized:
                filtered_out += 1
                continue

            normalized = re.sub(r"\s+", " ", sanitized).strip().lower()
            if normalized in seen:
                continue
            seen.add(normalized)

            ref_number = len(verified_entries) + 1
            sanitized = re.sub(r"^(\[\d+\]|\d+\.)\s*", "", sanitized).strip()
            verified_entries.append(
                {
                    "number": ref_number,
                    "formatted": f"[{ref_number}] {sanitized}",
                    "doi": doi,
                    "verified": True,
                    "paper": {
                        "title": title,
                        "authors": authors,
                        "year": year,
                        "url": url,
                        "doi": doi,
                        "source": source_name,
                        "verification_reason": verification.get("reason", ""),
                    },
                }
            )

        if verified_entries:
            out["citations"] = verified_entries
            out["formatted"] = [entry["formatted"] for entry in verified_entries]
            out["formatted_text"] = "## References\n\n" + "\n\n".join(entry["formatted"] for entry in verified_entries)
            out["total"] = len(verified_entries)
            out["verified"] = len(verified_entries)

        pyz_payload = source.get("pyzotero") if isinstance(source.get("pyzotero"), dict) else pyzotero_capabilities()
        verification_meta = {
            "input_total": len(raw_citations),
            "verified_kept": len(verified_entries),
            "filtered_out": filtered_out,
            "pyzotero_available": bool(pyz_payload.get("available", False)) if isinstance(pyz_payload, dict) else False,
            "requested_style_supported": bool(pyz_payload.get("requested_style_supported", False)) if isinstance(pyz_payload, dict) else False,
        }
        return out, verification_meta

    @staticmethod
    def _extract_reference_lines(text: str) -> List[str]:
        """Extract numbered references while preserving wrapped continuation lines."""
        refs: List[str] = []
        current_number: Optional[str] = None
        current_parts: List[str] = []

        def _flush() -> None:
            nonlocal current_number, current_parts
            if current_number and current_parts:
                merged = " ".join(part for part in current_parts if part).strip()
                merged = re.sub(r"\s+", " ", merged)
                merged = merged.strip(" -")
                if merged:
                    refs.append(f"[{current_number}] {merged}")
            current_number = None
            current_parts = []

        for raw in str(text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
            line = raw.strip()
            if not line:
                # Blank line likely denotes end of a wrapped entry.
                _flush()
                continue

            lowered = line.lower().strip("*#:- ")
            if lowered in {"references", "reference", "bibliography", "index terms", "keywords"}:
                continue
            if lowered.startswith("## references"):
                continue

            if line.startswith("- "):
                line = line[2:].strip()

            numbered = re.match(r"^\[(\d+)\]\s*(.+)$", line)
            if not numbered:
                numbered = re.match(r"^(\d+)\.(?:\s+|\s*$)(.*)$", line)

            if numbered:
                _flush()
                current_number = numbered.group(1)
                body = (numbered.group(2) or "").strip()
                if body:
                    current_parts.append(body)
                continue

            if current_number:
                # Continuation line for current numbered reference.
                current_parts.append(line)

        _flush()
        return refs

    @staticmethod
    def _sanitize_reference_entry(entry: str) -> str:
        """Normalize a single reference entry and remove heading noise."""
        raw = str(entry or "").replace("\r\n", "\n").replace("\r", "\n").strip()
        if not raw:
            return ""

        lines = []
        for line in raw.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            lowered = stripped.lower().strip("*#:- ")
            if lowered in {"references", "reference", "bibliography", "index terms", "keywords"}:
                continue
            if lowered.startswith("## references"):
                continue
            lines.append(stripped)

        if not lines:
            return ""

        merged = " ".join(lines)
        merged = re.sub(r"\s+", " ", merged).strip()
        merged = re.sub(r"^(\[(\d+)\]|\d+\.)\s*", "", merged)
        merged = merged.replace("”", '"').replace("“", '"').replace("’", "'").replace("‘", "'")

        # Keep only plausible reference-like entries.
        has_year = bool(re.search(r"\b(19|20)\d{2}\b", merged))
        has_doi = bool(re.search(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b", merged))
        has_source_marker = bool(re.search(r"\b(doi:|https?://|IEEE|Springer|Elsevier|Journal|Conference|Transactions)\b", merged, re.IGNORECASE))
        if not (has_year or has_doi or has_source_marker):
            return ""

        return merged

    def _build_ieee_bibliography(
        self,
        citations: Dict[str, Any],
        inline_entries: List[str],
    ) -> str:
        """Build an IEEE-style thebibliography block."""
        entries: List[str] = []

        for cite in citations.get("citations", []) or []:
            if not isinstance(cite, dict):
                continue
            if ("verified" in cite) and not bool(cite.get("verified")):
                continue
            text = str(cite.get("formatted") or cite.get("citation") or cite.get("text") or "").strip()
            if text:
                entries.append(text)

        for ref in citations.get("formatted", []) or []:
            if isinstance(ref, dict):
                if ("verified" in ref) and not bool(ref.get("verified")):
                    continue
                text = str(ref.get("citation", ref.get("text", ref.get("formatted", "")))).strip()
            else:
                text = str(ref).strip()
            if text:
                entries.append(text)

        if not entries:
            formatted_text = str(citations.get("formatted_text", "") or "")
            entries.extend(self._extract_reference_lines(formatted_text))

        entries.extend([e for e in inline_entries if e and e.strip()])

        unique_entries: List[str] = []
        seen = set()
        for entry in entries:
            sanitized = self._sanitize_reference_entry(entry)
            if not sanitized:
                continue
            normalized = re.sub(r"\s+", " ", sanitized).strip().lower()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            unique_entries.append(sanitized)

        if not unique_entries:
            return ""

        bib_lines = ["\\begin{thebibliography}{99}"]
        for idx, entry in enumerate(unique_entries, start=1):
            cleaned = re.sub(r"^\[\d+\]\s*", "", entry).strip()
            bib_lines.append(f"\\bibitem{{ref{idx}}} {self._escape_latex_with_urls(cleaned)}")
        bib_lines.append("\\end{thebibliography}")
        return "\n".join(bib_lines)

    @staticmethod
    def _inject_before_end_document(latex_text: str, block: str) -> str:
        """Inject extra LaTeX content immediately before \\end{document}."""
        marker = "\\end{document}"
        idx = latex_text.rfind(marker)
        if idx == -1:
            return latex_text.rstrip() + "\n\n" + block.strip() + "\n"
        return latex_text[:idx].rstrip() + "\n\n" + block.strip() + "\n\n" + latex_text[idx:]

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
            text = self._escape_latex_with_urls(text)
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

    @classmethod
    def _escape_latex_with_urls(cls, text: str) -> str:
        """Escape LaTeX text while preserving URLs through \\url{} wrappers."""
        raw = str(text or "")
        if not raw:
            return ""

        parts: List[str] = []
        cursor = 0
        for match in re.finditer(r"https?://\S+", raw):
            start, end = match.span()
            token = match.group(0)
            url = token.rstrip(".,);]")
            trailing = token[len(url):]

            if start > cursor:
                parts.append(cls._escape_latex(raw[cursor:start]))

            if url:
                parts.append(f"\\url{{{cls._sanitize_url_for_latex(url)}}}")
            if trailing:
                parts.append(cls._escape_latex(trailing))

            cursor = end

        if cursor < len(raw):
            parts.append(cls._escape_latex(raw[cursor:]))

        return "".join(parts)

    @staticmethod
    def _sanitize_url_for_latex(url: str) -> str:
        """Normalize URLs used inside \\url{} to avoid brace-related parse errors."""
        clean = str(url or "").strip().replace("\\", "/")
        clean = quote(clean, safe=":/?#[]@!$&'()*+,;=%-._~")
        clean = clean.replace("{", "%7B").replace("}", "%7D")
        return clean

    @staticmethod
    def _normalize_latex_text(text: str) -> str:
        """Normalize problematic Unicode/entities that can break pdflatex."""
        if not text:
            return ""

        normalized = html.unescape(str(text))
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

        # Transliterate remaining Unicode to ASCII where possible and drop
        # unsupported glyphs to keep pdflatex compilation stable.
        normalized = unicodedata.normalize("NFKD", normalized)
        normalized = normalized.encode("ascii", "ignore").decode("ascii")

        # Keep printable ASCII plus common whitespace controls.
        normalized = "".join(
            ch for ch in normalized if ch in "\n\r\t" or 32 <= ord(ch) <= 126
        )
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
