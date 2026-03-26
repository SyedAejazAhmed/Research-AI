"""Regression tests for planner/synthesizer academic section flow."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agents.planner import PlannerAgent
from app.agents.synthesizer import SynthesizerAgent


def test_planner_default_sections_reference_first_order() -> None:
    planner = PlannerAgent(llm_client=None)
    sections = planner._default_sections("federated learning in healthcare")
    titles = [s["title"] for s in sections]

    assert titles == [
        "References",
        "Abstract",
        "Introduction",
        "Related Studies",
        "Methodology",
        "Result and Discussion",
        "Conclusion",
    ]


def test_synthesizer_emits_sections_in_strict_order() -> None:
    synthesizer = SynthesizerAgent(llm_client=None)

    aggregated_data = {
        "plan": {
            "title": "Federated Learning in Healthcare",
            "keywords": ["federated learning", "healthcare", "privacy"],
        },
        "all_content": [],
        "sections_context": [],
        "citations_text": "## References\n[1] Example citation.",
        "total_sources": 1,
        "academic_sources": 1,
    }

    seen_order = []

    async def cb(agent, status, message, data=None):
        if status == "section_ready" and isinstance(data, dict):
            seen_order.append(data.get("key"))

    result = asyncio.run(synthesizer.synthesize(aggregated_data, callback=cb))

    assert seen_order == [
        "references",
        "abstract",
        "introduction",
        "related_studies",
        "methodology",
        "result_discussion",
        "conclusion",
    ]
    assert result["sections"][0]["key"] == "references"


class _FakeUnavailableLLM:
    is_available = True

    async def generate(self, prompt: str, max_tokens: int = 600, **kwargs) -> str:
        return "Local LLM (Ollama) is not currently available. Please install Ollama."


def test_synthesizer_sanitizes_unavailable_ollama_text() -> None:
    synthesizer = SynthesizerAgent(llm_client=_FakeUnavailableLLM())

    aggregated_data = {
        "plan": {
            "title": "Privacy-Preserving Clinical AI",
            "keywords": ["privacy", "clinical ai"],
        },
        "all_content": [],
        "sections_context": [],
        "citations_text": "## References\n[1] Example citation.",
        "total_sources": 1,
        "academic_sources": 1,
    }

    result = asyncio.run(synthesizer.synthesize(aggregated_data))

    bad_phrase = "local llm (ollama) is not currently available"
    assert bad_phrase not in result["abstract"].lower()
    for section in result["sections"]:
        assert bad_phrase not in section["content"].lower()


def test_synthesizer_token_budget_scales_with_word_target() -> None:
    # 1200-word sections should not be capped at very low token limits.
    assert SynthesizerAgent._token_budget(1200) >= 2400


class _RewriteLLM:
    is_available = True

    async def generate(self, prompt: str, max_tokens: int = 600, temperature: float = 0.3) -> str:
        return " ".join(["evidence"] * 220)


def test_enforce_word_target_expands_short_abstract() -> None:
    synthesizer = SynthesizerAgent(llm_client=_RewriteLLM())
    short_text = "Too short abstract text."

    result = asyncio.run(
        synthesizer._enforce_word_target(
            section_key="abstract",
            section_title="Abstract",
            text=short_text,
            plan={"title": "Test"},
            unified_context="",
        )
    )

    wc = len(result.split())
    assert 150 <= wc <= 250
