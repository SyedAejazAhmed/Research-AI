#!/usr/bin/env python3
"""
Academic MCP Server for GPT-Researcher

Provides academic research tools via Model Context Protocol (MCP):
- ArXiv search (free API)
- PubMed search (free NCBI API)
- Semantic Scholar search (free API)
- Google Scholar scraping (no API)
- University repository search (DuckDuckGo scraping)
- DOI reference formatting

100% API-free - uses public endpoints and HTML scraping.
"""
import asyncio
import json
import sys
import os
import re
from typing import List, Dict, Any
from urllib.parse import quote_plus
from datetime import datetime

# Check for required packages
try:
    import arxiv
    import requests
    from bs4 import BeautifulSoup
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install arxiv requests beautifulsoup4")
    sys.exit(1)

# Try to import MCP - skip if not compatible
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    # Test if the Server class has the expected API
    _test_server = Server("test")
    if not hasattr(_test_server, 'tool'):
        raise ImportError("MCP Server API incompatible")
    del _test_server
    HAS_MCP = True
except (ImportError, Exception) as e:
    HAS_MCP = False
    # Silently continue - standalone mode works fine



# =============================================================================
# Configuration
# =============================================================================

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/119.0.0.0",
]

UNIVERSITY_SITES = [
    "site:mit.edu",
    "site:stanford.edu",
    "site:harvard.edu",
    "site:berkeley.edu",
    "site:cam.ac.uk",
    "site:ox.ac.uk",
    "site:caltech.edu",
    "site:cmu.edu",
]

# Citation Format Templates
CITATION_FORMATS = {
    "APA": {
        "name": "APA 7th Edition",
        "description": "American Psychological Association (Psychology, Education, Social Sciences)",
        "template": "{authors} ({year}). {title}. {source}. {doi}"
    },
    "MLA": {
        "name": "MLA 9th Edition",
        "description": "Modern Language Association (Humanities, Literature, Arts)",
        "template": "{authors}. \"{title}.\" {source}, {year}. {doi}"
    },
    "Chicago": {
        "name": "Chicago Style (Author-Date)",
        "description": "Chicago Manual of Style (History, Arts, Humanities)",
        "template": "{authors}. {year}. \"{title}.\" {source}. {doi}"
    },
    "Harvard": {
        "name": "Harvard Referencing",
        "description": "Harvard Style (Business, Economics, Social Sciences)",
        "template": "{authors} ({year}) '{title}', {source}. {doi}"
    },
    "IEEE": {
        "name": "IEEE Style",
        "description": "Institute of Electrical and Electronics Engineers (Engineering, CS)",
        "template": "{authors}, \"{title},\" {source}, {year}. {doi}"
    },
    "Vancouver": {
        "name": "Vancouver Style",
        "description": "Medical and health sciences",
        "template": "{authors}. {title}. {source}. {year}. {doi}"
    }
}


# =============================================================================
# Helper Functions
# =============================================================================

def get_headers() -> Dict[str, str]:
    """Get random headers to avoid detection."""
    import random
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }


# =============================================================================
# Academic Search Functions
# =============================================================================

def search_arxiv(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Search arXiv for research papers.
    Returns papers with arXiv IDs and DOIs.
    """
    try:
        client = arxiv.Client()
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )
        
        results = []
        for paper in client.results(search):
            arxiv_id = paper.entry_id.split("/")[-1]
            results.append({
                "title": paper.title,
                "authors": ", ".join([a.name for a in paper.authors][:3]) + 
                          (" et al." if len(paper.authors) > 3 else ""),
                "abstract": paper.summary[:500] + "..." if len(paper.summary) > 500 else paper.summary,
                "doi": paper.doi if paper.doi else f"arXiv:{arxiv_id}",
                "arxiv_id": arxiv_id,
                "url": paper.pdf_url,
                "published": str(paper.published.date()) if paper.published else "",
                "source": "arXiv"
            })
        
        print(f"[ArXiv] Found {len(results)} papers")
        return results
        
    except Exception as e:
        print(f"[ArXiv] Error: {e}")
        return []


def search_semantic_scholar(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Search Semantic Scholar for academic papers with DOI.
    Free API - no key required.
    """
    try:
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": query,
            "limit": max_results,
            "fields": "title,abstract,url,year,authors,externalIds,citationCount"
        }
        
        response = requests.get(url, params=params, headers=get_headers(), timeout=15)
        response.raise_for_status()
        data = response.json().get("data", [])
        
        results = []
        for paper in data:
            external_ids = paper.get("externalIds", {}) or {}
            doi = external_ids.get("DOI", "")
            arxiv_id = external_ids.get("ArXiv", "")
            
            authors = paper.get("authors", []) or []
            author_names = ", ".join([a.get("name", "") for a in authors][:3])
            if len(authors) > 3:
                author_names += " et al."
            
            abstract = paper.get("abstract") or ""
            
            results.append({
                "title": paper.get("title", "Untitled"),
                "authors": author_names,
                "abstract": abstract[:500] + "..." if len(abstract) > 500 else abstract,
                "doi": doi if doi else (f"arXiv:{arxiv_id}" if arxiv_id else "N/A"),
                "url": paper.get("url", ""),
                "year": paper.get("year", ""),
                "citations": paper.get("citationCount", 0),
                "source": "Semantic Scholar"
            })
        
        print(f"[Semantic Scholar] Found {len(results)} papers")
        return results
        
    except Exception as e:
        print(f"[Semantic Scholar] Error: {e}")
        return []


def search_pubmed(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Search PubMed for medical and life science papers.
    Free NCBI API - no key required (rate limited without key).
    """
    try:
        # Search for article IDs
        search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        search_params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json"
        }
        
        response = requests.get(search_url, params=search_params, timeout=15)
        response.raise_for_status()
        ids = response.json().get("esearchresult", {}).get("idlist", [])
        
        if not ids:
            return []
        
        # Fetch article details
        fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        fetch_params = {
            "db": "pubmed",
            "id": ",".join(ids),
            "retmode": "json"
        }
        
        response = requests.get(fetch_url, params=fetch_params, timeout=15)
        response.raise_for_status()
        data = response.json().get("result", {})
        
        results = []
        for pmid in ids:
            if pmid not in data:
                continue
                
            paper = data[pmid]
            
            # Extract DOI from article IDs
            doi = ""
            for id_info in paper.get("articleids", []):
                if id_info.get("idtype") == "doi":
                    doi = id_info.get("value", "")
                    break
            
            results.append({
                "title": paper.get("title", "Untitled"),
                "authors": paper.get("sortfirstauthor", "Unknown"),
                "abstract": "",  # Summary doesn't include abstract
                "doi": doi if doi else f"PMID:{pmid}",
                "pmid": pmid,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "year": paper.get("pubdate", "")[:4],
                "source": "PubMed"
            })
        
        print(f"[PubMed] Found {len(results)} papers")
        return results
        
    except Exception as e:
        print(f"[PubMed] Error: {e}")
        return []


def search_google_scholar(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Scrape Google Scholar for academic papers.
    No API - uses HTML scraping.
    Note: May be blocked with heavy use.
    """
    try:
        url = f"https://scholar.google.com/scholar?q={quote_plus(query)}&hl=en"
        response = requests.get(url, headers=get_headers(), timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        results = []
        
        for item in soup.select(".gs_ri")[:max_results]:
            title_elem = item.select_one(".gs_rt a")
            snippet_elem = item.select_one(".gs_rs")
            info_elem = item.select_one(".gs_a")
            
            if not title_elem:
                continue
            
            title = title_elem.text.strip()
            url = title_elem.get("href", "")
            snippet = snippet_elem.text.strip()[:300] if snippet_elem else ""
            info = info_elem.text.strip() if info_elem else ""
            
            # Try to extract year from info
            year_match = re.search(r'\b(19|20)\d{2}\b', info)
            year = year_match.group(0) if year_match else ""
            
            # Try to extract authors (before the dash)
            authors = info.split(" - ")[0] if " - " in info else ""
            
            results.append({
                "title": title,
                "authors": authors[:100],
                "abstract": snippet,
                "doi": "See source",  # Scholar doesn't always show DOI
                "url": url,
                "year": year,
                "source": "Google Scholar"
            })
        
        print(f"[Google Scholar] Found {len(results)} papers")
        return results
        
    except Exception as e:
        print(f"[Google Scholar] Error: {e}")
        return []


def search_universities(query: str, max_results: int = 6) -> List[Dict[str, Any]]:
    """
    Search university repositories using DuckDuckGo.
    Searches MIT, Stanford, Harvard, Berkeley, etc.
    """
    results = []
    sites_to_search = UNIVERSITY_SITES[:4]  # Limit to avoid rate limiting
    
    for site in sites_to_search:
        try:
            search_query = f"{query} {site}"
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(search_query)}"
            
            response = requests.get(url, headers=get_headers(), timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            
            for item in soup.select(".web-result")[:2]:  # 2 per university
                title_elem = item.select_one(".result__a")
                snippet_elem = item.select_one(".result__snippet")
                
                if not title_elem:
                    continue
                
                results.append({
                    "title": title_elem.text.strip(),
                    "url": title_elem.get("href", ""),
                    "abstract": snippet_elem.text.strip()[:200] if snippet_elem else "",
                    "doi": "University source",
                    "source": site.replace("site:", "").upper()
                })
            
            # Small delay to avoid rate limiting
            import time
            time.sleep(0.3)
            
        except Exception as e:
            print(f"[University Search] Error for {site}: {e}")
            continue
    
    print(f"[Universities] Found {len(results)} sources")
    return results


def format_citation(papers: List[Dict[str, Any]], style: str = "APA") -> str:
    """
    Format papers into citations using specified academic style.
    
    Supported Formats:
    - APA: American Psychological Association (Psychology, Education)
    - MLA: Modern Language Association (Humanities, Literature)
    - Chicago: Chicago Manual of Style (History, Arts)
    - Harvard: Harvard Referencing (Business, Economics)
    - IEEE: IEEE Style (Engineering, Computer Science)
    - Vancouver: Vancouver Style (Medical, Health Sciences)
    
    Args:
        papers: List of paper dictionaries with metadata
        style: Citation format (APA, MLA, Chicago, Harvard, IEEE, Vancouver)
        
    Returns:
        Formatted citation string with [1], [2]... numbering
    """
    if not papers:
        return "No references found."
    
    # Normalize format name (handle case variations)
    style_map = {
        "APA": "APA",
        "MLA": "MLA",
        "CHICAGO": "Chicago",
        "HARVARD": "Harvard",
        "IEEE": "IEEE",
        "VANCOUVER": "Vancouver"
    }
    
    style = style.upper()
    if style in style_map:
        style = style_map[style]
    elif style not in CITATION_FORMATS:
        print(f"[Warning] Unknown style '{style}', defaulting to APA")
        style = "APA"
    
    # Sort papers by year (ascending: 2023 → 2025)
    def get_sort_key(paper):
        year_str = paper.get('year', '')
        try:
            # Extract 4-digit year if present
            year_match = re.search(r'\b(19|20)\d{2}\b', str(year_str))
            if year_match:
                return int(year_match.group(0))
            return 9999  # Papers without year go to end
        except:
            return 9999
    
    sorted_papers = sorted(papers, key=get_sort_key)
    
    formatted = []
    for i, paper in enumerate(sorted_papers, 1):
        authors = paper.get("authors", "Unknown Author")
        year = paper.get("year", "n.d.")
        title = paper.get("title", "Untitled")
        doi = paper.get("doi", "")
        source = paper.get("source", "")
        url = paper.get("url", "")
        citations = paper.get("citations", 0)
        
        # Clean up authors based on style
        if len(authors) > 100:
            authors = authors[:97] + "..."
        
        # Format citation based on selected style
        if style == "APA":
            # APA: Author, A. A. (Year). Title. Source. DOI
            ref = f"[{i}] {authors} ({year}). {title}."
            if source:
                ref += f" {source}."
            if doi and doi != "N/A":
                if doi.startswith("10."):
                    ref += f" https://doi.org/{doi}"
                elif doi.startswith("arXiv:"):
                    ref += f" {doi}"
                elif doi.startswith("PMID:"):
                    ref += f" {doi}"
                else:
                    ref += f" DOI: {doi}"
                    
        elif style == "MLA":
            # MLA: Author. "Title." Source, Year. DOI
            ref = f"[{i}] {authors}. \"{title}.\""
            if source:
                ref += f" {source},"
            ref += f" {year}."
            if doi and doi != "N/A" and doi.startswith("10."):
                ref += f" https://doi.org/{doi}"
            elif url:
                ref += f" {url}"
                
        elif style == "Chicago":
            # Chicago: Author. Year. "Title." Source. DOI
            ref = f"[{i}] {authors}. {year}. \"{title}.\""
            if source:
                ref += f" {source}."
            if doi and doi != "N/A":
                if doi.startswith("10."):
                    ref += f" https://doi.org/{doi}."
                else:
                    ref += f" {doi}."
                    
        elif style == "Harvard":
            # Harvard: Author (Year) 'Title', Source. DOI
            ref = f"[{i}] {authors} ({year}) '{title}'"
            if source:
                ref += f", {source}"
            if doi and doi != "N/A":
                if doi.startswith("10."):
                    ref += f". doi: {doi}"
                else:
                    ref += f". {doi}"
                    
        elif style == "IEEE":
            # IEEE: [1] Author, "Title," Source, Year. DOI
            ref = f"[{i}] {authors}, \"{title},\""
            if source:
                ref += f" {source},"
            ref += f" {year}."
            if doi and doi != "N/A":
                if doi.startswith("10."):
                    ref += f" doi: {doi}."
                else:
                    ref += f" {doi}."
                    
        elif style == "Vancouver":
            # Vancouver: 1. Author. Title. Source. Year; DOI
            ref = f"{i}. {authors}. {title}."
            if source:
                ref += f" {source}."
            ref += f" {year};"
            if doi and doi != "N/A":
                if doi.startswith("10."):
                    ref += f" doi: {doi}"
                else:
                    ref += f" {doi}"
        
        # Add citation count if available (for all styles)
        if citations > 0:
            ref += f" [Cited by {citations}]"
        
        formatted.append(ref)
    
    return "\n\n".join(formatted)


def format_doi_references(papers: List[Dict[str, Any]], style: str = "APA") -> str:
    """Format DOI references in the specified citation style.
    
    Args:
        papers: List of paper dictionaries with metadata
        style: Citation style (APA, MLA, Chicago, Harvard, IEEE, Vancouver)
        
    Returns:
        Formatted reference string
    """
    return format_citation(papers, style)


def get_available_formats() -> str:
    """Return formatted list of available citation formats."""
    output = "Available Citation Formats:\n" + "="*60 + "\n\n"
    
    for code, info in CITATION_FORMATS.items():
        output += f"{code:12} - {info['name']}\n"
        output += f"{'':12}   {info['description']}\n\n"
    
    return output


def select_citation_format() -> str:
    """
    Interactive citation format selector.
    Asks user to choose from available formats.
    """
    print("\n" + "="*70)
    print("CITATION FORMAT SELECTOR")
    print("="*70 + "\n")
    
    print(get_available_formats())
    
    while True:
        choice = input("Enter citation format (APA/MLA/Chicago/Harvard/IEEE/Vancouver): ").strip().upper()
        
        if choice in CITATION_FORMATS:
            selected = CITATION_FORMATS[choice]
            print(f"\n✓ Selected: {selected['name']}")
            print(f"  For: {selected['description']}\n")
            return choice
        else:
            print(f"❌ Invalid format. Please choose from: {', '.join(CITATION_FORMATS.keys())}\n")


def comprehensive_academic_search(query: str, max_per_source: int = 10, citation_format: str = "APA") -> Dict[str, Any]:
    """
    Search all academic sources and return combined results with formatted citations.
    Target: 20-30 unique references total from multiple sources.
    
    Sources:
    - ArXiv (preprints, CS/Math/Physics)
    - Semantic Scholar (multi-disciplinary with citations)
    - PubMed (medical/life sciences)
    - Google Scholar (broad coverage)
    - University repositories (institutional research)
    
    Args:
        query: Search query string
        max_per_source: Maximum results per source (default 10)
        citation_format: Citation style (APA, MLA, Chicago, Harvard, IEEE, Vancouver)
        
    Returns:
        Dictionary with papers, formatted references, and metadata
    """
    print(f"\n{'='*60}")
    print(f"Academic Search: {query}")
    print(f"Citation Format: {CITATION_FORMATS.get(citation_format.upper(), {}).get('name', citation_format)}")
    print(f"Target: 20-30 unique references")
    print(f"{'='*60}")
    
    all_papers = []
    
    # Search all sources with optimized limits for 20-30 total
    all_papers.extend(search_arxiv(query, max_per_source))
    all_papers.extend(search_semantic_scholar(query, max_per_source))
    all_papers.extend(search_pubmed(query, max_per_source))
    all_papers.extend(search_google_scholar(query, max_per_source // 2))
    all_papers.extend(search_universities(query, max_per_source // 2))
    
    print(f"\nRaw results collected: {len(all_papers)} papers")
    
    # Remove duplicates based on title similarity
    unique_papers = []
    seen_titles = set()
    
    for paper in all_papers:
        title_lower = paper.get("title", "").lower()[:50]
        if title_lower not in seen_titles:
            seen_titles.add(title_lower)
            unique_papers.append(paper)
    
    # Format references in selected citation style
    references = format_citation(unique_papers, citation_format)
    
    result = {
        "query": query,
        "total_results": len(unique_papers),
        "citation_format": citation_format,
        "format_name": CITATION_FORMATS.get(citation_format.upper(), {}).get("name", citation_format),
        "papers": unique_papers,
        "formatted_references": references,
        "timestamp": datetime.now().isoformat()
    }
    
    print(f"\nTotal unique papers: {len(unique_papers)}")
    print(f"{'='*60}\n")
    
    return result


# =============================================================================
# MCP Server Setup (if MCP is installed)
# =============================================================================

if HAS_MCP:
    app = Server("academic_research")
    
    @app.tool()
    async def academic_search(query: str, max_results: int = 30, citation_format: str = "APA") -> str:
        """
        Comprehensive academic search across ArXiv, PubMed, Semantic Scholar,
        Google Scholar, and university repositories.
        
        Returns 20-30 unique research papers with citations in your chosen format.
        
        Citation Formats:
        - APA: American Psychological Association (Psychology, Education)
        - MLA: Modern Language Association (Humanities, Literature)
        - Chicago: Chicago Manual of Style (History, Arts)
        - Harvard: Harvard Referencing (Business, Economics)
        - IEEE: IEEE Style (Engineering, Computer Science)
        - Vancouver: Vancouver Style (Medical, Health Sciences)
        
        Args:
            query: Research query (e.g., "machine learning in healthcare")
            max_results: Target number of references (default 30)
            citation_format: APA, MLA, Chicago, Harvard, IEEE, or Vancouver
            
        Returns:
            JSON with papers array and formatted_references string
        """
        # Calculate optimal per-source limit to get 20-30 total unique papers
        per_source = max(6, max_results // 4)
        result = comprehensive_academic_search(query, per_source, citation_format)
        return json.dumps(result, indent=2)
    
    @app.tool()
    async def search_arxiv_tool(query: str, max_results: int = 10) -> str:
        """Search arXiv for research papers with DOI/arXiv IDs."""
        results = search_arxiv(query, max_results)
        return json.dumps(results, indent=2)
    
    @app.tool()
    async def search_pubmed_tool(query: str, max_results: int = 10) -> str:
        """Search PubMed for medical and life science papers."""
        results = search_pubmed(query, max_results)
        return json.dumps(results, indent=2)
    
    @app.tool()
    async def search_semantic_tool(query: str, max_results: int = 10) -> str:
        """Search Semantic Scholar for academic papers."""
        results = search_semantic_scholar(query, max_results)
        return json.dumps(results, indent=2)
    
    @app.tool()
    async def get_formatted_citations(query: str, num_references: int = 25, citation_format: str = "APA") -> str:
        """
        Get ONLY formatted citation references (no JSON, just clean text).
        Choose from multiple academic citation styles.
        
        Returns properly formatted academic citations:
        
        APA Format:
        [1] Author, A. (2023). Paper Title. Source. https://doi.org/10.xxxx
        
        MLA Format:
        [1] Author, A. "Paper Title." Source, 2023. https://doi.org/10.xxxx
        
        Chicago Format:
        [1] Author, A. 2023. "Paper Title." Source. https://doi.org/10.xxxx
        
        Harvard Format:
        [1] Author, A. (2023) 'Paper Title', Source. doi: 10.xxxx
        
        IEEE Format:
        [1] Author, A., "Paper Title," Source, 2023. doi: 10.xxxx
        
        Vancouver Format:
        1. Author A. Paper Title. Source. 2023; doi: 10.xxxx
        
        Args:
            query: Research query
            num_references: Target number of references (default 25)
            citation_format: APA, MLA, Chicago, Harvard, IEEE, or Vancouver
            
        Returns:
            Plain text with numbered citations ready to paste into reports
        """
        per_source = max(6, num_references // 4)
        result = comprehensive_academic_search(query, per_source, citation_format)
        
        # Add header with metadata
        header = f"References for: {query}\n"
        header += f"Citation Format: {result.get('format_name', citation_format)}\n"
        header += f"Total: {result['total_results']} papers\n"
        header += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        header += "=" * 70 + "\n\n"
        
        return header + result["formatted_references"]
    
    @app.tool()
    async def list_citation_formats() -> str:
        """List all available citation formats with descriptions."""
        return get_available_formats()
    
    async def main_mcp():
        """Run as MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options()
            )


# =============================================================================
# Standalone Mode (for testing without MCP)
# =============================================================================

def main_standalone():
    """Run as standalone test with interactive citation format selection."""
    print("\n" + "="*70)
    print("ACADEMIC MCP SERVER - Multi-Format Citation Generator")
    print("Testing: 20-30 References with Multiple Citation Styles")
    print("="*70)
    
    # Select citation format interactively
    citation_format = select_citation_format()
    
    test_query = input("\nEnter research query (or press Enter for default): ").strip()
    if not test_query:
        test_query = "explainable AI and interpretable machine learning"
        print(f"Using default query: {test_query}")
    
    print(f"\nTarget: 20-30 unique research paper references\n")
    
    # Use optimized parameters to get 20-30 references
    result = comprehensive_academic_search(test_query, max_per_source=8, citation_format=citation_format)
    
    print("\n" + "="*70)
    print(f"FORMATTED CITATIONS - {result.get('format_name', citation_format)} Style")
    print("="*70 + "\n")
    print(result["formatted_references"])
    
    print("\n" + "="*70)
    print(f"✓ Total unique papers: {result['total_results']}")
    print(f"✓ Citation format: {result.get('format_name', citation_format)}")
    print(f"✓ Target met: {20 <= result['total_results'] <= 35}")
    print("="*70)
    
    # Save results
    filename_base = f"academic_{citation_format.lower()}"
    
    with open(f"{filename_base}_results.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Full results saved to: {filename_base}_results.json")
    
    # Save citations to text file
    with open(f"{filename_base}_citations.txt", "w", encoding="utf-8") as f:
        f.write(f"References for: {test_query}\n")
        f.write(f"Citation Format: {result.get('format_name', citation_format)}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 70 + "\n\n")
        f.write(result["formatted_references"])
    print(f"✓ Citations saved to: {filename_base}_citations.txt")
    
    print("\n" + "="*70)
    print("Test complete! Check the output files for formatted references.")
    print("="*70)


if __name__ == "__main__":
    if HAS_MCP and len(sys.argv) > 1 and sys.argv[1] == "--mcp":
        asyncio.run(main_mcp())
    else:
        main_standalone()
