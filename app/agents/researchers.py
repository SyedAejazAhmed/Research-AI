"""
Yukti Research AI - Research Agents
====================================
Parallel research agents that gather data from multiple sources:
1. Web Context Agent
2. Academic Research Agent (ArXiv, PubMed, Semantic Scholar)
3. Document Processing Agent
4. Metadata & Citation Agent
"""

import asyncio
import logging
import re
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.utils.cache import cache
from app.utils.references import is_verified_academic_paper

logger = logging.getLogger(__name__)


class WebContextAgent:
    """
    Agent 1: Web Context Research
    Searches the web for relevant context, news, and recent developments.
    """
    
    def __init__(self):
        self.name = "Web Context Agent"
        self.results = []
    
    async def research(self, query: str, keywords: List[str], callback=None) -> Dict[str, Any]:
        """Search web for relevant context."""
        if callback:
            await callback("web_agent", "searching", f"Searching web for: {query}")
        
        results = []
        
        try:
            import httpx
            
            # Use DuckDuckGo instant answer API (free, no key)
            async with httpx.AsyncClient(timeout=15.0) as client:
                search_queries = [query] + [f"{query} {kw}" for kw in keywords[:3]]
                
                for sq in search_queries:
                    try:
                        resp = await client.get(
                            "https://api.duckduckgo.com/",
                            params={"q": sq, "format": "json", "no_html": 1}
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            
                            # Extract abstract
                            if data.get("Abstract"):
                                results.append({
                                    "title": data.get("Heading", sq),
                                    "content": data["Abstract"],
                                    "url": data.get("AbstractURL", ""),
                                    "source": data.get("AbstractSource", "Web"),
                                    "type": "web_context"
                                })
                            
                            # Extract related topics
                            for topic in data.get("RelatedTopics", [])[:5]:
                                if isinstance(topic, dict) and topic.get("Text"):
                                    results.append({
                                        "title": topic.get("Text", "")[:100],
                                        "content": topic.get("Text", ""),
                                        "url": topic.get("FirstURL", ""),
                                        "source": "DuckDuckGo",
                                        "type": "web_context"
                                    })
                    except Exception as e:
                        logger.warning(f"Web search error for '{sq}': {e}")
                        continue
                    
                    await asyncio.sleep(0.3)  # Rate limiting
                        
        except ImportError:
            logger.warning("httpx not installed, web search disabled")
        except Exception as e:
            logger.error(f"Web context agent error: {e}")
        
        self.results = results
        
        if callback:
            await callback("web_agent", "completed", f"Found {len(results)} web results")
        
        return {
            "agent": self.name,
            "results": results,
            "count": len(results),
            "timestamp": datetime.now().isoformat()
        }


class AcademicResearchAgent:
    """
    Agent 2: Academic Research
    Searches ArXiv, PubMed, and Semantic Scholar for academic papers.
    """
    
    def __init__(self):
        self.name = "Academic Research Agent"
        self.results = []
    
    async def research(self, query: str, keywords: List[str], callback=None) -> Dict[str, Any]:
        """Search academic databases for relevant papers."""
        # Check cache first
        cached_results = cache.get(query, "academic_research")
        if cached_results:
            if callback:
                await callback("academic_agent", "completed", f"Using cached results ({len(cached_results)} papers)")
            return {
                "agent": self.name,
                "results": cached_results,
                "count": len(cached_results),
                "cached": True,
                "timestamp": datetime.now().isoformat()
            }

        if callback:
            await callback("academic_agent", "searching", "Searching academic databases...")
        
        all_papers = []
        
        # Search ArXiv
        if callback:
            await callback("academic_agent", "searching", "Searching ArXiv...")
        arxiv_papers = await self._search_arxiv(query)
        all_papers.extend(arxiv_papers)
        
        # Search PubMed
        if callback:
            await callback("academic_agent", "searching", "Searching PubMed...")
        pubmed_papers = await self._search_pubmed(query)
        all_papers.extend(pubmed_papers)
        
        # Search Semantic Scholar
        if callback:
            await callback("academic_agent", "searching", "Searching Semantic Scholar...")
        ss_papers = await self._search_semantic_scholar(query)
        all_papers.extend(ss_papers)
        
        # Deduplicate by title similarity
        unique_papers = self._deduplicate(all_papers)
        self.results = unique_papers
        
        # Save to cache
        cache.set(query, unique_papers, "academic_research")
        
        if callback:
            await callback("academic_agent", "completed", f"Found {len(unique_papers)} unique academic papers")
        
        return {
            "agent": self.name,
            "results": unique_papers,
            "count": len(unique_papers),
            "sources": {
                "arxiv": len(arxiv_papers),
                "pubmed": len(pubmed_papers),
                "semantic_scholar": len(ss_papers)
            },
            "timestamp": datetime.now().isoformat()
        }
    
    async def _search_arxiv(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search ArXiv for papers."""
        papers = []
        try:
            import httpx
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    "http://export.arxiv.org/api/query",
                    params={
                        "search_query": f"all:{query}",
                        "start": 0,
                        "max_results": max_results,
                        "sortBy": "relevance"
                    }
                )
                if resp.status_code == 200:
                    papers = self._parse_arxiv_xml(resp.text)
        except Exception as e:
            logger.error(f"ArXiv search error: {e}")
        return papers
    
    def _parse_arxiv_xml(self, xml_text: str) -> List[Dict]:
        """Parse ArXiv API XML response."""
        papers = []
        try:
            from xml.etree import ElementTree as ET
            root = ET.fromstring(xml_text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            
            for entry in root.findall("atom:entry", ns):
                title = entry.find("atom:title", ns)
                summary = entry.find("atom:summary", ns)
                published = entry.find("atom:published", ns)
                link = entry.find("atom:id", ns)
                
                authors = []
                for author in entry.findall("atom:author", ns):
                    name = author.find("atom:name", ns)
                    if name is not None:
                        authors.append(name.text.strip())
                
                # Extract DOI if available
                doi = ""
                for lnk in entry.findall("atom:link", ns):
                    if lnk.get("title") == "doi":
                        doi = lnk.get("href", "")
                
                arxiv_id = ""
                if link is not None:
                    arxiv_id = link.text.strip().split("/abs/")[-1]
                
                papers.append({
                    "title": title.text.strip() if title is not None else "Untitled",
                    "authors": authors,
                    "abstract": summary.text.strip() if summary is not None else "",
                    "year": published.text[:4] if published is not None else "",
                    "url": link.text.strip() if link is not None else "",
                    "doi": doi or f"arXiv:{arxiv_id}",
                    "source": "ArXiv",
                    "type": "academic_paper"
                })
        except Exception as e:
            logger.error(f"ArXiv XML parse error: {e}")
        return papers
    
    async def _search_pubmed(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search PubMed for papers."""
        papers = []
        try:
            import httpx
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Step 1: Search for IDs
                search_resp = await client.get(
                    "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                    params={
                        "db": "pubmed",
                        "term": query,
                        "retmax": max_results,
                        "retmode": "json",
                        "sort": "relevance"
                    }
                )
                
                if search_resp.status_code == 200:
                    search_data = search_resp.json()
                    id_list = search_data.get("esearchresult", {}).get("idlist", [])
                    
                    if id_list:
                        # Step 2: Fetch details
                        detail_resp = await client.get(
                            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
                            params={
                                "db": "pubmed",
                                "id": ",".join(id_list),
                                "retmode": "json"
                            }
                        )
                        
                        if detail_resp.status_code == 200:
                            detail_data = detail_resp.json()
                            results = detail_data.get("result", {})
                            
                            for pmid in id_list:
                                if pmid in results:
                                    paper = results[pmid]
                                    authors = []
                                    for auth in paper.get("authors", []):
                                        authors.append(auth.get("name", ""))
                                    
                                    doi_ids = [a for a in paper.get("articleids", []) if a.get("idtype") == "doi"]
                                    doi = doi_ids[0]["value"] if doi_ids else ""
                                    
                                    papers.append({
                                        "title": paper.get("title", "Untitled"),
                                        "authors": authors,
                                        "abstract": "",  # Summary API doesn't return abstracts
                                        "year": paper.get("pubdate", "")[:4],
                                        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                                        "doi": doi,
                                        "source": "PubMed",
                                        "type": "academic_paper"
                                    })
        except Exception as e:
            logger.error(f"PubMed search error: {e}")
        return papers
    
    async def _search_semantic_scholar(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search Semantic Scholar for papers."""
        papers = []
        try:
            import httpx
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    "https://api.semanticscholar.org/graph/v1/paper/search",
                    params={
                        "query": query,
                        "limit": max_results,
                        "fields": "title,authors,abstract,year,url,externalIds,citationCount"
                    }
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    for paper in data.get("data", []):
                        authors = [a.get("name", "") for a in paper.get("authors", [])]
                        ext_ids = paper.get("externalIds", {})
                        doi = ext_ids.get("DOI", "") or ext_ids.get("ArXiv", "")
                        
                        papers.append({
                            "title": paper.get("title", "Untitled"),
                            "authors": authors,
                            "abstract": paper.get("abstract", "") or "",
                            "year": str(paper.get("year", "")),
                            "url": paper.get("url", ""),
                            "doi": doi,
                            "source": "Semantic Scholar",
                            "citation_count": paper.get("citationCount", 0),
                            "type": "academic_paper"
                        })
        except Exception as e:
            logger.error(f"Semantic Scholar search error: {e}")
        return papers
    
    def _deduplicate(self, papers: List[Dict]) -> List[Dict]:
        """Remove duplicate papers based on title similarity."""
        seen_titles = set()
        unique = []
        
        for paper in papers:
            # Normalize title for comparison
            normalized = re.sub(r'[^a-z0-9\s]', '', paper.get("title", "").lower()).strip()
            
            if normalized and normalized not in seen_titles:
                seen_titles.add(normalized)
                unique.append(paper)
        
        return unique


class DocumentProcessingAgent:
    """
    Agent 3: Document Processing
    Processes and ranks research content for relevance and quality.
    """
    
    def __init__(self):
        self.name = "Document Processing Agent"
    
    async def process(self, research_data: List[Dict], query: str, callback=None) -> Dict[str, Any]:
        """Process and rank research documents."""
        if callback:
            await callback("doc_agent", "processing", "Processing and ranking documents...")
        
        # Score and rank documents
        scored_docs = []
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        for doc in research_data:
            score = self._calculate_relevance(doc, query_words, query_lower)
            doc["relevance_score"] = score
            scored_docs.append(doc)
        
        # Sort by relevance
        scored_docs.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        # Filter out low-quality sources (score < 0.1)
        high_quality = [d for d in scored_docs if d.get("relevance_score", 0) >= 0.1]
        
        if callback:
            await callback("doc_agent", "completed", f"Processed {len(high_quality)} high-quality documents")
        
        return {
            "agent": self.name,
            "processed_documents": high_quality,
            "total_processed": len(research_data),
            "high_quality_count": len(high_quality),
            "filtered_count": len(research_data) - len(high_quality),
            "timestamp": datetime.now().isoformat()
        }
    
    def _calculate_relevance(self, doc: Dict, query_words: set, query_lower: str) -> float:
        """Calculate relevance score for a document."""
        score = 0.0
        
        title = doc.get("title", "").lower()
        content = doc.get("content", "").lower() or doc.get("abstract", "").lower()
        
        # Title match (weighted heavily)
        title_words = set(title.split())
        title_overlap = len(query_words & title_words)
        score += title_overlap * 0.3
        
        # Content keyword match
        for word in query_words:
            if word in content:
                score += 0.1
        
        # Exact phrase match bonus
        if query_lower in title:
            score += 0.5
        if query_lower in content:
            score += 0.3
        
        # Source quality bonus
        source = doc.get("source", "").lower()
        if source in ["arxiv", "pubmed", "semantic scholar"]:
            score += 0.2
        
        # Citation count bonus
        citations = doc.get("citation_count", 0)
        if citations > 100:
            score += 0.3
        elif citations > 50:
            score += 0.2
        elif citations > 10:
            score += 0.1
        
        # DOI presence bonus
        if doc.get("doi"):
            score += 0.1
        
        return min(score, 1.0)  # Cap at 1.0


class CitationAgent:
    """
    Agent 4: Metadata & Citation Agent
    Generates and validates citations, verifies DOIs.
    """
    
    def __init__(self):
        self.name = "Citation Agent"
    
    async def generate_citations(self, papers: List[Dict], style: str = "IEEE", callback=None) -> Dict[str, Any]:
        """Generate formatted citations for all papers."""
        if callback:
            await callback("citation_agent", "generating", "Generating citations...")
        
        citations = []
        verified_count = 0
        filtered_non_papers = 0
        
        for i, paper in enumerate(papers):
            verification = is_verified_academic_paper(paper)
            if not verification.get("is_academic_paper"):
                filtered_non_papers += 1
                continue

            citation_number = len(citations) + 1
            citation = self._format_citation(paper, citation_number, style)

            is_verified = bool(
                verification.get("doi_valid")
                or verification.get("scholarly_domain")
                or paper.get("doi")
            )
            if is_verified:
                verified_count += 1
            
            citations.append({
                "number": citation_number,
                "formatted": citation,
                "doi": paper.get("doi", ""),
                "verified": is_verified,
                "verification": verification,
                "paper": paper
            })
        
        if callback:
            await callback(
                "citation_agent",
                "completed",
                f"Generated {len(citations)} citations ({verified_count} verified, {filtered_non_papers} non-paper items filtered).",
            )
        
        return {
            "agent": self.name,
            "citations": citations,
            "total": len(citations),
            "verified": verified_count,
            "filtered_non_papers": filtered_non_papers,
            "style": style,
            "formatted_text": self._build_reference_section(citations),
            "timestamp": datetime.now().isoformat()
        }
    
    def _format_citation(self, paper: Dict, number: int, style: str = "APA") -> str:
        """Format a single citation in the given style."""
        authors = paper.get("authors", [])
        title = paper.get("title", "Untitled")
        year = paper.get("year", "n.d.")
        doi = paper.get("doi", "")
        source = paper.get("source", "")
        url = paper.get("url", "")
        
        # Format authors
        if len(authors) > 3:
            author_str = f"{authors[0]}, {authors[1]}, ... & {authors[-1]}"
        elif len(authors) > 1:
            author_str = ", ".join(authors[:-1]) + f", & {authors[-1]}"
        elif authors:
            author_str = authors[0]
        else:
            author_str = "Unknown Author"
        
        if style == "APA":
            citation = f"[{number}] {author_str} ({year}). {title}. *{source}*."
            if doi:
                citation += f" https://doi.org/{doi}" if not doi.startswith("arXiv") else f" {doi}"
        elif style == "IEEE":
            citation = f"[{number}] {author_str}, \"{title},\" {source}, {year}."
            if doi:
                citation += f" DOI: {doi}"
        else:  # MLA-like default
            citation = f"[{number}] {author_str}. \"{title}.\" {source}, {year}."
            if url:
                citation += f" {url}"
        
        return citation
    
    def _build_reference_section(self, citations: List[Dict]) -> str:
        """Build a formatted references section."""
        if not citations:
            return "No references found."
        
        lines = ["## References\n"]
        for cite in citations:
            lines.append(cite["formatted"])
        
        return "\n\n".join(lines)
