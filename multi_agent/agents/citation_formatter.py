"""
Citation Formatter Agent
========================

Formats citations in various academic styles.
Supports: APA 7th, MLA 9th, Chicago 17th, IEEE, Harvard, Vancouver.

This agent ONLY formats - it does NOT store citations.
Citation Memory Agent handles storage.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from enum import Enum

from .base import BaseAgent, AgentConfig, AgentResponse


class CitationStyle(Enum):
    """Supported citation styles."""
    APA = "apa"
    MLA = "mla"
    CHICAGO = "chicago"
    IEEE = "ieee"
    HARVARD = "harvard"
    VANCOUVER = "vancouver"


@dataclass
class FormattedCitation:
    """A formatted citation result."""
    style: str
    in_text: str
    reference: str
    footnote: Optional[str] = None


class CitationFormatterAgent(BaseAgent):
    """
    Agent for formatting citations in various academic styles.
    
    Supports:
    - APA 7th Edition
    - MLA 9th Edition
    - Chicago 17th Edition (Notes-Bibliography)
    - IEEE
    - Harvard
    - Vancouver
    """
    
    def __init__(self, websocket=None, stream_output=None, headers=None):
        config = AgentConfig(name="CitationFormatter", description="Citation formatting")
        super().__init__(websocket, stream_output, headers, config)
    
    def format_apa(self, citation: Dict[str, Any]) -> FormattedCitation:
        """Format citation in APA 7th edition style."""
        authors = citation.get("authors", [])
        year = citation.get("year", "n.d.")
        title = citation.get("title", "")
        source = citation.get("source", "")
        doi = citation.get("doi", "")
        url = citation.get("url", "")
        
        # Format authors for reference
        if len(authors) == 1:
            author_ref = self._format_author_apa(authors[0])
            author_intext = self._get_last_name(authors[0])
        elif len(authors) == 2:
            author_ref = f"{self._format_author_apa(authors[0])} & {self._format_author_apa(authors[1])}"
            author_intext = f"{self._get_last_name(authors[0])} & {self._get_last_name(authors[1])}"
        elif len(authors) >= 3:
            author_ref = ", ".join(self._format_author_apa(a) for a in authors[:-1])
            author_ref += f", & {self._format_author_apa(authors[-1])}"
            author_intext = f"{self._get_last_name(authors[0])} et al."
        else:
            author_ref = "Unknown"
            author_intext = "Unknown"
        
        # Build reference
        reference = f"{author_ref} ({year}). {title}."
        if source:
            reference += f" *{source}*."
        if doi:
            reference += f" https://doi.org/{doi}"
        elif url:
            reference += f" {url}"
        
        in_text = f"({author_intext}, {year})"
        
        return FormattedCitation(style="apa", in_text=in_text, reference=reference)
    
    def format_mla(self, citation: Dict[str, Any]) -> FormattedCitation:
        """Format citation in MLA 9th edition style."""
        authors = citation.get("authors", [])
        year = citation.get("year", "")
        title = citation.get("title", "")
        source = citation.get("source", "")
        
        # MLA author format: Last, First.
        if len(authors) == 1:
            author_ref = self._format_author_mla(authors[0])
            author_intext = self._get_last_name(authors[0])
        elif len(authors) == 2:
            author_ref = f"{self._format_author_mla(authors[0])}, and {authors[1]}"
            author_intext = f"{self._get_last_name(authors[0])} and {self._get_last_name(authors[1])}"
        elif len(authors) >= 3:
            author_ref = f"{self._format_author_mla(authors[0])}, et al."
            author_intext = f"{self._get_last_name(authors[0])} et al."
        else:
            author_ref = "Unknown"
            author_intext = "Unknown"
        
        reference = f'{author_ref} "{title}."'
        if source:
            reference += f" *{source}*,"
        reference += f" {year}."
        
        in_text = f"({author_intext})"
        
        return FormattedCitation(style="mla", in_text=in_text, reference=reference)
    
    def format_chicago(self, citation: Dict[str, Any]) -> FormattedCitation:
        """Format citation in Chicago 17th edition (Notes-Bibliography) style."""
        authors = citation.get("authors", [])
        year = citation.get("year", "")
        title = citation.get("title", "")
        source = citation.get("source", "")
        
        # Chicago author format
        if len(authors) == 1:
            author_ref = self._format_author_chicago(authors[0])
            author_note = authors[0]
        elif len(authors) == 2:
            author_ref = f"{self._format_author_chicago(authors[0])}, and {authors[1]}"
            author_note = f"{authors[0]} and {authors[1]}"
        elif len(authors) >= 3:
            author_ref = f"{self._format_author_chicago(authors[0])}, et al."
            author_note = f"{authors[0]} et al."
        else:
            author_ref = "Unknown"
            author_note = "Unknown"
        
        reference = f'{author_ref}. "{title}."'
        if source:
            reference += f" *{source}*"
        reference += f" ({year})."
        
        footnote = f'{author_note}, "{title},"'
        if source:
            footnote += f" *{source}*"
        footnote += f" ({year})."
        
        in_text = f"({self._get_last_name(authors[0]) if authors else 'Unknown'} {year})"
        
        return FormattedCitation(style="chicago", in_text=in_text, reference=reference, footnote=footnote)
    
    def format_ieee(self, citation: Dict[str, Any], number: int = 1) -> FormattedCitation:
        """Format citation in IEEE style."""
        authors = citation.get("authors", [])
        year = citation.get("year", "")
        title = citation.get("title", "")
        source = citation.get("source", "")
        
        # IEEE: First Initial. Last
        author_parts = []
        for author in authors[:6]:  # IEEE limits to 6 authors
            parts = author.split()
            if len(parts) >= 2:
                initials = "".join(p[0] + "." for p in parts[:-1])
                author_parts.append(f"{initials} {parts[-1]}")
            else:
                author_parts.append(author)
        
        if len(authors) > 6:
            author_ref = ", ".join(author_parts) + ", et al."
        else:
            author_ref = ", ".join(author_parts[:-1]) + " and " + author_parts[-1] if len(author_parts) > 1 else author_parts[0] if author_parts else "Unknown"
        
        reference = f'[{number}] {author_ref}, "{title},"'
        if source:
            reference += f" *{source}*,"
        reference += f" {year}."
        
        in_text = f"[{number}]"
        
        return FormattedCitation(style="ieee", in_text=in_text, reference=reference)
    
    def format_harvard(self, citation: Dict[str, Any]) -> FormattedCitation:
        """Format citation in Harvard style."""
        authors = citation.get("authors", [])
        year = citation.get("year", "n.d.")
        title = citation.get("title", "")
        source = citation.get("source", "")
        
        # Harvard is similar to APA
        if len(authors) == 1:
            author_ref = self._get_last_name(authors[0])
            author_intext = author_ref
        elif len(authors) == 2:
            author_ref = f"{self._get_last_name(authors[0])} and {self._get_last_name(authors[1])}"
            author_intext = author_ref
        elif len(authors) >= 3:
            author_ref = f"{self._get_last_name(authors[0])} et al."
            author_intext = author_ref
        else:
            author_ref = "Unknown"
            author_intext = "Unknown"
        
        reference = f"{author_ref} ({year}) '{title}',"
        if source:
            reference += f" *{source}*."
        
        in_text = f"({author_intext}, {year})"
        
        return FormattedCitation(style="harvard", in_text=in_text, reference=reference)
    
    def format_vancouver(self, citation: Dict[str, Any], number: int = 1) -> FormattedCitation:
        """Format citation in Vancouver style."""
        authors = citation.get("authors", [])
        year = citation.get("year", "")
        title = citation.get("title", "")
        source = citation.get("source", "")
        
        # Vancouver: Last FM (no periods, no commas between initials)
        author_parts = []
        for author in authors[:6]:
            parts = author.split()
            if len(parts) >= 2:
                initials = "".join(p[0] for p in parts[:-1])
                author_parts.append(f"{parts[-1]} {initials}")
            else:
                author_parts.append(author)
        
        if len(authors) > 6:
            author_ref = ", ".join(author_parts) + ", et al"
        else:
            author_ref = ", ".join(author_parts)
        
        reference = f"{number}. {author_ref}. {title}."
        if source:
            reference += f" {source}."
        reference += f" {year}."
        
        in_text = f"({number})"
        
        return FormattedCitation(style="vancouver", in_text=in_text, reference=reference)
    
    def _format_author_apa(self, author: str) -> str:
        """Format author name for APA: Last, F. M."""
        parts = author.split()
        if len(parts) >= 2:
            initials = " ".join(p[0] + "." for p in parts[:-1])
            return f"{parts[-1]}, {initials}"
        return author
    
    def _format_author_mla(self, author: str) -> str:
        """Format author name for MLA: Last, First."""
        parts = author.split()
        if len(parts) >= 2:
            return f"{parts[-1]}, {' '.join(parts[:-1])}"
        return author
    
    def _format_author_chicago(self, author: str) -> str:
        """Format author name for Chicago: Last, First."""
        return self._format_author_mla(author)
    
    def _get_last_name(self, author: str) -> str:
        """Extract last name from full name."""
        parts = author.split()
        return parts[-1] if parts else author
    
    def format_citation(self, citation, style: str, number: int = 1) -> FormattedCitation:
        """Format a citation in the specified style.
        
        Args:
            citation: Either a dictionary or an object with citation fields
            style: Citation style (apa, mla, chicago, ieee, harvard, vancouver)
            number: Number for numbered styles (IEEE, Vancouver)
        
        Returns:
            FormattedCitation object
        """
        # Convert Citation object to dict if needed
        if hasattr(citation, 'to_dict'):
            citation = citation.to_dict()
        elif hasattr(citation, '__dict__') and not isinstance(citation, dict):
            citation = citation.__dict__
        
        style_lower = style.lower()
        
        formatters = {
            "apa": lambda: self.format_apa(citation),
            "mla": lambda: self.format_mla(citation),
            "chicago": lambda: self.format_chicago(citation),
            "ieee": lambda: self.format_ieee(citation, number),
            "harvard": lambda: self.format_harvard(citation),
            "vancouver": lambda: self.format_vancouver(citation, number),
        }
        
        if style_lower not in formatters:
            raise ValueError(f"Unsupported style: {style}. Supported: {list(formatters.keys())}")
        
        return formatters[style_lower]()
    
    def format_bibliography(self, citations: List[Dict[str, Any]], style: str) -> str:
        """Format multiple citations as a bibliography."""
        formatted = []
        for i, citation in enumerate(citations, 1):
            result = self.format_citation(citation, style, number=i)
            formatted.append(result.reference)
        
        return "\n\n".join(formatted)
    
    async def execute(self, operation: str, **kwargs) -> AgentResponse:
        """Execute citation formatting operations."""
        try:
            if operation == "format":
                citation = kwargs.get("citation", {})
                style = kwargs.get("style", "apa")
                number = kwargs.get("number", 1)
                result = self.format_citation(citation, style, number)
                return AgentResponse(success=True, data={
                    "style": result.style,
                    "in_text": result.in_text,
                    "reference": result.reference,
                    "footnote": result.footnote,
                })
            
            elif operation == "bibliography":
                citations = kwargs.get("citations", [])
                style = kwargs.get("style", "apa")
                result = self.format_bibliography(citations, style)
                return AgentResponse(success=True, data=result)
            
            elif operation == "styles":
                return AgentResponse(success=True, data=[s.value for s in CitationStyle])
            
            else:
                return AgentResponse(success=False, error=f"Unknown operation: {operation}")
                
        except Exception as e:
            return AgentResponse(success=False, error=str(e))
