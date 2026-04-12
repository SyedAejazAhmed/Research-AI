"""Reference generation service.

Discover papers via DuckDuckGo, enrich metadata with scholarly APIs,
and return Zotero-like items plus formatted references.
"""

from __future__ import annotations

import json
import logging
import re
from difflib import SequenceMatcher
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
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
DEFAULT_LIMIT = 30
DEFAULT_STYLE = "IEEE"
REFERENCE_NEAR_TARGET_MIN = 24
MAX_QUERY_VARIANTS = 4

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

QUERY_STOPWORDS = {
    "a", "an", "and", "for", "from", "in", "of", "on", "to", "with",
    "study", "research", "paper", "analysis", "survey", "review",
}

NOISY_SHORT_TITLE_TERMS = {
    "call", "calls", "papers", "editorial", "preface", "contents", "issue",
    "volume", "index", "other", "side", "news", "announcement",
}


logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REFERENCE_MEMORY_PATH = PROJECT_ROOT / "sessions" / "reference_memory.json"
MEMORY_MAX_ENTRIES = 5000
FUZZY_DUPLICATE_THRESHOLD = 0.88
CANDIDATE_MULTIPLIER = 6
DOI_PATTERN = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$")

STYLE_TO_CSL = {
    "IEEE": "ieee",
    "APA": "apa",
    "MLA": "modern-language-association",
    "CHICAGO": "chicago-author-date",
    "HARVARD": "harvard-cite-them-right",
    "VANCOUVER": "vancouver",
}


def _canonical_url(url: str) -> str:
    parsed = urlparse((url or "").strip())
    host = (parsed.netloc or "").lower().strip()
    path = (parsed.path or "").rstrip("/").strip()
    if not host:
        return ""
    return f"{host}{path}"


def _reference_signature(title: str, doi: str, url: str) -> str:
    normalized_doi = (doi or "").strip().lower()
    if normalized_doi:
        return f"doi:{normalized_doi}"

    canonical = _canonical_url(url)
    if canonical:
        return f"url:{canonical}"

    return f"title:{_normalize_title(title)}"


def _is_fuzzy_duplicate(candidate_title: str, existing_titles: List[str]) -> bool:
    cand = _normalize_title(candidate_title)
    if not cand:
        return False

    for existing in existing_titles:
        norm_existing = _normalize_title(existing)
        if not norm_existing:
            continue

        if cand == norm_existing:
            return True

        # If one title contains the other and both are substantial, treat as duplicate.
        if (cand in norm_existing or norm_existing in cand) and min(len(cand), len(norm_existing)) >= 18:
            return True

        min_len = min(len(cand), len(norm_existing))
        threshold = 0.95 if min_len < 22 else FUZZY_DUPLICATE_THRESHOLD
        ratio = SequenceMatcher(None, cand, norm_existing).ratio()
        if ratio >= threshold:
            return True

    return False


def _load_reference_memory(path: Optional[Path] = None) -> List[Dict[str, str]]:
    if path is None:
        path = REFERENCE_MEMORY_PATH

    if not path.exists():
        return []

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to read reference memory: %s", exc)
        return []

    entries = payload.get("entries", []) if isinstance(payload, dict) else []
    normalized: List[Dict[str, str]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        signature = str(entry.get("signature", "")).strip()
        title_norm = _normalize_title(str(entry.get("title_norm") or entry.get("title") or ""))
        if not signature and not title_norm:
            continue
        normalized.append(
            {
                "signature": signature,
                "title_norm": title_norm,
                "title": str(entry.get("title", "")).strip(),
                "doi": str(entry.get("doi", "")).strip(),
                "url": str(entry.get("url", "")).strip(),
                "source": str(entry.get("source", "")).strip(),
                "year": str(entry.get("year", "")).strip(),
                "last_seen": str(entry.get("last_seen", "")).strip(),
            }
        )

    return normalized


def _dedupe_memory_entries(entries: List[Dict[str, str]]) -> List[Dict[str, str]]:
    deduped: Dict[str, Dict[str, str]] = {}
    for entry in entries:
        signature = str(entry.get("signature", "")).strip()
        title_norm = _normalize_title(str(entry.get("title_norm") or entry.get("title") or ""))
        key = signature or f"title:{title_norm}"
        if not key or key == "title:":
            continue
        if key in deduped:
            deduped.pop(key)
        clean_entry = dict(entry)
        clean_entry["title_norm"] = title_norm
        deduped[key] = clean_entry
    return list(deduped.values())[-MEMORY_MAX_ENTRIES:]


def _save_reference_memory(entries: List[Dict[str, str]], path: Optional[Path] = None) -> None:
    if path is None:
        path = REFERENCE_MEMORY_PATH

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "updated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "entries": _dedupe_memory_entries(entries),
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.warning("Failed to save reference memory: %s", exc)


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
    is_academic_paper: bool = False
    verification_reason: str = ""

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
            "isAcademicPaper": self.is_academic_paper,
            "verificationReason": self.verification_reason,
        }


def _looks_like_doi(value: str) -> bool:
    doi = str(value or "").strip()
    if not doi:
        return False
    return bool(DOI_PATTERN.match(doi))


def _is_plausible_year(value: str) -> bool:
    text = str(value or "").strip()
    if not text.isdigit():
        return False
    year = int(text)
    current_year = datetime.now(UTC).year
    return 1900 <= year <= current_year + 1


def _infer_item_type(doi_valid: bool, scholarly_domain: bool, source: str) -> str:
    if doi_valid or scholarly_domain:
        source_lower = str(source or "").lower()
        if "conference" in source_lower or "proceedings" in source_lower:
            return "conferencePaper"
        if "arxiv" in source_lower:
            return "preprint"
        return "journalArticle"
    return "document"


def is_verified_academic_paper(
    paper: Dict[str, Any],
    query_terms: Optional[set[str]] = None,
) -> Dict[str, Any]:
    """Heuristically verify whether a candidate resembles an academic paper."""
    title = str(paper.get("title", "")).strip()
    url = str(paper.get("url", "")).strip()
    doi = str(paper.get("doi", "")).strip()
    year = str(paper.get("year", "")).strip()
    source = str(paper.get("source", "")).strip()
    authors = paper.get("authors") or []

    title_norm = _normalize_title(title)
    title_token_count = len(title_norm.split())
    title_valid = title_token_count >= 3 and not _looks_offtopic_short_title(title, query_terms or set())
    doi_valid = _looks_like_doi(doi) or doi.lower().startswith("arxiv:")
    scholarly_domain = _is_scholarly_url(url)
    year_valid = _is_plausible_year(year)
    source_valid = bool(source)
    authors_valid = bool([a for a in authors if str(a).strip()])

    score = 0
    if title_valid:
        score += 2
    if doi_valid:
        score += 2
    if scholarly_domain:
        score += 1
    if year_valid:
        score += 1
    if source_valid:
        score += 1
    if authors_valid:
        score += 1

    is_academic = title_valid and score >= 4 and (doi_valid or scholarly_domain or source_valid)
    item_type = _infer_item_type(doi_valid, scholarly_domain, source)

    reasons = []
    if title_valid:
        reasons.append("title_ok")
    if doi_valid:
        reasons.append("doi_ok")
    if scholarly_domain:
        reasons.append("scholarly_domain")
    if year_valid:
        reasons.append("year_ok")
    if source_valid:
        reasons.append("source_ok")
    if authors_valid:
        reasons.append("authors_ok")

    return {
        "is_academic_paper": is_academic,
        "item_type": item_type,
        "doi_valid": doi_valid,
        "scholarly_domain": scholarly_domain,
        "score": score,
        "reason": ",".join(reasons) if reasons else "insufficient_metadata",
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


def _query_terms(query: str) -> set[str]:
    terms = set()
    for token in re.findall(r"[a-z0-9]{3,}", str(query or "").lower()):
        if token in QUERY_STOPWORDS:
            continue
        terms.add(token)
    return terms


def _looks_offtopic_short_title(title: str, query_terms: set[str]) -> bool:
    tokens = [t for t in re.findall(r"[a-z0-9]{2,}", str(title or "").lower()) if t]
    if not tokens or len(tokens) > 4:
        return False
    if query_terms and set(tokens) & query_terms:
        return False
    if len(tokens) <= 2:
        return True
    return bool(set(tokens) & NOISY_SHORT_TITLE_TERMS)


def _search_ddg(query: str, limit: int) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    seen = set()

    if DDGS is not None:
        try:
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
                    if len(rows) >= limit * CANDIDATE_MULTIPLIER:
                        break
        except Exception as exc:
            logger.warning("DDGS discovery failed for query '%s': %s", query, exc)

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
            if len(rows) >= limit * CANDIDATE_MULTIPLIER:
                break
            mirror_url = f"{DDG_JINA_MIRROR}?q={quote_plus(variant)}"
            try:
                response = requests.get(mirror_url, timeout=30)
                response.raise_for_status()
            except Exception as exc:
                logger.warning("Mirror discovery failed for variant '%s': %s", variant, exc)
                continue
            text = response.text
            for match in re.finditer(r"## \[(.*?)\]\((https?://[^)]+)\)", text):
                title = match.group(1).strip()
                url = _decode_ddg_redirect(match.group(2).strip())
                if not title or not url or url in seen or not _is_scholarly_url(url):
                    continue
                context = re.sub(r"\s+", " ", text[match.end(): match.end() + 220]).strip()
                seen.add(url)
                rows.append({"title": title, "url": url, "snippet": context})
                if len(rows) >= limit * CANDIDATE_MULTIPLIER:
                    break

    return rows


def _crossref_item_to_meta(item: Dict[str, Any], fallback_title: str = "") -> Optional[Dict[str, Any]]:
    if not item:
        return None

    authors = []
    for author in item.get("author", []) or []:
        given = (author.get("given") or "").strip()
        family = (author.get("family") or "").strip()
        full = f"{given} {family}".strip()
        if full:
            authors.append(full)

    year = "n.d."
    date_parts = (item.get("issued") or {}).get("date-parts") or []
    if date_parts and date_parts[0]:
        year = str(date_parts[0][0])

    container = item.get("container-title") or []
    source = container[0] if container else ""
    doi = (item.get("DOI") or "").strip()
    url = (item.get("URL") or "").strip()

    titles = item.get("title") or []
    title = titles[0].strip() if titles else fallback_title

    return {
        "title": title or fallback_title,
        "authors": authors,
        "year": year,
        "source": source,
        "doi": doi,
        "abstract": "",
        "url": url,
    }


def _search_crossref_query(query: str, limit: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    seen = set()

    try:
        response = requests.get(
            CROSSREF_URL,
            params={"query": query, "rows": max(limit * 4, 60)},
            timeout=25,
        )
        response.raise_for_status()
    except Exception as exc:
        logger.warning("Crossref query fallback failed for '%s': %s", query, exc)
        return rows

    items = (response.json().get("message") or {}).get("items") or []
    for item in items:
        titles = item.get("title") or []
        title = titles[0].strip() if titles else ""
        if not title:
            continue

        doi = (item.get("DOI") or "").strip()
        url = (item.get("URL") or "").strip()
        if doi and not url:
            url = f"https://doi.org/{doi}"
        if not url:
            continue

        key = f"{title.lower()}::{url.lower()}"
        if key in seen:
            continue
        seen.add(key)

        container = item.get("container-title") or []
        snippet = container[0].strip() if container else ""

        rows.append({
            "title": title,
            "url": url,
            "snippet": snippet,
            "crossref_item": item,
        })
        if len(rows) >= limit * CANDIDATE_MULTIPLIER:
            break

    return rows


def _query_variants(query: str) -> List[str]:
    """Generate a small set of high-signal query variants for Crossref fallback."""
    base = re.sub(r"\s+", " ", str(query or "")).strip()
    if not base:
        return []

    tokens = [t for t in re.findall(r"[A-Za-z0-9+-]+", base) if len(t) > 2]
    core = " ".join(tokens[:8]) if tokens else base

    variants = [
        base,
        f"{core} survey",
        f"{core} review",
        f"{core} recent advances",
    ]

    deduped: List[str] = []
    seen = set()
    for variant in variants:
        normalized = variant.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(variant.strip())
        if len(deduped) >= MAX_QUERY_VARIANTS:
            break
    return deduped


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


def _compact_url(url: str, max_len: int = 96) -> str:
    raw = str(url or "").strip()
    if not raw:
        return ""
    if len(raw) <= max_len:
        return raw

    parsed = urlparse(raw)
    host = (parsed.netloc or "").strip()
    path = (parsed.path or "").strip()
    if host:
        shortened_path = path[: max(12, max_len - len(host) - 18)]
        return f"https://{host}{shortened_path}..."
    return raw[: max_len - 3] + "..."


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
            elif item.url:
                line += f" URL: {_compact_url(item.url)}"
        elif s == "APA":
            line = f"[{idx}] {authors} ({item.year}). {item.title}. {item.source}."
            if item.doi:
                line += f" doi: {item.doi}"
        elif s == "MLA":
            line = f"[{idx}] {authors}. \"{item.title}.\" {item.source}, {item.year}."
            if item.doi:
                line += f" doi: {item.doi}"
        elif s == "CHICAGO":
            line = f"[{idx}] {authors}. {item.year}. \"{item.title}.\" {item.source}."
            if item.doi:
                line += f" doi: {item.doi}."
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


def generate_references(
    query: str,
    limit: int = DEFAULT_LIMIT,
    style: str = DEFAULT_STYLE,
    excluded_titles: Optional[List[str]] = None,
) -> Dict[str, Any]:
    excluded_title_norms = {
        _normalize_title(title)
        for title in (excluded_titles or [])
        if _normalize_title(title)
    }

    memory_entries = _load_reference_memory()
    memory_titles = [entry.get("title_norm", "") for entry in memory_entries if entry.get("title_norm")]
    memory_signatures = {
        str(entry.get("signature", "")).strip()
        for entry in memory_entries
        if str(entry.get("signature", "")).strip()
    }
    prioritize_target_count = limit >= REFERENCE_NEAR_TARGET_MIN
    query_terms = _query_terms(query)

    candidates: List[Dict[str, Any]] = []
    candidate_keys = set()

    def _append_candidate_list(rows: List[Dict[str, Any]]) -> None:
        for row in rows:
            title = str(row.get("title", "")).strip().lower()
            url = str(row.get("url", "")).strip().lower()
            key = f"{title}::{url}"
            if not title or not url or key in candidate_keys:
                continue
            candidate_keys.add(key)
            candidates.append(row)
            if len(candidates) >= limit * CANDIDATE_MULTIPLIER:
                return

    try:
        _append_candidate_list(_search_ddg(query, limit))
    except Exception as exc:
        logger.warning("Primary discovery failed for '%s': %s", query, exc)

    search_queries = _query_variants(query) if prioritize_target_count else [query]
    for variant in search_queries:
        try:
            _append_candidate_list(_search_crossref_query(variant, limit))
        except Exception as exc:
            logger.warning("Crossref fallback failed for '%s': %s", variant, exc)
        if len(candidates) >= limit * CANDIDATE_MULTIPLIER:
            break

    references: List[ReferenceItem] = []
    seen_titles = set()
    accepted_titles: List[str] = []
    accepted_signatures = set()
    skipped_duplicates = 0
    filtered_non_academic = 0

    for cand in candidates:
        if len(references) >= limit:
            break

        title = str(cand.get("title", "")).strip()
        if not title:
            continue

        norm_title = _normalize_title(title)
        if not norm_title:
            continue

        if _looks_offtopic_short_title(title, query_terms):
            skipped_duplicates += 1
            continue

        if norm_title in excluded_title_norms:
            skipped_duplicates += 1
            continue
        if norm_title in seen_titles:
            skipped_duplicates += 1
            continue
        if _is_fuzzy_duplicate(norm_title, accepted_titles):
            skipped_duplicates += 1
            continue
        if (not prioritize_target_count) and _is_fuzzy_duplicate(norm_title, memory_titles):
            skipped_duplicates += 1
            continue

        meta = None
        crossref_item = cand.get("crossref_item") if isinstance(cand, dict) else None
        if crossref_item:
            meta = _crossref_item_to_meta(crossref_item, title)

        if not meta:
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
            meta = {
                "title": title,
                "authors": cand.get("authors") or [],
                "year": _extract_year(cand.get("snippet", "")),
                "source": urlparse(cand.get("url", "")).netloc,
                "doi": "",
                "abstract": cand.get("snippet", ""),
                "url": cand.get("url", ""),
            }

        final_title = (meta.get("title") or title).strip()
        final_doi = (meta.get("doi") or "").strip()
        final_url = (meta.get("url") or cand.get("url") or "").strip()
        if _looks_offtopic_short_title(final_title, query_terms):
            skipped_duplicates += 1
            continue
        final_norm_title = _normalize_title(final_title) or norm_title
        final_signature = _reference_signature(final_title, final_doi, final_url)

        if final_signature in accepted_signatures or ((not prioritize_target_count) and final_signature in memory_signatures):
            skipped_duplicates += 1
            continue
        if final_norm_title in seen_titles or final_norm_title in excluded_title_norms:
            skipped_duplicates += 1
            continue
        if _is_fuzzy_duplicate(final_norm_title, accepted_titles):
            skipped_duplicates += 1
            continue
        if (not prioritize_target_count) and _is_fuzzy_duplicate(final_norm_title, memory_titles):
            skipped_duplicates += 1
            continue

        verification = is_verified_academic_paper(
            {
                "title": final_title,
                "url": final_url,
                "doi": final_doi,
                "year": str(meta.get("year") or _extract_year(cand.get("snippet", ""))),
                "source": str(meta.get("source") or "").strip(),
                "authors": meta.get("authors") or [],
            },
            query_terms=query_terms,
        )
        if not verification["is_academic_paper"]:
            filtered_non_academic += 1
            continue

        authors = [a for a in (meta.get("authors") or []) if a and a.lower() != "unknown"]
        if not authors:
            authors = ["Unknown Author"]

        source = (meta.get("source") or "").strip() or urlparse(cand.get("url", "")).netloc

        references.append(
            ReferenceItem(
                title=final_title,
                url=final_url,
                source=source,
                authors=authors,
                year=str(meta.get("year") or _extract_year(cand.get("snippet", ""))),
                doi=final_doi,
                abstract=(meta.get("abstract") or cand.get("snippet") or "").strip(),
                item_type=verification["item_type"],
                is_academic_paper=True,
                verification_reason=verification["reason"],
            )
        )

        seen_titles.add(final_norm_title)
        accepted_titles.append(final_norm_title)
        accepted_signatures.add(final_signature)

    references.sort(key=lambda r: int(r.year) if r.year.isdigit() else 9999)

    now_iso = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    updated_memory = list(memory_entries)
    for ref in references:
        updated_memory.append(
            {
                "signature": _reference_signature(ref.title, ref.doi, ref.url),
                "title_norm": _normalize_title(ref.title),
                "title": ref.title,
                "doi": ref.doi,
                "url": ref.url,
                "source": ref.source,
                "year": ref.year,
                "last_seen": now_iso,
            }
        )
    deduped_memory = _dedupe_memory_entries(updated_memory)
    _save_reference_memory(deduped_memory)

    pyz = pyzotero_capabilities()
    requested_csl = STYLE_TO_CSL.get(style.upper(), style.lower())
    available_formats = {str(f).strip().lower() for f in pyz.get("formats", [])}
    pyz["requested_style"] = requested_csl
    pyz["requested_style_supported"] = requested_csl in available_formats if pyz.get("available") else False
    pyz["verification_note"] = (
        "Reference entries are filtered to academic-paper candidates using DOI/domain/metadata checks; "
        "pyzotero availability is also checked for CSL style compatibility."
    )

    return {
        "query": query,
        "count": len(references),
        "style": style.upper(),
        "style_name": STYLE_NAMES.get(style.upper(), style.upper()),
        "papers": [r.to_zotero_like() for r in references],
        "formatted_references": format_references(references, style),
        "source_domains": SCHOLARLY_DOMAINS,
        "pyzotero": pyz,
        "generated_at": now_iso,
        "dedup_stats": {
            "skipped_duplicates": skipped_duplicates,
            "filtered_non_academic": filtered_non_academic,
            "memory_entries": len(deduped_memory),
            "excluded_titles": len(excluded_title_norms),
        },
    }
