"""Tests for reference deduplication (exact, fuzzy, and memory-based)."""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.utils import references as refmod


def _slug(text: str) -> str:
    return "-".join(text.lower().split())


def _fake_semantic(title: str):
    return {
        "title": title,
        "authors": ["Jane Doe"],
        "year": "2024",
        "source": "IEEE Access",
        "doi": "",
        "abstract": "",
        "url": f"https://example.org/{_slug(title)}",
    }


def test_generate_references_removes_exact_and_fuzzy_duplicates(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(refmod, "REFERENCE_MEMORY_PATH", tmp_path / "reference_memory.json")
    monkeypatch.setattr(
        refmod,
        "_search_ddg",
        lambda query, limit: [
            {"title": "A Novel Method for AI Diagnosis", "url": "https://example.org/p1", "snippet": "2024"},
            {"title": "A novel method for AI diagnosis", "url": "https://example.org/p2", "snippet": "2024"},
            {"title": "A Novel Method for AI-Based Diagnosis", "url": "https://example.org/p3", "snippet": "2024"},
            {"title": "Clinical Data Curation with LLMs", "url": "https://example.org/p4", "snippet": "2023"},
        ],
    )
    monkeypatch.setattr(refmod, "_search_crossref_query", lambda query, limit: [])
    monkeypatch.setattr(refmod, "_enrich_semantic_scholar", _fake_semantic)
    monkeypatch.setattr(refmod, "_enrich_crossref", lambda title: None)

    result = refmod.generate_references("medical ai", limit=10, style="IEEE")

    titles = [paper["title"] for paper in result["papers"]]
    assert len(titles) == 2
    assert "A Novel Method for AI Diagnosis" in titles
    assert "Clinical Data Curation with LLMs" in titles


def test_reference_memory_skips_reused_references_on_next_generation(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(refmod, "REFERENCE_MEMORY_PATH", tmp_path / "reference_memory.json")
    monkeypatch.setattr(refmod, "_search_crossref_query", lambda query, limit: [])
    monkeypatch.setattr(refmod, "_enrich_semantic_scholar", _fake_semantic)
    monkeypatch.setattr(refmod, "_enrich_crossref", lambda title: None)

    calls = {"count": 0}

    def _search(query, limit):
        calls["count"] += 1
        if calls["count"] == 1:
            return [
                {"title": "Reliable Vision-Language Diagnostics", "url": "https://example.org/a", "snippet": "2024"},
                {"title": "Foundation Models in Clinical Workflows", "url": "https://example.org/b", "snippet": "2024"},
            ]
        return [
            {"title": "Reliable vision language diagnostics", "url": "https://example.org/a2", "snippet": "2024"},
            {"title": "Foundation Models in Clinical Workflows", "url": "https://example.org/b", "snippet": "2024"},
            {"title": "Novel Calibration Strategies for Clinical LLMs", "url": "https://example.org/c", "snippet": "2025"},
        ]

    monkeypatch.setattr(refmod, "_search_ddg", _search)

    first = refmod.generate_references("clinical llm", limit=5, style="IEEE")
    second = refmod.generate_references("clinical llm", limit=5, style="IEEE")

    assert first["count"] == 2
    assert second["count"] == 1
    assert second["papers"][0]["title"] == "Novel Calibration Strategies for Clinical LLMs"
    assert second["dedup_stats"]["skipped_duplicates"] >= 2


def test_excluded_titles_filter_matches_case_insensitive(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(refmod, "REFERENCE_MEMORY_PATH", tmp_path / "reference_memory.json")
    monkeypatch.setattr(
        refmod,
        "_search_ddg",
        lambda query, limit: [
            {"title": "Federated Learning for MRI Analysis", "url": "https://example.org/mri", "snippet": "2022"},
            {"title": "Interpretable Diagnostics with LLMs", "url": "https://example.org/llm", "snippet": "2023"},
        ],
    )
    monkeypatch.setattr(refmod, "_search_crossref_query", lambda query, limit: [])
    monkeypatch.setattr(refmod, "_enrich_semantic_scholar", _fake_semantic)
    monkeypatch.setattr(refmod, "_enrich_crossref", lambda title: None)

    result = refmod.generate_references(
        "diagnostics",
        limit=5,
        style="HARVARD",
        excluded_titles=["federated learning for mri analysis"],
    )

    titles = [paper["title"] for paper in result["papers"]]
    assert "Federated Learning for MRI Analysis" not in titles
    assert "Interpretable Diagnostics with LLMs" in titles
