"""
Citation Memory Agent
=====================

Stores and retrieves citations with search capabilities.
Handles DOI, arXiv ID, BibTeX, CSL JSON ingestion.
Maintains normalized and raw citation records.
"""

import json
import hashlib
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from datetime import datetime
import asyncio
import aiofiles
from pathlib import Path

from .base import BaseAgent, AgentConfig, AgentResponse
from .utils.views import print_agent_output


@dataclass
class Citation:
    """Represents a single citation."""
    id: str
    title: str
    authors: List[str]
    year: int
    source: str = None
    url: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    abstract: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    citation_key: Optional[str] = None
    bibtex_type: str = "article"
    raw_bibtex: Optional[str] = None
    raw_source: Optional[str] = None  # Original source format
    raw_data: Dict[str, Any] = field(default_factory=dict)  # Original raw data
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Citation":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def generate_citation_key(self) -> str:
        """Generate BibTeX-style citation key."""
        first_author = self.authors[0].split()[-1] if self.authors else "Unknown"
        first_author = ''.join(c for c in first_author if c.isalnum())
        year = str(self.year) if self.year else "XXXX"
        title_words = [w for w in self.title.split() if len(w) > 3]
        title_word = ''.join(c for c in (title_words[0] if title_words else "untitled") if c.isalnum())
        return f"{first_author}{year}{title_word}".lower()


class CitationMemoryAgent(BaseAgent):
    """
    Agent for storing and retrieving research citations.
    
    Features:
    - Add, update, delete citations
    - Search by title, author, keyword, year, DOI
    - Import/export BibTeX format
    - Duplicate detection via DOI/title matching
    - Normalized metadata storage
    """
    
    def __init__(self, storage_path: str = "./citations", websocket=None, stream_output=None, headers=None):
        config = AgentConfig(name="CitationMemory", description="Citation storage and retrieval")
        super().__init__(websocket, stream_output, headers, config)
        self.storage_path = Path(storage_path)
        self.citations: Dict[str, Citation] = {}
        self._index_by_author: Dict[str, Set[str]] = {}
        self._index_by_year: Dict[int, Set[str]] = {}
        self._index_by_keyword: Dict[str, Set[str]] = {}
        self._index_by_doi: Dict[str, str] = {}
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Load citations from storage."""
        if self._initialized:
            return True
        try:
            self.storage_path.mkdir(parents=True, exist_ok=True)
            citations_file = self.storage_path / "citations.json"
            if citations_file.exists():
                async with aiofiles.open(citations_file, "r") as f:
                    data = json.loads(await f.read())
                    for cit_data in data.get("citations", []):
                        citation = Citation.from_dict(cit_data)
                        self.citations[citation.id] = citation
                        self._update_indices(citation)
            self._initialized = True
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize: {e}")
            return False
    
    async def save(self) -> bool:
        """Save citations to storage."""
        try:
            citations_file = self.storage_path / "citations.json"
            data = {
                "version": "1.0",
                "updated_at": datetime.utcnow().isoformat(),
                "citations": [c.to_dict() for c in self.citations.values()],
            }
            async with aiofiles.open(citations_file, "w") as f:
                await f.write(json.dumps(data, indent=2))
            return True
        except Exception as e:
            self.logger.error(f"Failed to save: {e}")
            return False
    
    def _generate_id(self, citation: Citation) -> str:
        content = f"{citation.title}|{','.join(citation.authors)}|{citation.year}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _update_indices(self, citation: Citation) -> None:
        for author in citation.authors:
            self._index_by_author.setdefault(author.lower(), set()).add(citation.id)
        if citation.year:
            self._index_by_year.setdefault(citation.year, set()).add(citation.id)
        for kw in citation.keywords:
            self._index_by_keyword.setdefault(kw.lower(), set()).add(citation.id)
        if citation.doi:
            self._index_by_doi[citation.doi.lower()] = citation.id
    
    def _remove_from_indices(self, citation: Citation) -> None:
        for author in citation.authors:
            self._index_by_author.get(author.lower(), set()).discard(citation.id)
        if citation.year:
            self._index_by_year.get(citation.year, set()).discard(citation.id)
        for kw in citation.keywords:
            self._index_by_keyword.get(kw.lower(), set()).discard(citation.id)
        if citation.doi and citation.doi.lower() in self._index_by_doi:
            del self._index_by_doi[citation.doi.lower()]
    
    def add_citation(
        self,
        citation: Citation = None,
        *,
        title: str = None,
        authors: List[str] = None,
        year: int = None,
        **kwargs
    ) -> Citation:
        """
        Add a new citation.
        
        Can be called with either a Citation object or keyword arguments.
        
        Args:
            citation: A Citation object (optional)
            title: Citation title (if not passing Citation object)
            authors: List of authors (if not passing Citation object)
            year: Publication year (if not passing Citation object)
            **kwargs: Additional citation fields
            
        Returns:
            The added Citation object
        """
        # Create citation from kwargs if not provided
        if citation is None:
            if title is None:
                raise ValueError("Title is required")
            citation = Citation(
                id=kwargs.pop("id", None) or "",
                title=title,
                authors=authors or [],
                year=year,
                source=kwargs.pop("source", None),
                doi=kwargs.pop("doi", None),
                url=kwargs.pop("url", None),
                abstract=kwargs.pop("abstract", None),
                keywords=kwargs.pop("keywords", []),
                bibtex_type=kwargs.pop("bibtex_type", "article"),
                raw_data=kwargs.pop("raw_data", {}),
            )
        
        if not citation.id:
            citation.id = self._generate_id(citation)
        if not citation.citation_key:
            citation.citation_key = citation.generate_citation_key()
        
        # Check for duplicates by DOI
        if citation.doi and citation.doi.lower() in self._index_by_doi:
            raise ValueError(f"Duplicate DOI: {citation.doi}")
        
        if citation.id in self.citations:
            raise ValueError(f"Citation ID exists: {citation.id}")
        
        self.citations[citation.id] = citation
        self._update_indices(citation)
        
        # Return the citation object directly
        return citation
    
    async def add_citation_async(self, citation: Citation) -> AgentResponse:
        """Add a new citation (async version)."""
        if not self._initialized:
            await self.initialize()
        
        try:
            result = self.add_citation(citation=citation)
            await self.save()
            return AgentResponse(success=True, data=result.to_dict(), 
                               metadata={"total": len(self.citations)})
        except ValueError as e:
            return AgentResponse(success=False, error=str(e))
    
    async def get_citation(self, citation_id: str) -> AgentResponse:
        """Get citation by ID."""
        if not self._initialized:
            await self.initialize()
        citation = self.citations.get(citation_id)
        if citation:
            return AgentResponse(success=True, data=citation.to_dict())
        return AgentResponse(success=False, error=f"Not found: {citation_id}")
    
    async def get_by_doi(self, doi: str) -> AgentResponse:
        """Get citation by DOI."""
        if not self._initialized:
            await self.initialize()
        cit_id = self._index_by_doi.get(doi.lower())
        if cit_id:
            return await self.get_citation(cit_id)
        return AgentResponse(success=False, error=f"DOI not found: {doi}")
    
    async def search(self, query: str = None, author: str = None, year: int = None,
                    year_range: tuple = None, keywords: List[str] = None,
                    doi: str = None, limit: int = 50) -> AgentResponse:
        """Search citations with filters."""
        if not self._initialized:
            await self.initialize()
        
        results = set(self.citations.keys())
        
        if doi:
            cit_id = self._index_by_doi.get(doi.lower())
            results = {cit_id} if cit_id else set()
        
        if author:
            author_matches = set()
            for key, ids in self._index_by_author.items():
                if author.lower() in key:
                    author_matches.update(ids)
            results &= author_matches
        
        if year:
            results &= self._index_by_year.get(year, set())
        
        if year_range:
            year_matches = set()
            for y in range(year_range[0], year_range[1] + 1):
                year_matches.update(self._index_by_year.get(y, set()))
            results &= year_matches
        
        if keywords:
            for kw in keywords:
                kw_matches = set()
                for key, ids in self._index_by_keyword.items():
                    if kw.lower() in key:
                        kw_matches.update(ids)
                results &= kw_matches
        
        if query:
            query_lower = query.lower()
            text_matches = set()
            for cid in results:
                c = self.citations[cid]
                if query_lower in c.title.lower() or (c.abstract and query_lower in c.abstract.lower()):
                    text_matches.add(cid)
            results = text_matches
        
        citations = [self.citations[cid].to_dict() for cid in list(results)[:limit]]
        return AgentResponse(success=True, data=citations, 
                           metadata={"total": len(results), "returned": len(citations)})
    
    async def delete_citation(self, citation_id: str) -> AgentResponse:
        """Delete a citation."""
        if not self._initialized:
            await self.initialize()
        if citation_id not in self.citations:
            return AgentResponse(success=False, error=f"Not found: {citation_id}")
        
        self._remove_from_indices(self.citations[citation_id])
        del self.citations[citation_id]
        await self.save()
        return AgentResponse(success=True, data={"deleted": citation_id})
    
    async def import_bibtex(self, bibtex_content: str) -> AgentResponse:
        """Import citations from BibTeX."""
        if not self._initialized:
            await self.initialize()
        
        import re
        entries = []
        pattern = r'@(\w+)\s*\{\s*([^,]+)\s*,([^@]*)\}'
        
        for match in re.finditer(pattern, bibtex_content, re.DOTALL):
            entry_type, key, fields = match.groups()
            entry = {"_type": entry_type.lower(), "_key": key.strip(), "_raw": match.group(0)}
            for field_match in re.finditer(r'(\w+)\s*=\s*\{([^}]*)\}', fields):
                entry[field_match.group(1).lower()] = field_match.group(2).strip()
            entries.append(entry)
        
        imported, skipped = 0, 0
        for entry in entries:
            authors = [a.strip() for a in entry.get("author", "").strip("{}").split(" and ")]
            citation = Citation(
                id="",
                title=entry.get("title", "").strip("{}"),
                authors=authors,
                year=int(entry.get("year", 0)) if entry.get("year", "").isdigit() else 0,
                source=entry.get("journal", entry.get("booktitle", "")),
                doi=entry.get("doi"),
                url=entry.get("url"),
                abstract=entry.get("abstract"),
                citation_key=entry.get("_key"),
                raw_bibtex=entry.get("_raw"),
                raw_source="bibtex",
            )
            response = await self.add_citation(citation)
            if response.success:
                imported += 1
            else:
                skipped += 1
        
        return AgentResponse(success=True, data={"imported": imported, "skipped": skipped})
    
    async def export_bibtex(self, citation_ids: List[str] = None) -> AgentResponse:
        """Export citations to BibTeX format."""
        if not self._initialized:
            await self.initialize()
        
        to_export = [self.citations[cid] for cid in (citation_ids or self.citations.keys()) 
                    if cid in self.citations]
        
        entries = []
        for c in to_export:
            if c.raw_bibtex:
                entries.append(c.raw_bibtex)
            else:
                entry_type = "article" if "journal" in c.source.lower() else "misc"
                lines = [f"@{entry_type}{{{c.citation_key or c.generate_citation_key()},",
                        f"  title = {{{c.title}}},",
                        f"  author = {{{' and '.join(c.authors)}}},",
                        f"  year = {{{c.year}}},"]
                if c.source:
                    lines.append(f"  journal = {{{c.source}}},")
                if c.doi:
                    lines.append(f"  doi = {{{c.doi}}},")
                if c.url:
                    lines.append(f"  url = {{{c.url}}},")
                lines.append("}")
                entries.append("\n".join(lines))
        
        return AgentResponse(success=True, data="\n\n".join(entries),
                           metadata={"count": len(entries)})
    
    async def get_statistics(self) -> AgentResponse:
        """Get citation statistics."""
        if not self._initialized:
            await self.initialize()
        
        years = [c.year for c in self.citations.values() if c.year]
        return AgentResponse(success=True, data={
            "total": len(self.citations),
            "authors": len(self._index_by_author),
            "keywords": len(self._index_by_keyword),
            "year_range": (min(years), max(years)) if years else None,
            "with_doi": len(self._index_by_doi),
        })
    
    async def execute(self, operation: str, **kwargs) -> AgentResponse:
        """Execute citation memory operations."""
        if not self._initialized:
            await self.initialize()
        
        ops = {
            "add": lambda: self.add_citation(Citation(**kwargs)),
            "get": lambda: self.get_citation(kwargs.get("citation_id")),
            "get_by_doi": lambda: self.get_by_doi(kwargs.get("doi")),
            "search": lambda: self.search(**kwargs),
            "delete": lambda: self.delete_citation(kwargs.get("citation_id")),
            "import_bibtex": lambda: self.import_bibtex(kwargs.get("bibtex_content")),
            "export_bibtex": lambda: self.export_bibtex(kwargs.get("citation_ids")),
            "stats": lambda: self.get_statistics(),
        }
        
        if operation not in ops:
            return AgentResponse(success=False, error=f"Unknown operation: {operation}")
        return await ops[operation]()
