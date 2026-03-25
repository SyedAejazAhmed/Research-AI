"""Reference generation service.

Discover papers via DuckDuckGo, enrich metadata with scholarly APIs,
and return Zotero-like items plus formatted references.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import requests

try:
    from ddgs import DDGS
except Exception:
    try:
        from duckduckgo_search import DDGS
    except Exception:
        DDGS = None


DDG_JINA_MIRROR = "https://r.jina.ai/http://duckduckgo.com/html/"
SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
CROSSREF_URL = "https://api.crossref.org/works"
DEFAULT_LIMIT = 24
DEFAULT_STYLE = "IEEE"

SCHOLARLY_DOMAINS = [
    "ieeexplore.ieee.org",
    "scopus.com",
    "link.springer.com",
    "sciencedirect.com",
    "nature.com",
    "onlinelibrary.wiley.com",
    "dl.acm.org",
    "pubmed.ncbi.nlm.nih.gov",
    "arxiv.org",
    "mdpi.com",
    "tandfonline.com",
]

STYLE_NAMES = {
    "IEEE": "IEEE",
    "APA": "APA 7th",
    "MLA": "MLA 9th",
    "CHICAGO": "Chicago",
    "HARVARD": "Harvard",
    "VANCOUVER": "Vancouver",
}


@dataclass
class ReferenceItem:
    title: str
    url: str
    source: str
    authors: List[str]
    year: str
    doi: str = ""
    abstract: str = ""
    item_type: str = "journalArticle"

    def to_zotero_like(self) -> Dict[str, Any]:
        creators: List[Dict[str, str]] = []
        for author in self.authors:
            name = author.strip()
            if not name:
                continue
            parts = name.split()
            if len(parts) == 1:
                creators.append({"creatorType": "author", "name": parts[0]})
            else:
                creators.append(
                    {
                        "creatorType": "author",
                        "firstName": " ".join(parts[:-1]),
                        "lastName": parts[-1],
                    }
                )

        return {
            "itemType": self.item_type,
            "title": self.title,
            "creators": creators,
            "date": self.year,
            "DOI": self.doi,
            "url": self.url,
            "publicationTitle": self.source,
            "abstractNote": self.abstract,
            "accessDate": datetime.now(UTC).strftime("%Y-%m-%d"),
        }


def _extract_year(text: str) -> str:
    match = re.search(r"\b(19|20)\d{2}\b", text)
    return match.group(0) if match else "n.d."


def _decode_ddg_redirect(url: str) -> str:
    if "duckduckgo.com/l/?" not in url:
        return url
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    uddg = params.get("uddg", [""])[0]
    return unquote(uddg) if uddg else url


def _is_scholarly_url(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return any(domain in host for domain in SCHOLARLY_DOMAINS)


def _normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", title.lower())).strip()


def _search_ddg(query: str, limit: int) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    seen = set()

    if DDGS is not None:
        with DDGS() as ddgs:
            for row in ddgs.text(f"{query} research paper", max_results=max(limit * 5, 80)):
                title = (row.get("title") or "").strip()
                url = (row.get("href") or row.get("url") or "").strip()
                body = (row.get("body") or "").strip()
                if not title or not url:
                    continue
                url = _decode_ddg_redirect(url)
                if url in seen or not _is_scholarly_url(url):
                    continue
                seen.add(url)
                rows.append({"title": title, "url": url, "snippet": body})
                if len(rows) >= limit * 3:
                    break

    if len(rows) < limit:
        variants = [
            f"{query} site:ieeexplore.ieee.org",
            f"{query} site:scopus.com",
            f"{query} site:link.springer.com",
            f"{query} site:sciencedirect.com",
            f"{query} site:dl.acm.org",
            f"{query} site:nature.com",
            f"{query} site:arxiv.org",
            f"{query} site:pubmed.ncbi.nlm.nih.gov",
        ]
        for variant in variants:
            if len(rows) >= limit * 3:
                break
            mirror_url = f"{DDG_JINA_MIRROR}?q={quote_plus(variant)}"
            response = requests.get(mirror_url, timeout=30)
            response.raise_for_status()
            text = response.text
            for match in re.finditer(r"## \[(.*?)\]\((https?://[^)]+)\)", text):
                title = match.group(1).strip()
                url = _decode_ddg_redirect(match.group(2).strip())
                if not title or not url or url in seen or not _is_scholarly_url(url):
                    continue
                context = re.sub(r"\s+", " ", text[match.end(): match.end() + 220]).strip()
                seen.add(url)
                rows.append({"title": title, "url": url, "snippet": context})
                if len(rows) >= limit * 3:
                    break

    return rows


def _enrich_semantic_scholar(title: str) -> Optional[Dict[str, Any]]:
    params = {
        "query": title,
        "limit": 5,
        "fields": "title,authors,year,venue,externalIds,abstract,url",
    }
    response = requests.get(SEMANTIC_SCHOLAR_URL, params=params, timeout=20)
    response.raise_for_status()
    data = response.json().get("data", [])
    if not data:
        return None

    normalized_target = _normalize_title(title)
    best = None
    for item in data:
        cand_title = item.get("title", "")
        if not cand_title:
            continue
        norm_cand = _normalize_title(cand_title)
        overlap = len(set(normalized_target.split()) & set(norm_cand.split()))
        if overlap >= 4:
            best = item
            break

    if best is None:
        best = data[0]

    external_ids = best.get("externalIds") or {}
    authors = [a.get("name", "").strip() for a in (best.get("authors") or []) if a.get("name")]

    return {
        "title": best.get("title") or title,
        "authors": authors,
        "year": str(best.get("year") or "n.d."),
        "source": best.get("venue") or "",
        "doi": external_ids.get("DOI", ""),
        "abstract": best.get("abstract") or "",
        "url": best.get("url") or "",
    }


def _enrich_crossref(title: str) -> Optional[Dict[str, Any]]:
    response = requests.get(CROSSREF_URL, params={"query.title": title, "rows": 3}, timeout=20)
    response.raise_for_status()
    items = (response.json().get("message") or {}).get("items") or []
    if not items:
        return None

    best = items[0]
    c_authors = []
    for a in best.get("author", []) or []:
        given = (a.get("given") or "").strip()
        family = (a.get("family") or "").strip()
        full = f"{given} {family}".strip()
        if full:
            c_authors.append(full)

    year = "n.d."
    date_parts = (best.get("issued") or {}).get("date-parts") or []
    if date_parts and date_parts[0]:
        year = str(date_parts[0][0])

    source = ""
    container = best.get("container-title") or []
    if container:
        source = container[0]

    return {
        "title": (best.get("title") or [title])[0],
        "authors": c_authors,
        "year": year,
        "source": source,
        "doi": best.get("DOI", ""),
        "abstract": "",
        "url": (best.get("URL") or ""),
    }


def _to_ieee_authors(authors: List[str]) -> str:
    out = []
    for name in authors[:6]:
        parts = name.strip().split()
        if len(parts) == 1:
            out.append(parts[0])
        else:
            initials = " ".join(f"{p[0]}." for p in parts[:-1] if p)
            out.append(f"{initials} {parts[-1]}")
    if len(authors) > 6:
        out.append("et al.")
    return ", ".join(out)


def format_references(items: List[ReferenceItem], style: str) -> str:
    s = style.upper()
    lines: List[str] = []

    for idx, item in enumerate(items, start=1):
        authors = ", ".join(item.authors) if item.authors else "Unknown"
        ieee_authors = _to_ieee_authors(item.authors) if item.authors else "Unknown"

        if s == "IEEE":
            line = f"[{idx}] {ieee_authors}, \"{item.title},\" {item.source}, {item.year}."
            if item.doi:
                line += f" doi: {item.doi}."
            line += f" {item.url}"
        elif s == "APA":
            line = f"[{idx}] {authors} ({item.year}). {item.title}. {item.source}."
            if item.doi:
                line += f" https://doi.org/{item.doi}"
        elif s == "MLA":
            line = f"[{idx}] {authors}. \"{item.title}.\" {item.source}, {item.year}."
            if item.doi:
                line += f" https://doi.org/{item.doi}"
        elif s == "CHICAGO":
            line = f"[{idx}] {authors}. {item.year}. \"{item.title}.\" {item.source}."
            if item.doi:
                line += f" https://doi.org/{item.doi}."
        elif s == "HARVARD":
            line = f"[{idx}] {authors} ({item.year}) '{item.title}', {item.source}."
            if item.doi:
                line += f" doi: {item.doi}"
        elif s == "VANCOUVER":
            line = f"{idx}. {authors}. {item.title}. {item.source}. {item.year}."
            if item.doi:
                line += f" doi: {item.doi}"
        else:
            raise ValueError("Unsupported style. Use IEEE/APA/MLA/Chicago/Harvard/Vancouver")

        lines.append(line)

    return "\n\n".join(lines)


def pyzotero_capabilities() -> Dict[str, Any]:
    try:
        from pyzotero import zotero

        z = zotero.Zotero("0", "user", None)
        formats = sorted(list(z.processors.keys()))
        return {
            "available": True,
            "formats": formats,
            "style_note": (
                "For citation output, pyzotero uses Zotero API `content=citation` and "
                "accepts CSL style IDs (e.g., ieee, apa, modern-language-association)."
            ),
        }
    except Exception as exc:
        return {"available": False, "formats": [], "style_note": str(exc)}


def generate_references(query: str, limit: int = DEFAULT_LIMIT, style: str = DEFAULT_STYLE) -> Dict[str, Any]:
    candidates = _search_ddg(query, limit)

    references: List[ReferenceItem] = []
    seen_titles = set()

    for cand in candidates:
        if len(references) >= limit:
            break

        title = cand["title"]
        norm_title = _normalize_title(title)
        if norm_title in seen_titles:
            continue

        meta = None
        try:
            meta = _enrich_semantic_scholar(title)
        except Exception:
            meta = None

        if not meta:
            try:
                meta = _enrich_crossref(title)
            except Exception:
                meta = None

        if not meta:
            continue

        authors = [a for a in (meta.get("authors") or []) if a and a.lower() != "unknown"]
        if not authors:
            continue

        source = (meta.get("source") or "").strip() or urlparse(cand["url"]).netloc
        final_url = (meta.get("url") or cand["url"] or "").strip()

        references.append(
            ReferenceItem(
                title=(meta.get("title") or title).strip(),
                url=final_url,
                source=source,
                authors=authors,
                year=str(meta.get("year") or _extract_year(cand.get("snippet", ""))),
                doi=(meta.get("doi") or "").strip(),
                abstract=(meta.get("abstract") or cand.get("snippet") or "").strip(),
            )
        )
        seen_titles.add(norm_title)

    references.sort(key=lambda r: int(r.year) if r.year.isdigit() else 9999)
    pyz = pyzotero_capabilities()

    return {
        "query": query,
        "count": len(references),
        "style": style.upper(),
        "style_name": STYLE_NAMES.get(style.upper(), style.upper()),
        "papers": [r.to_zotero_like() for r in references],
        "formatted_references": format_references(references, style),
        "source_domains": SCHOLARLY_DOMAINS,
        "pyzotero": pyz,
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
