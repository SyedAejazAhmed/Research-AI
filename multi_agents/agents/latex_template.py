"""
LaTeX Template Agent
====================

Manages LaTeX templates for academic documents.
Provides templates for: articles, reports, theses, presentations.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from enum import Enum
from pathlib import Path
import os

from .base import BaseAgent, AgentConfig, AgentResponse


class TemplateType(Enum):
    """Available LaTeX template types."""
    ARTICLE = "article"
    REPORT = "report"
    THESIS = "thesis"
    PRESENTATION = "presentation"
    LETTER = "letter"
    BOOK = "book"


@dataclass
class LaTeXTemplate:
    """A LaTeX template."""
    name: str
    template_type: TemplateType
    content: str
    description: str = ""
    required_packages: List[str] = None
    variables: List[str] = None
    
    def __post_init__(self):
        if self.required_packages is None:
            self.required_packages = []
        if self.variables is None:
            # Auto-extract variables from content
            import re
            self.variables = re.findall(r'\$\{(\w+)\}', self.content)


class LaTeXTemplateAgent(BaseAgent):
    """
    Agent for managing LaTeX templates.
    
    Features:
    - Predefined academic templates
    - Custom template registration
    - Template variable substitution
    - Package dependency tracking
    """
    
    def __init__(self, templates_dir: str = "./templates", websocket=None, stream_output=None, headers=None):
        config = AgentConfig(name="LaTeXTemplate", description="LaTeX template management")
        super().__init__(websocket, stream_output, headers, config)
        self.templates_dir = Path(templates_dir)
        self.templates: Dict[str, LaTeXTemplate] = {}
        self._load_builtin_templates()
    
    def _load_builtin_templates(self) -> None:
        """Load built-in templates."""
        # Article template
        self.templates["article"] = LaTeXTemplate(
            name="article",
            template_type=TemplateType.ARTICLE,
            description="Standard academic article",
            required_packages=["amsmath", "graphicx", "hyperref", "natbib"],
            content=r"""\documentclass[12pt,a4paper]{article}

% Packages
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{amsmath,amssymb}
\usepackage{graphicx}
\usepackage{hyperref}
\usepackage{natbib}
\usepackage{geometry}
\geometry{margin=1in}

% Title
\title{${title}}
\author{${author}}
\date{${date}}

\begin{document}

\maketitle

\begin{abstract}
${abstract}
\end{abstract}

\section{Introduction}
${introduction}

\section{Methods}
${methods}

\section{Results}
${results}

\section{Discussion}
${discussion}

\section{Conclusion}
${conclusion}

\bibliographystyle{plainnat}
\bibliography{${bibliography}}

\end{document}
"""
        )
        
        # Research report template
        self.templates["report"] = LaTeXTemplate(
            name="report",
            template_type=TemplateType.REPORT,
            description="Research report with chapters",
            required_packages=["amsmath", "graphicx", "hyperref", "natbib", "fancyhdr"],
            content=r"""\documentclass[12pt,a4paper]{report}

% Packages
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{amsmath,amssymb}
\usepackage{graphicx}
\usepackage{hyperref}
\usepackage{natbib}
\usepackage{geometry}
\usepackage{fancyhdr}
\geometry{margin=1in}

% Header/Footer
\pagestyle{fancy}
\fancyhf{}
\rhead{${short_title}}
\lhead{\leftmark}
\cfoot{\thepage}

% Title
\title{${title}}
\author{${author}}
\date{${date}}

\begin{document}

\maketitle

\begin{abstract}
${abstract}
\end{abstract}

\tableofcontents
\newpage

\chapter{Introduction}
${introduction}

\chapter{Literature Review}
${literature_review}

\chapter{Methodology}
${methodology}

\chapter{Results}
${results}

\chapter{Discussion}
${discussion}

\chapter{Conclusion}
${conclusion}

\bibliographystyle{plainnat}
\bibliography{${bibliography}}

\end{document}
"""
        )
        
        # Thesis template
        self.templates["thesis"] = LaTeXTemplate(
            name="thesis",
            template_type=TemplateType.THESIS,
            description="Thesis/Dissertation template",
            required_packages=["amsmath", "graphicx", "hyperref", "natbib", "fancyhdr", "setspace"],
            content=r"""\documentclass[12pt,a4paper,twoside]{report}

% Packages
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{amsmath,amssymb}
\usepackage{graphicx}
\usepackage{hyperref}
\usepackage{natbib}
\usepackage{geometry}
\usepackage{fancyhdr}
\usepackage{setspace}
\geometry{margin=1.5in}
\doublespacing

% Title Page
\title{${title}}
\author{${author}}
\date{${date}}

\begin{document}

% Title Page
\begin{titlepage}
\centering
\vspace*{2cm}
{\LARGE\bfseries ${title}\par}
\vspace{2cm}
{\Large ${author}\par}
\vspace{1cm}
{\large A thesis submitted in partial fulfillment\\of the requirements for the degree of\\${degree}\par}
\vspace{2cm}
{\large ${institution}\par}
{\large ${department}\par}
\vspace{2cm}
{\large ${date}\par}
\end{titlepage}

% Abstract
\chapter*{Abstract}
\addcontentsline{toc}{chapter}{Abstract}
${abstract}

% Acknowledgments
\chapter*{Acknowledgments}
\addcontentsline{toc}{chapter}{Acknowledgments}
${acknowledgments}

\tableofcontents
\listoffigures
\listoftables

\chapter{Introduction}
${introduction}

\chapter{Literature Review}
${literature_review}

\chapter{Methodology}
${methodology}

\chapter{Results}
${results}

\chapter{Discussion}
${discussion}

\chapter{Conclusion}
${conclusion}

\appendix
\chapter{Appendix}
${appendix}

\bibliographystyle{plainnat}
\bibliography{${bibliography}}

\end{document}
"""
        )
        
        # Presentation (Beamer) template
        self.templates["presentation"] = LaTeXTemplate(
            name="presentation",
            template_type=TemplateType.PRESENTATION,
            description="Beamer presentation",
            required_packages=["beamer", "graphicx", "hyperref"],
            content=r"""\documentclass{beamer}

\usetheme{${theme}}
\usecolortheme{${color_theme}}

\title{${title}}
\author{${author}}
\institute{${institution}}
\date{${date}}

\begin{document}

\begin{frame}
\titlepage
\end{frame}

\begin{frame}{Outline}
\tableofcontents
\end{frame}

\section{Introduction}
\begin{frame}{Introduction}
${introduction}
\end{frame}

\section{Main Content}
${slides}

\section{Conclusion}
\begin{frame}{Conclusion}
${conclusion}
\end{frame}

\begin{frame}{References}
${references}
\end{frame}

\begin{frame}
\centering
\Huge Thank You!\\
\vspace{1cm}
\large Questions?
\end{frame}

\end{document}
"""
        )
    
    def get_template(self, template_type) -> Optional[LaTeXTemplate]:
        """
        Get a template by name or type.
        
        Args:
            template_type: Either a TemplateType enum or a string name
            
        Returns:
            LaTeXTemplate or None
        """
        if isinstance(template_type, TemplateType):
            name = template_type.value
        else:
            name = str(template_type)
        return self.templates.get(name)
    
    def get_template_by_name(self, name: str) -> Optional[LaTeXTemplate]:
        """Get a template by name (alias for get_template)."""
        return self.get_template(name)
    
    def list_templates(self) -> List[LaTeXTemplate]:
        """List all available templates."""
        return list(self.templates.values())
    
    def register_template(self, template: LaTeXTemplate) -> bool:
        """Register a custom template."""
        self.templates[template.name] = template
        return True
    
    def fill_template(self, template_name, variables: Dict[str, str]) -> str:
        """Fill a template with variables."""
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Template not found: {template_name}")
        
        content = template.content
        for key, value in variables.items():
            content = content.replace(f"${{{key}}}", value)
        
        return content
    
    def render_template(self, template_type, variables: Dict[str, str] = None, **kwargs) -> str:
        """
        Render a template with the provided variables.
        
        Args:
            template_type: Template type (TemplateType, string, or LaTeXTemplate)
            variables: Variable dictionary (optional, can pass as kwargs)
            **kwargs: Variable key-value pairs (merged with variables dict)
            
        Returns:
            Rendered LaTeX content
        """
        # Merge variables dict and kwargs
        all_vars = {}
        if variables:
            all_vars.update(variables)
        all_vars.update(kwargs)
        
        # Get template name
        if isinstance(template_type, LaTeXTemplate):
            template_name = template_type.name
        elif isinstance(template_type, TemplateType):
            template_name = template_type.value
        else:
            template_name = str(template_type)
        
        return self.fill_template(template_name, all_vars)
    
    def create_custom_template(
        self, 
        name: str, 
        template_type: TemplateType, 
        content: str,
        description: str = "",
        required_packages: List[str] = None
    ) -> LaTeXTemplate:
        """
        Create and register a custom template.
        
        Args:
            name: Template name
            template_type: Template type
            content: LaTeX content with ${variable} placeholders
            description: Template description
            required_packages: List of required LaTeX packages
            
        Returns:
            The created LaTeXTemplate
        """
        template = LaTeXTemplate(
            name=name,
            template_type=template_type,
            content=content,
            description=description,
            required_packages=required_packages or []
        )
        self.register_template(template)
        return template
    
    def create_template(
        self, 
        name: str, 
        content: str,
        template_type: TemplateType = TemplateType.ARTICLE,
        description: str = "",
    ) -> LaTeXTemplate:
        """
        Create and register a custom template (alias for create_custom_template).
        
        Args:
            name: Template name
            content: LaTeX content with ${variable} placeholders
            template_type: Template type (default: ARTICLE)
            description: Template description
            
        Returns:
            The created LaTeXTemplate
        """
        return self.create_custom_template(
            name=name,
            template_type=template_type,
            content=content,
            description=description,
        )
    
    def get_required_variables(self, template_name: str) -> List[str]:
        """Get list of required variables for a template."""
        template = self.templates.get(template_name)
        if not template:
            return []
        
        import re
        return re.findall(r'\$\{(\w+)\}', template.content)
    
    async def execute(self, operation: str, **kwargs) -> AgentResponse:
        """Execute template operations."""
        try:
            if operation == "list":
                return AgentResponse(success=True, data=self.list_templates())
            
            elif operation == "get":
                template = self.get_template(kwargs.get("name", ""))
                if template:
                    return AgentResponse(success=True, data={
                        "name": template.name,
                        "type": template.template_type.value,
                        "content": template.content,
                        "packages": template.required_packages,
                    })
                return AgentResponse(success=False, error="Template not found")
            
            elif operation == "fill":
                name = kwargs.get("name", "")
                variables = kwargs.get("variables", {})
                content = self.fill_template(name, variables)
                return AgentResponse(success=True, data=content)
            
            elif operation == "variables":
                name = kwargs.get("name", "")
                variables = self.get_required_variables(name)
                return AgentResponse(success=True, data=variables)
            
            elif operation == "register":
                template = LaTeXTemplate(**kwargs)
                self.register_template(template)
                return AgentResponse(success=True, data={"registered": template.name})
            
            else:
                return AgentResponse(success=False, error=f"Unknown operation: {operation}")
                
        except Exception as e:
            return AgentResponse(success=False, error=str(e))
