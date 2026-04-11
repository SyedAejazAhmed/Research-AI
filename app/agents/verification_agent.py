"""Verification agent for generated report integrity and source traceability."""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


EXPECTED_SECTION_ORDER = [
    "introduction",
    "related_studies",
    "methodology",
    "result_discussion",
    "conclusion",
    "references",
]


class VerificationAgent:
    """Validate generated content consistency and persist source logs."""

    def __init__(self, output_dir: str = "outputs"):
        self.name = "Verification Agent"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    async def verify(
        self,
        synthesis: Dict[str, Any],
        aggregated_data: Dict[str, Any],
        citations: Dict[str, Any],
        session_id: str,
        callback=None,
    ) -> Dict[str, Any]:
        if callback:
            await callback("verifier", "checking", "Validating references and collecting source trace log...")

        abstract = str(synthesis.get("abstract") or "")
        sections = synthesis.get("sections") or []

        section_checks = self._check_sections(abstract, sections)
        citation_checks = self._check_citations(abstract, sections, citations)
        sources = self._collect_sources(
            aggregated_data=aggregated_data,
            citations=citations,
            cited_numbers=set(citation_checks.get("cited_numbers", [])),
        )

        source_log_payload = {
            "session_id": session_id,
            "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "source_count": len(sources),
            "sources": sources,
        }
        source_log_path = self.output_dir / f"{session_id}_sources_log.json"
        source_log_path.write_text(json.dumps(source_log_payload, indent=2), encoding="utf-8")

        summary = {
            "sections_complete": not section_checks["missing_sections"],
            "references_present": section_checks["references_present"],
            "inline_citation_count": len(citation_checks["cited_numbers"]),
            "reference_count": len(citation_checks["available_reference_numbers"]),
            "missing_reference_numbers": citation_checks["missing_reference_numbers"],
            "uncited_reference_numbers": citation_checks["uncited_reference_numbers"],
            "numbering_contiguous": citation_checks["numbering_contiguous"],
            "source_count": len(sources),
        }

        verification_payload = {
            "session_id": session_id,
            "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "summary": summary,
            "section_checks": section_checks,
            "citation_checks": citation_checks,
        }
        verification_log_path = self.output_dir / f"{session_id}_verification_log.json"
        verification_log_path.write_text(json.dumps(verification_payload, indent=2), encoding="utf-8")

        if callback:
            await callback(
                "verifier",
                "completed",
                f"Verification complete: {len(sources)} sources logged; {len(citation_checks['missing_reference_numbers'])} missing reference link(s).",
            )

        return {
            "agent": self.name,
            "summary": summary,
            "source_log": str(source_log_path),
            "verification_log": str(verification_log_path),
            "section_checks": section_checks,
            "citation_checks": citation_checks,
        }

    @staticmethod
    def _parse_citation_numbers(text: str) -> Set[int]:
        return {int(n) for n in re.findall(r"\[(\d+)\]", text or "")}

    @staticmethod
    def _safe_int(value: Any) -> Optional[int]:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _check_sections(self, abstract: str, sections: List[Dict[str, Any]]) -> Dict[str, Any]:
        section_keys = [str(s.get("key") or "").strip() for s in sections if s.get("key")]
        missing_sections = [k for k in EXPECTED_SECTION_ORDER if k not in section_keys]

        ordered_subset = [k for k in section_keys if k in EXPECTED_SECTION_ORDER]
        expected_subset = [k for k in EXPECTED_SECTION_ORDER if k in section_keys]

        references_content = ""
        for section in sections:
            if section.get("key") == "references":
                references_content = str(section.get("content") or "")
                break

        return {
            "abstract_present": bool((abstract or "").strip()),
            "references_present": bool(references_content.strip()),
            "missing_sections": missing_sections,
            "section_order_valid": ordered_subset == expected_subset,
            "section_keys": section_keys,
        }

    def _check_citations(
        self,
        abstract: str,
        sections: List[Dict[str, Any]],
        citations: Dict[str, Any],
    ) -> Dict[str, Any]:
        narrative_parts = [abstract]
        references_text = ""
        for section in sections:
            key = str(section.get("key") or "").strip().lower()
            content = str(section.get("content") or "")
            if key == "references":
                references_text = content
                continue
            narrative_parts.append(content)

        cited_numbers = sorted(self._parse_citation_numbers("\n".join(narrative_parts)))

        available_numbers = set()
        for cite in citations.get("citations") or []:
            number = self._safe_int(cite.get("number"))
            if number is not None:
                available_numbers.add(number)

        references_section_numbers = sorted(self._parse_citation_numbers(references_text))

        if not available_numbers and references_section_numbers:
            available_numbers = set(references_section_numbers)

        sorted_available = sorted(available_numbers)
        missing_reference_numbers = sorted(set(cited_numbers) - available_numbers)
        uncited_reference_numbers = sorted(available_numbers - set(cited_numbers))

        contiguous_expected = list(range(1, len(sorted_available) + 1))

        return {
            "cited_numbers": cited_numbers,
            "available_reference_numbers": sorted_available,
            "references_section_numbers": references_section_numbers,
            "missing_reference_numbers": missing_reference_numbers,
            "uncited_reference_numbers": uncited_reference_numbers,
            "numbering_contiguous": sorted_available == contiguous_expected,
        }

    def _collect_sources(
        self,
        aggregated_data: Dict[str, Any],
        citations: Dict[str, Any],
        cited_numbers: Set[int],
    ) -> List[Dict[str, Any]]:
        by_key: Dict[str, Dict[str, Any]] = {}

        def _identity(title: str, url: str, doi: str) -> str:
            d = (doi or "").strip().lower()
            if d:
                return f"doi:{d}"
            u = (url or "").strip().lower()
            if u:
                return f"url:{u}"
            t = re.sub(r"[^a-z0-9\s]", "", (title or "").strip().lower())
            t = re.sub(r"\s+", " ", t).strip()
            return f"title:{t}"

        def _upsert(source: Dict[str, Any]) -> None:
            key = _identity(
                str(source.get("title") or ""),
                str(source.get("url") or ""),
                str(source.get("doi") or ""),
            )
            if key in by_key:
                existing = by_key[key]
                origins = set(existing.get("origins", []))
                origins.update(source.get("origins", []))
                existing["origins"] = sorted(origins)
                if not existing.get("source") and source.get("source"):
                    existing["source"] = source.get("source")
                if not existing.get("year") and source.get("year"):
                    existing["year"] = source.get("year")
                if not existing.get("authors") and source.get("authors"):
                    existing["authors"] = source.get("authors")
                if source.get("reference_numbers"):
                    existing_numbers = set(existing.get("reference_numbers", []))
                    existing_numbers.update(source.get("reference_numbers", []))
                    existing["reference_numbers"] = sorted(existing_numbers)
                existing["cited_in_text"] = bool(existing.get("cited_in_text") or source.get("cited_in_text"))
                return
            by_key[key] = source

        for cite in citations.get("citations") or []:
            paper = cite.get("paper") or {}
            number = self._safe_int(cite.get("number"))
            _upsert(
                {
                    "title": str(paper.get("title") or "Untitled"),
                    "url": str(paper.get("url") or ""),
                    "doi": str(cite.get("doi") or paper.get("doi") or ""),
                    "source": str(paper.get("source") or ""),
                    "year": str(paper.get("year") or ""),
                    "authors": paper.get("authors") or [],
                    "type": "citation",
                    "origins": ["citation"],
                    "reference_numbers": [number] if number is not None else [],
                    "cited_in_text": bool(number in cited_numbers) if number is not None else False,
                }
            )

        for item in aggregated_data.get("all_content") or []:
            _upsert(
                {
                    "title": str(item.get("title") or "Untitled"),
                    "url": str(item.get("url") or ""),
                    "doi": str(item.get("doi") or ""),
                    "source": str(item.get("source") or ""),
                    "year": str(item.get("year") or ""),
                    "authors": item.get("authors") or [],
                    "type": str(item.get("type") or "unknown"),
                    "origins": ["aggregated"],
                    "reference_numbers": [],
                    "cited_in_text": False,
                }
            )

        output = list(by_key.values())
        output.sort(key=lambda s: (str(s.get("title") or "").lower(), str(s.get("url") or "")))
        return output
