"""Regression tests for planner/synthesizer academic section flow."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agents.planner import PlannerAgent
from app.agents.synthesizer import SynthesizerAgent, SECTION_WORD_BOUNDS


def test_planner_default_sections_abstract_first_order() -> None:
    planner = PlannerAgent(llm_client=None)
    sections = planner._default_sections("federated learning in healthcare")
    titles = [s["title"] for s in sections]

    assert titles == [
        "Abstract",
        "Introduction",
        "Related Studies",
        "Methodology",
        "Result and Discussion",
        "Conclusion",
        "References",
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
        "abstract",
        "introduction",
        "related_studies",
        "methodology",
        "result_discussion",
        "conclusion",
        "references",
    ]
    assert result["sections"][-1]["key"] == "references"


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


def test_synthesizer_normalize_ieee_text_removes_markdown_links() -> None:
    raw = "Prior work reports strong gains [Example Study](https://example.org/study) and reproducibility."
    cleaned = SynthesizerAgent._normalize_ieee_text(raw)

    assert "[Example Study](https://example.org/study)" not in cleaned
    assert "Example Study" in cleaned
    assert "https://example.org/study" not in cleaned


def test_synthesizer_normalize_ieee_text_preserves_line_structure() -> None:
    raw = (
        "Physics-Based Restoration Techniques\n"
        "These methods leverage attenuation models.\n\n"
        "Domain Adaptation\n"
        "Feature alignment improves transfer."
    )
    cleaned = SynthesizerAgent._normalize_ieee_text(raw)

    assert "\n\n" in cleaned
    assert "Physics-Based Restoration Techniques\nThese methods" in cleaned


def test_synthesizer_finalize_section_text_handles_truncated_tail() -> None:
    raw = "First sentence is complete. Second sentence is complete. Third sentence is cut"
    cleaned = SynthesizerAgent._finalize_section_text(raw)

    assert cleaned.endswith(".")
    assert "Third sentence is cut" not in cleaned


class _AlwaysShortLLM:
    is_available = True

    async def generate(self, prompt: str, max_tokens: int = 600, temperature: float = 0.2) -> str:
        return " ".join(["evidence"] * 40)


def test_synthesizer_enforces_strict_word_bounds_when_llm_undergenerates() -> None:
    synthesizer = SynthesizerAgent(llm_client=_AlwaysShortLLM())

    aggregated_data = {
        "plan": {
            "title": "Underwater Image Enhancement for Maritime Security",
            "keywords": ["underwater", "enhancement", "maritime"],
        },
        "all_content": [],
        "sections_context": [],
        "citations_text": "## References\n\n[1] Example citation.",
        "total_sources": 5,
        "academic_sources": 5,
    }

    result = asyncio.run(synthesizer.synthesize(aggregated_data))

    abstract_wc = len(result["abstract"].split())
    assert 150 <= abstract_wc <= 250

    for section in result["sections"]:
        key = section.get("key")
        if key not in SECTION_WORD_BOUNDS:
            continue
        min_w, max_w = SECTION_WORD_BOUNDS[key]
        wc = len((section.get("content") or "").split())
        assert min_w <= wc <= max_w
