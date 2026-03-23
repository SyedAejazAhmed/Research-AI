"""
Yukti Research AI - Publisher Agent
=====================================
Structures sections, applies academic tone,
generates final report, and handles export (PDF/Word).
"""

import logging
import json
import os
import shutil
import tempfile
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class PublisherAgent:
    """
    Publisher Agent: Final report formatting and export.
    
    Responsibilities:
    - Structure sections with academic formatting
    - Generate PDF and Word exports
    - Store session history
    """
    
    def __init__(self, output_dir: str = "outputs"):
        self.name = "Publisher Agent"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    async def publish(self, synthesis: Dict[str, Any], session_id: str, callback=None) -> Dict[str, Any]:
        """
        Publish the final research report.
        """
        if callback:
            await callback("publisher", "publishing", "Preparing final report...")
        
        full_report = synthesis.get("full_report", "")
        title = synthesis.get("title", "Research Report")
        compile_errors = []
        compile_warnings = []
        
        # Save markdown report
        report_path = self.output_dir / f"{session_id}_report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(full_report)
        
        # Generate HTML version
        if callback:
            await callback("publisher", "publishing", "Generating HTML & PDF reports...")
        
        html_content = self._markdown_to_html(full_report, title)
        html_path = self.output_dir / f"{session_id}_report.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        # Generate LaTeX version (IEEE Style)
        latex_path = self.output_dir / f"{session_id}_report.tex"
        try:
            self._generate_latex(synthesis, str(latex_path))
            has_latex = True
        except Exception as e:
            logger.error(f"LaTeX generation error: {e}")
            has_latex = False

        # Generate PDF from TeX first (preferred), fallback to markdown PDF.
        pdf_path = self.output_dir / f"{session_id}_report.pdf"
        has_pdf = False
        if has_latex:
            has_pdf, compile_errors, compile_warnings = self._compile_pdf_from_tex(
                tex_path=str(latex_path),
                output_pdf_path=str(pdf_path)
            )

        if not has_pdf:
            try:
                self._generate_pdf(full_report, title, str(pdf_path))
                has_pdf = True
            except Exception as e:
                logger.error(f"PDF generation error: {e}")
                has_pdf = False
        
        # Save session metadata
        metadata = {
            "session_id": session_id,
            "title": title,
            "word_count": synthesis.get("word_count", 0),
            "sections": len(synthesis.get("sections", [])),
            "created_at": datetime.now().isoformat(),
            "files": {
                "markdown": str(report_path),
                "html": str(html_path),
                "pdf": str(pdf_path) if has_pdf else None,
                "latex": str(latex_path) if has_latex else None,
                "compile_errors": compile_errors,
                "compile_warnings": compile_warnings,
            },
        }
        
        meta_path = self.output_dir / f"{session_id}_meta.json"
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)
        
        if callback:
            await callback("publisher", "completed", "Report published in Markdown, HTML, PDF, and LaTeX! 🎉")
        
        return {
            "agent": self.name,
            "session_id": session_id,
            "title": title,
            "files": {
                "markdown": str(report_path),
                "html": str(html_path),
                "pdf": str(pdf_path) if has_pdf else None,
                "latex": str(latex_path) if has_latex else None,
                "metadata": str(meta_path)
            },
            "compile_errors": compile_errors,
            "compile_warnings": compile_warnings,
            "word_count": synthesis.get("word_count", 0),
            "timestamp": datetime.now().isoformat()
        }

    def _compile_pdf_from_tex(self, tex_path: str, output_pdf_path: str):
        """Compile PDF from an existing TeX file using the LaTeX Docker compiler."""
        try:
            from multi_agent.Latex_engine.compiler.compile import LaTeXCompiler

            with tempfile.TemporaryDirectory(prefix="yukti_pub_") as tmpdir:
                tex_name = os.path.basename(tex_path)
                tmp_tex = os.path.join(tmpdir, tex_name)
                shutil.copy(tex_path, tmp_tex)

                compiler = LaTeXCompiler(image_name="texlive-compiler:latest", timeout=300)
                result = compiler.compile(tex_file=tex_name, workspace_path=tmpdir, bibtex=False)

                errors = result.get("errors", [])
                warnings = result.get("warnings", [])
                pdf_tmp_path = result.get("pdf_path")

                if result.get("success") and pdf_tmp_path and os.path.exists(pdf_tmp_path):
                    shutil.copy(pdf_tmp_path, output_pdf_path)
                    return True, errors, warnings

                logger.warning(f"TeX to PDF compilation failed: {errors}")
                return False, errors, warnings

        except Exception as e:
            logger.error(f"TeX to PDF compilation error: {e}")
            return False, [str(e)], []

    def _generate_latex(self, synthesis: Dict, output_path: str):
        """Generate an IEEE-style LaTeX file, preferring the repository template file."""
        title = synthesis.get("title", "Research Report")
        abstract = synthesis.get("abstract", "")
        sections = synthesis.get("sections", [])

        # Simple LaTeX escape function
        def tex_escape(text):
            return text.replace('&', '\\&').replace('%', '\\%').replace('$', '\\$').replace('#', '\\#').replace('_', '\\_').replace('{', '\\{').replace('}', '\\}')

        section_map = {
            "INTRODUCTION": "",
            "LITERATURE_REVIEW": "",
            "METHODOLOGY": "",
            "RESULTS": "",
            "CONCLUSION": "",
        }
        for section in sections:
            sec_title_raw = section.get("title", "")
            sec_title = sec_title_raw.lower()
            sec_content = tex_escape(section.get("content", ""))
            if "intro" in sec_title:
                section_map["INTRODUCTION"] = sec_content
            elif "literature" in sec_title or "related" in sec_title:
                section_map["LITERATURE_REVIEW"] = sec_content
            elif "method" in sec_title:
                section_map["METHODOLOGY"] = sec_content
            elif "result" in sec_title or "discussion" in sec_title:
                section_map["RESULTS"] = sec_content
            elif "conclusion" in sec_title:
                section_map["CONCLUSION"] = sec_content

        template_path = Path("multi_agent/Latex_engine/templates/ieee_template.tex")
        if template_path.exists():
            template = template_path.read_text(encoding="utf-8")
            latex_template = (
                template
                .replace("{{TITLE}}", tex_escape(title))
                .replace("{{AUTHORS}}", "YuktiResearch AI Agent")
                .replace("{{AFFILIATION}}", "Autonomous Research Division")
                .replace("{{EMAIL}}", "research@yukti.local")
                .replace("{{ABSTRACT}}", tex_escape(abstract))
                .replace("{{KEYWORDS}}", "Academic Research, AI Synthesis, Autonomous Agents, Yukti AI")
                .replace("{{INTRODUCTION}}", section_map["INTRODUCTION"])
                .replace("{{LITERATURE_REVIEW}}", section_map["LITERATURE_REVIEW"])
                .replace("{{METHODOLOGY}}", section_map["METHODOLOGY"])
                .replace("{{RESULTS}}", section_map["RESULTS"])
                .replace("{{CONCLUSION}}", section_map["CONCLUSION"])
            )
        else:
            latex_template = r"""\documentclass[conference]{IEEEtran}
\IEEEoverridecommandlockouts
\usepackage{cite}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{algorithmic}
\usepackage{graphicx}
\usepackage{textcomp}
\def\BibTeX{{\rm B\kern-.05em{\sc i\kern-.025em b}\kern-.08em
    T\kern-.1667em\lower.7ex\hbox{E}\kern-.125emX}}
\begin{document}

	itle{""" + tex_escape(title) + r"""}

\author{\IEEEauthorblockN{YuktiResearch AI Agent}
\IEEEauthorblockA{\textit{Autonomous Research Division} \\
	extit{Dart Vadar Team}\\
St. Joseph's College of Engineering \\
Chennai, India}
}

\maketitle

\begin{abstract}
""" + tex_escape(abstract) + r"""
\end{abstract}

\begin{IEEEkeywords}
Academic Research, AI Synthesis, Autonomous Agents, Yukti AI
\end{IEEEkeywords}

"""
            # Add sections if template file is missing
            for section in sections:
                section_title = tex_escape(section.get("title", "Untitled Section"))
                section_content = tex_escape(section.get("content", ""))
                latex_template += f"\\section{{{section_title}}}\n{section_content}\n\n"

            latex_template += r"""
\section*{Acknowledgment}
This research was generated autonomously by Yukti Research AI for Prince PROTOTHON'26.

\begin{thebibliography}{00}
\bibitem{b1} Generated via Yukti Research Agent Pipeline using ArXiv and Semantic Scholar sources.
\end{thebibliography}

\end{document}
"""

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(latex_template)

    def _generate_pdf(self, markdown_text: str, title: str, output_path: str):
        """Generate a native PDF from markdown text."""
        from fpdf import FPDF
        
        class PDF(FPDF):
            def header(self):
                self.set_font('helvetica', 'B', 8)
                self.set_text_color(150)
                self.cell(0, 10, 'Yukti Research AI - Autonomous Academic Report', 0, 0, 'R')
                self.ln(15)

            def footer(self):
                self.set_y(-15)
                self.set_font('helvetica', 'I', 8)
                self.set_text_color(150)
                self.cell(0, 10, f'Page {self.page_no()} | Generated by YuktiResearch AI', 0, 0, 'C')

        pdf = PDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        
        # Title
        pdf.set_font('helvetica', 'B', 24)
        pdf.set_text_color(15, 12, 41) # Deep blue
        pdf.multi_cell(0, 15, title)
        pdf.ln(5)
        
        # Generation Date
        pdf.set_font('helvetica', 'I', 10)
        pdf.set_text_color(100)
        pdf.cell(0, 10, f"Date: {datetime.now().strftime('%B %d, %Y')}", ln=True)
        pdf.ln(10)
        
        # Parse markdown and add to PDF
        pdf.set_font('times', '', 12)
        pdf.set_text_color(0)
        
        # Clean markdown formatting for simple PDF output
        clean_text = markdown_text.replace('# ', '').replace('## ', '\n').replace('### ', '')
        clean_text = clean_text.replace('**', '').replace('*', '')
        
        # Replace non-latin-1 characters
        clean_text = clean_text.encode('latin-1', 'replace').decode('latin-1')
        
        pdf.multi_cell(0, 7, clean_text)
        pdf.output(output_path)
    
    def _markdown_to_html(self, markdown_text: str, title: str) -> str:
        """Convert markdown to styled HTML document."""
        try:
            import markdown
            body = markdown.markdown(
                markdown_text,
                extensions=["tables", "fenced_code", "toc"]
            )
        except ImportError:
            # Simple conversion
            body = self._simple_md_to_html(markdown_text)
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Yukti Research AI</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Merriweather:wght@300;400;700&display=swap');
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Merriweather', Georgia, serif;
            line-height: 1.8;
            color: #1a1a2e;
            max-width: 800px;
            margin: 0 auto;
            padding: 40px 20px;
            background: #fefefe;
        }}
        
        h1 {{
            font-family: 'Inter', sans-serif;
            font-size: 2rem;
            font-weight: 700;
            color: #0f0c29;
            margin-bottom: 0.5em;
            border-bottom: 3px solid #667eea;
            padding-bottom: 0.3em;
        }}
        
        h2 {{
            font-family: 'Inter', sans-serif;
            font-size: 1.4rem;
            font-weight: 600;
            color: #302b63;
            margin-top: 2em;
            margin-bottom: 0.8em;
        }}
        
        h3 {{
            font-family: 'Inter', sans-serif;
            font-size: 1.1rem;
            font-weight: 500;
            color: #24243e;
            margin-top: 1.5em;
            margin-bottom: 0.5em;
        }}
        
        p {{
            margin-bottom: 1em;
            text-align: justify;
        }}
        
        em {{ color: #667eea; }}
        
        strong {{ color: #0f0c29; }}
        
        a {{
            color: #667eea;
            text-decoration: none;
            border-bottom: 1px solid #667eea40;
        }}
        
        a:hover {{ border-bottom-color: #667eea; }}
        
        hr {{
            border: none;
            height: 1px;
            background: linear-gradient(90deg, transparent, #667eea40, transparent);
            margin: 2em 0;
        }}
        
        blockquote {{
            border-left: 4px solid #667eea;
            padding-left: 1em;
            margin: 1em 0;
            color: #555;
            font-style: italic;
        }}
        
        code {{
            background: #f0f0f5;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.9em;
        }}
        
        ol, ul {{
            margin-left: 1.5em;
            margin-bottom: 1em;
        }}
        
        li {{ margin-bottom: 0.3em; }}
        
        .footer {{
            margin-top: 3em;
            padding-top: 1em;
            border-top: 1px solid #eee;
            font-size: 0.85em;
            color: #888;
            text-align: center;
        }}
        
        @media print {{
            body {{ max-width: 100%; padding: 20px; }}
            h1 {{ font-size: 1.6rem; }}
            h2 {{ font-size: 1.2rem; }}
        }}
    </style>
</head>
<body>
    {body}
    <div class="footer">
        <p>Generated by <strong>Yukti Research AI</strong> &mdash; Autonomous Academic Research System</p>
        <p>{datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
    </div>
</body>
</html>"""
        return html
    
    def _simple_md_to_html(self, text: str) -> str:
        """Simple markdown to HTML conversion."""
        import re
        
        # Headers
        text = re.sub(r'^### (.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
        text = re.sub(r'^## (.+)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
        text = re.sub(r'^# (.+)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
        
        # Bold and italic
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        
        # Links
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
        
        # Horizontal rule
        text = re.sub(r'^---$', '<hr>', text, flags=re.MULTILINE)
        
        # Paragraphs
        paragraphs = text.split('\n\n')
        result = []
        for p in paragraphs:
            p = p.strip()
            if p and not p.startswith('<h') and not p.startswith('<hr'):
                result.append(f'<p>{p}</p>')
            else:
                result.append(p)
        
        return '\n'.join(result)
