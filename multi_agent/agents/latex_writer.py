"""
LaTeX Writer Agent
==================

Writes LaTeX documents from research content.
Handles section generation, citation insertion, figure/table placement.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from pathlib import Path
import re

from .base import BaseAgent, AgentConfig, AgentResponse

# Lazy import – researcher may not be installed in all environments
def _call_model_lazy():
    try:
        from .utils.llms import call_model as _cm
        return _cm
    except Exception:  # noqa: BLE001
        return None


@dataclass
class LaTeXSection:
    """A section of a LaTeX document."""
    title: str
    content: str
    level: int = 1  # 1=section, 2=subsection, 3=subsubsection
    label: Optional[str] = None
    
    def to_latex(self) -> str:
        """Render section to LaTeX."""
        commands = {1: 'section', 2: 'subsection', 3: 'subsubsection'}
        cmd = commands.get(self.level, 'section')
        safe_title = self.title
        for src, dst in [("&", r"\&"), ("%", r"\%"), ("#", r"\#"), ("_", r"\_")]:
            safe_title = safe_title.replace(src, dst)
        label_str = ""
        if self.label:
            label_str = f"\\label{{{self.label}}}"
        else:
            import re
            safe_label = re.sub(r'[^a-zA-Z0-9]', '', self.title.lower())
            label_str = f"\\label{{sec:{safe_label}}}"
        
        return f"\\{cmd}{{{safe_title}}}{label_str}\n\n{self.content}\n"


@dataclass
class LaTeXDocument:
    """A complete LaTeX document."""
    title: str
    author: str
    abstract: str = ""
    sections: List[LaTeXSection] = None
    bibliography: List[str] = None
    preamble: str = ""
    document_class: str = "article"
    
    def __post_init__(self):
        if self.sections is None:
            self.sections = []
        if self.bibliography is None:
            self.bibliography = []
    
    def add_section(self, section: LaTeXSection) -> None:
        """Add a section to the document."""
        self.sections.append(section)
    
    def to_latex(self) -> str:
        """Render the complete document to LaTeX."""
        preamble = self.preamble if self.preamble else f"""\\documentclass[12pt,a4paper]{{{self.document_class}}}

\\usepackage[utf8]{{inputenc}}
\\usepackage[T1]{{fontenc}}
\\usepackage{{amsmath,amssymb}}
\\usepackage{{graphicx}}
\\usepackage{{hyperref}}
\\usepackage{{natbib}}
\\usepackage{{geometry}}
\\geometry{{margin=1in}}
"""
        
        abstract_section = ""
        if self.abstract:
            abstract_section = f"""
\\begin{{abstract}}
{self.abstract}
\\end{{abstract}}
"""
        
        sections_content = "\n".join(s.to_latex() for s in self.sections)
        
        return f"""{preamble}
\\title{{{self.title}}}
\\author{{{self.author}}}
\\date{{\\today}}

\\begin{{document}}

\\maketitle
{abstract_section}
{sections_content}

\\end{{document}}
"""


class LaTeXWriterAgent(BaseAgent):
    """
    Agent for writing LaTeX documents.
    
    Features:
    - Convert markdown/text to LaTeX
    - Insert citations properly
    - Generate section structure
    - Handle figures and tables
    - Math equation formatting
    """
    
    def __init__(self, websocket=None, stream_output=None, headers=None):
        config = AgentConfig(name="LaTeXWriter", description="LaTeX document writing")
        super().__init__(websocket, stream_output, headers, config)
    
    def markdown_to_latex(self, markdown: str) -> str:
        """Convert markdown text to LaTeX."""
        latex = markdown
        
        # Headers
        latex = re.sub(r'^### (.+)$', r'\\subsubsection{\1}', latex, flags=re.MULTILINE)
        latex = re.sub(r'^## (.+)$', r'\\subsection{\1}', latex, flags=re.MULTILINE)
        latex = re.sub(r'^# (.+)$', r'\\section{\1}', latex, flags=re.MULTILINE)
        
        # Bold and italic
        latex = re.sub(r'\*\*\*(.+?)\*\*\*', r'\\textbf{\\textit{\1}}', latex)
        latex = re.sub(r'\*\*(.+?)\*\*', r'\\textbf{\1}', latex)
        latex = re.sub(r'\*(.+?)\*', r'\\textit{\1}', latex)
        latex = re.sub(r'__(.+?)__', r'\\textbf{\1}', latex)
        # Do not use underscore-based italics because it corrupts DOIs/URLs like 10.1007/..._47
        
        # Code
        latex = re.sub(r'```(\w*)\n(.*?)```', r'\\begin{verbatim}\n\2\\end{verbatim}', latex, flags=re.DOTALL)
        latex = re.sub(r'`(.+?)`', r'\\texttt{\1}', latex)
        
        # Lists
        lines = latex.split('\n')
        in_itemize = False
        in_enumerate = False
        result = []
        
        for line in lines:
            stripped = line.strip()
            
            # Unordered list
            if stripped.startswith('- ') or stripped.startswith('* '):
                if not in_itemize:
                    result.append('\\begin{itemize}')
                    in_itemize = True
                result.append('  \\item ' + stripped[2:])
            # Ordered list
            elif re.match(r'^\d+\. ', stripped):
                if not in_enumerate:
                    result.append('\\begin{enumerate}')
                    in_enumerate = True
                result.append('  \\item ' + re.sub(r'^\d+\. ', '', stripped))
            else:
                if in_itemize:
                    result.append('\\end{itemize}')
                    in_itemize = False
                if in_enumerate:
                    result.append('\\end{enumerate}')
                    in_enumerate = False
                result.append(line)
        
        if in_itemize:
            result.append('\\end{itemize}')
        if in_enumerate:
            result.append('\\end{enumerate}')
        
        latex = '\n'.join(result)
        
        # Links
        latex = re.sub(r'\[(.+?)\]\((.+?)\)', r'\\href{\2}{\1}', latex)
        
        # Images (basic conversion)
        latex = re.sub(
            r'!\[(.+?)\]\((.+?)\)',
            r'\\begin{figure}[h]\n\\centering\n\\includegraphics[width=0.8\\textwidth]{\2}\n\\caption{\1}\n\\end{figure}',
            latex
        )
        
        # Escape special characters (that aren't already LaTeX commands)
        # Be careful not to escape existing LaTeX
        for char in ['%', '&', '#', '_']:
            latex = re.sub(r'(?<!\\)' + re.escape(char), '\\' + char, latex)
        
        return latex
    
    def create_section(self, title: str, content: str, level: int = 1, label: str = None) -> LaTeXSection:
        """Create a LaTeX section."""
        if label is None:
            label = "sec:" + re.sub(r'[^a-zA-Z0-9]', '', title.lower())
        
        return LaTeXSection(
            title=title,
            content=content,
            level=level,
            label=label
        )
    
    def create_section_latex(self, title: str, content: str, level: int = 1) -> str:
        """Create a LaTeX section as a string."""
        section = self.create_section(title, content, level)
        return section.to_latex()
    
    def create_document(
        self,
        title: str,
        author: str,
        content: str = "",
        abstract: str = "",
        document_class: str = "article",
        sections: List[LaTeXSection] = None,
    ) -> LaTeXDocument:
        """
        Create a LaTeX document.
        
        Args:
            title: Document title
            author: Document author
            content: Main content (will be added as a section if provided)
            abstract: Document abstract
            document_class: LaTeX document class
            sections: List of sections to include
            
        Returns:
            LaTeXDocument object
        """
        doc = LaTeXDocument(
            title=title,
            author=author,
            abstract=abstract,
            document_class=document_class,
            sections=sections or [],
        )
        
        # If content is provided but no sections, add content as introduction
        if content and not doc.sections:
            doc.add_section(self.create_section("Content", content))
        
        return doc
    
    def create_figure(self, path: str, caption: str, label: str, width: str = "0.8\\textwidth") -> str:
        """Create a LaTeX figure."""
        return f"""\\begin{{figure}}[htbp]
\\centering
\\includegraphics[width={width}]{{{path}}}
\\caption{{{caption}}}
\\label{{fig:{label}}}
\\end{{figure}}
"""
    
    def create_table(
        self,
        data: List[List[str]],
        caption: str = None,
        label: str = None,
        alignment: str = None,
        headers: List[str] = None,
        rows: List[List[str]] = None,
    ) -> str:
        """
        Create a LaTeX table.
        
        Args:
            data: 2D list where first row is headers, rest are data rows
            caption: Table caption
            label: Table label
            alignment: Column alignment (e.g., "lcc" or "c|c|c")
            headers: Optional explicit headers (legacy support)
            rows: Optional explicit rows (legacy support)
            
        Returns:
            LaTeX table string
        """
        # Support both old API (headers, rows) and new API (data)
        if headers is not None and rows is not None:
            header_row = headers
            data_rows = rows
        elif data:
            header_row = data[0] if data else []
            data_rows = data[1:] if len(data) > 1 else []
        else:
            header_row = []
            data_rows = []
        
        num_cols = len(header_row) if header_row else (len(data_rows[0]) if data_rows else 0)
        
        # Default alignment - only add separators if not provided
        if alignment is None:
            alignment = '|' + '|'.join(['c'] * num_cols) + '|'
        # If alignment provided, use it as-is (user controls separators)
        
        table = f"""\\begin{{table}}[htbp]
\\centering
"""
        if caption:
            table += f"\\caption{{{caption}}}\n"
        if label:
            if not label.startswith("tab:"):
                label = f"tab:{label}"
            table += f"\\label{{{label}}}\n"
        
        table += f"""\\begin{{tabular}}{{{alignment}}}
\\hline
{' & '.join(header_row)} \\\\
\\hline
"""
        for row in data_rows:
            table += ' & '.join(row) + ' \\\\\n'
        
        table += """\\hline
\\end{tabular}
\\end{table}
"""
        return table
    
    def create_equation(
        self,
        equation: str,
        label: Optional[str] = None,
        numbered: bool = True,
        inline: bool = False,
    ) -> str:
        """
        Create a LaTeX equation.
        
        Args:
            equation: The mathematical expression
            label: Optional label for referencing
            numbered: Whether to number the equation
            inline: If True, create inline math ($...$)
            
        Returns:
            LaTeX equation string
        """
        if inline:
            return f"${equation}$"
        
        if numbered and label:
            return f"""\\begin{{equation}}
\\label{{eq:{label}}}
{equation}
\\end{{equation}}
"""
        elif numbered:
            return f"""\\begin{{equation}}
{equation}
\\end{{equation}}
"""
        else:
            return f"""\\[
{equation}
\\]
"""
    
    def insert_citation(self, key: str, style: str = "cite") -> str:
        """Insert a citation command."""
        styles = {
            "cite": f"\\cite{{{key}}}",
            "citep": f"\\citep{{{key}}}",  # natbib parenthetical
            "citet": f"\\citet{{{key}}}",  # natbib textual
            "footcite": f"\\footcite{{{key}}}",  # biblatex footnote
        }
        return styles.get(style, f"\\cite{{{key}}}")
    
    def create_bibliography_entry(self, citation: Dict[str, Any]) -> str:
        """Create a BibTeX entry from citation data."""
        key = citation.get("citation_key", "unknown")
        authors = " and ".join(citation.get("authors", []))
        
        entry_type = "article"
        source = citation.get("source", "").lower()
        if "conference" in source or "proceedings" in source:
            entry_type = "inproceedings"
        elif "book" in source:
            entry_type = "book"
        
        entry = f"@{entry_type}{{{key},\n"
        entry += f"  author = {{{authors}}},\n"
        entry += f"  title = {{{citation.get('title', '')}}},\n"
        entry += f"  year = {{{citation.get('year', '')}}},\n"
        
        if citation.get("source"):
            if entry_type == "article":
                entry += f"  journal = {{{citation.get('source')}}},\n"
            else:
                entry += f"  booktitle = {{{citation.get('source')}}},\n"
        
        if citation.get("doi"):
            entry += f"  doi = {{{citation.get('doi')}}},\n"
        if citation.get("url"):
            entry += f"  url = {{{citation.get('url')}}},\n"
        
        entry += "}\n"
        return entry
    
    def assemble_document(self, doc: LaTeXDocument) -> str:
        """Assemble a complete LaTeX document."""
        if self._is_ieee_document_class(doc.document_class):
            return self._assemble_ieee_document(doc)

        latex = f"\\documentclass[12pt,a4paper]{{{doc.document_class}}}\n\n"

        # Standard preamble
        latex += """% Packages
\\usepackage[utf8]{inputenc}
\\usepackage[T1]{fontenc}
\\usepackage{amsmath,amssymb}
\\usepackage{graphicx}
\\usepackage{hyperref}
\\usepackage{natbib}
\\usepackage{geometry}
\\geometry{margin=1in}

"""

        if doc.preamble:
            latex += f"% Custom preamble\n{doc.preamble}\n\n"

        # Title info
        latex += f"\\title{{{doc.title}}}\n"
        latex += f"\\author{{{doc.author}}}\n"
        latex += "\\date{\\today}\n\n"

        # Document body
        latex += "\\begin{document}\n\n"
        latex += "\\maketitle\n\n"

        if doc.abstract:
            latex += f"\\begin{{abstract}}\n{doc.abstract}\n\\end{{abstract}}\n\n"

        # Sections
        for section in doc.sections:
            latex += section.to_latex()
            latex += "\n"

        # Bibliography
        if doc.bibliography:
            latex += "\\bibliographystyle{plainnat}\n"
            latex += "\\bibliography{references}\n\n"

        latex += "\\end{document}\n"

        return latex

    @staticmethod
    def _is_ieee_document_class(document_class: str) -> bool:
        """Return True when the requested template is an IEEE variant."""
        normalized = (document_class or "").strip().lower()
        return normalized in {"ieee", "ieeetran", "ieee-tran", "ieee_tran"}

    def _assemble_ieee_document(self, doc: LaTeXDocument) -> str:
        """Assemble a document using IEEEtran conference format."""
        latex = """\\documentclass[conference]{IEEEtran}
\\IEEEoverridecommandlockouts

% IEEE packages
\\usepackage[utf8]{inputenc}
\\usepackage[T1]{fontenc}
\\usepackage{cite}
\\usepackage{amsmath,amssymb,amsfonts}
\\usepackage{algorithmic}
\\usepackage{graphicx}
\\usepackage{textcomp}
\\usepackage{xcolor}
\\usepackage{hyperref}
\\usepackage{url}

"""

        if doc.preamble:
            latex += f"% Custom preamble\n{doc.preamble}\n\n"

        latex += f"\\title{{{doc.title}}}\n"
        latex += f"\\author{{{doc.author}}}\n\n"
        latex += "\\begin{document}\n\n"
        latex += "\\maketitle\n\n"

        if doc.abstract:
            latex += f"\\begin{{abstract}}\n{doc.abstract}\n\\end{{abstract}}\n\n"

        latex += "\\begin{IEEEkeywords}\n"
        latex += "Artificial Intelligence, Academic Writing, IEEE Format\n"
        latex += "\\end{IEEEkeywords}\n\n"

        for section in doc.sections:
            latex += section.to_latex()
            latex += "\n"

        if doc.bibliography:
            latex += "\\bibliographystyle{IEEEtran}\n"
            latex += "\\bibliography{references}\n\n"

        latex += "\\end{document}\n"
        return latex
    
    async def write_from_research(self, research_data: Dict[str, Any], model: str = None) -> str:
        """Write a LaTeX document from research data using LLM."""
        # Build prompt for LLM
        prompt = [
            {
                "role": "system",
                "content": """You are an expert academic writer. Convert the research data into 
well-structured LaTeX content. Focus on clear, academic writing style.
Return ONLY the LaTeX content for the sections, not the full document structure."""
            },
            {
                "role": "user",
                "content": f"""Convert this research into LaTeX sections:

Title: {research_data.get('title', 'Research Report')}

Research Data:
{research_data.get('content', '')}

Generate LaTeX content for: Introduction, Literature Review, Methodology, Results, Discussion, Conclusion.
Use proper LaTeX formatting for citations, equations if any, and figures."""
            }
        ]
        
        if model:
            call_model = _call_model_lazy()
            if call_model:
                content = await call_model(prompt, model=model)
            else:
                content = self.markdown_to_latex(research_data.get('content', ''))
        else:
            # Return a basic structure if no model
            content = self.markdown_to_latex(research_data.get('content', ''))
        
        return content
    
    async def execute(self, operation: str, **kwargs) -> AgentResponse:
        """Execute LaTeX writing operations."""
        try:
            if operation == "markdown_to_latex":
                markdown = kwargs.get("markdown", "")
                latex = self.markdown_to_latex(markdown)
                return AgentResponse(success=True, data=latex)
            
            elif operation == "create_section":
                title = kwargs.get("title", "")
                content = kwargs.get("content", "")
                level = kwargs.get("level", 1)
                latex = self.create_section(title, content, level)
                return AgentResponse(success=True, data=latex)
            
            elif operation == "create_figure":
                latex = self.create_figure(
                    kwargs.get("path", ""),
                    kwargs.get("caption", ""),
                    kwargs.get("label", "fig"),
                    kwargs.get("width", "0.8\\textwidth")
                )
                return AgentResponse(success=True, data=latex)
            
            elif operation == "create_table":
                latex = self.create_table(
                    kwargs.get("headers", []),
                    kwargs.get("rows", []),
                    kwargs.get("caption", ""),
                    kwargs.get("label", "tab")
                )
                return AgentResponse(success=True, data=latex)
            
            elif operation == "create_equation":
                latex = self.create_equation(
                    kwargs.get("equation", ""),
                    kwargs.get("label"),
                    kwargs.get("numbered", True)
                )
                return AgentResponse(success=True, data=latex)
            
            elif operation == "assemble":
                doc = LaTeXDocument(**kwargs)
                latex = self.assemble_document(doc)
                return AgentResponse(success=True, data=latex)
            
            elif operation == "write_from_research":
                latex = await self.write_from_research(
                    kwargs.get("research_data", {}),
                    kwargs.get("model")
                )
                return AgentResponse(success=True, data=latex)
            
            elif operation == "bibtex_entry":
                entry = self.create_bibliography_entry(kwargs.get("citation", {}))
                return AgentResponse(success=True, data=entry)
            
            else:
                return AgentResponse(success=False, error=f"Unknown operation: {operation}")
                
        except Exception as e:
            return AgentResponse(success=False, error=str(e))
