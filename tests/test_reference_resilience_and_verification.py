"""Regression tests for reference fallback resilience and verification logging."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agents.verification_agent import VerificationAgent
from app.utils import references as refmod


def _crossref_candidate() -> dict:
    crossref_item = {
        "title": ["Robust Medical AI with Language Models"],
        "author": [{"given": "Jane", "family": "Doe"}],
        "issued": {"date-parts": [[2024, 1, 1]]},
        "container-title": ["IEEE Access"],
        "DOI": "10.1000/sample.doi",
        "URL": "https://doi.org/10.1000/sample.doi",
    }
    return {
        "title": "Robust Medical AI with Language Models",
        "url": "https://doi.org/10.1000/sample.doi",
        "snippet": "IEEE Access",
        "crossref_item": crossref_item,
    }


def test_generate_references_uses_crossref_query_fallback(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(refmod, "REFERENCE_MEMORY_PATH", tmp_path / "reference_memory.json")
    monkeypatch.setattr(refmod, "_search_ddg", lambda query, limit: [])
    monkeypatch.setattr(refmod, "_search_crossref_query", lambda query, limit: [_crossref_candidate()])

    result = refmod.generate_references("medical llm diagnosis", limit=5, style="IEEE")

    assert result["count"] == 1
    assert "[1]" in result["formatted_references"]
    assert "10.1000/sample.doi" in result["formatted_references"]


def test_generate_references_handles_primary_discovery_exception(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(refmod, "REFERENCE_MEMORY_PATH", tmp_path / "reference_memory.json")

    def _boom(query, limit):
        raise RuntimeError("discovery blocked")

    monkeypatch.setattr(refmod, "_search_ddg", _boom)
    monkeypatch.setattr(refmod, "_search_crossref_query", lambda query, limit: [_crossref_candidate()])

    result = refmod.generate_references("federated healthcare ai", limit=5, style="HARVARD")

    assert result["count"] == 1
    assert "Harvard" in result["style_name"]


def test_verification_agent_saves_source_and_verification_logs(tmp_path: Path) -> None:
    agent = VerificationAgent(output_dir=str(tmp_path))

    synthesis = {
        "title": "Verification Smoke",
        "abstract": "This work evaluates pipelines with evidence [1].",
        "full_report": "Abstract [1] Introduction [1]",
        "sections": [
            {"key": "introduction", "title": "Introduction", "content": "Background with citation [1]."},
            {"key": "related_studies", "title": "Related Studies", "content": "Prior work [1]."},
            {"key": "methodology", "title": "Methodology", "content": "Method details [1]."},
            {"key": "result_discussion", "title": "Result and Discussion", "content": "Results [1]."},
            {"key": "conclusion", "title": "Conclusion", "content": "Conclusion [1]."},
            {"key": "references", "title": "References", "content": "[1] J. Doe, \"Robust Medical AI with Language Models,\" IEEE Access, 2024."},
        ],
    }

    aggregated_data = {
        "all_content": [
            {
                "title": "Robust Medical AI with Language Models",
                "url": "https://doi.org/10.1000/sample.doi",
                "doi": "10.1000/sample.doi",
                "source": "IEEE Access",
                "authors": ["Jane Doe"],
                "year": "2024",
                "type": "academic",
            }
        ]
    }

    citations = {
        "citations": [
            {
                "number": 1,
                "formatted": "[1] J. Doe, \"Robust Medical AI with Language Models,\" IEEE Access, 2024.",
                "doi": "10.1000/sample.doi",
                "verified": True,
                "paper": {
                    "title": "Robust Medical AI with Language Models",
                    "authors": ["Jane Doe"],
                    "year": "2024",
                    "url": "https://doi.org/10.1000/sample.doi",
                    "doi": "10.1000/sample.doi",
                    "source": "IEEE Access",
                },
            }
        ],
        "total": 1,
        "style": "IEEE",
    }

    result = asyncio.run(
        agent.verify(
            synthesis=synthesis,
            aggregated_data=aggregated_data,
            citations=citations,
            session_id="verifytest",
        )
    )

    source_log = Path(result["source_log"])
    verification_log = Path(result["verification_log"])

    assert source_log.exists()
    assert verification_log.exists()

    source_payload = json.loads(source_log.read_text(encoding="utf-8"))
    verification_payload = json.loads(verification_log.read_text(encoding="utf-8"))

    assert source_payload["source_count"] >= 1
    assert verification_payload["summary"]["reference_count"] == 1
    assert verification_payload["summary"]["sections_complete"] is True
