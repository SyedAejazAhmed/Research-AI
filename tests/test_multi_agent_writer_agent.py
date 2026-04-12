"""Tests for robust multi_agent WriterAgent behavior."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from multi_agent.agents.writer import WriterAgent


def test_writer_agent_fallback_without_model() -> None:
    agent = WriterAgent()
    research_state = {
        "title": "Underwater Image Enhancement",
        "research_data": [
            "Method uses GAN-based enhancement with domain adaptation.",
            "Evaluation compares PSNR and SSIM across multiple datasets.",
        ],
        "task": {
            "citation_style": "IEEE",
            "follow_guidelines": False,
            "verbose": False,
            "model": None,
        },
    }

    payload = asyncio.run(agent.write_sections(research_state))

    assert isinstance(payload, dict)
    assert payload.get("introduction")
    assert payload.get("conclusion")
    assert isinstance(payload.get("sources"), list)


def test_writer_agent_normalizes_ieee_sources_numbering() -> None:
    agent = WriterAgent()
    payload = {
        "table_of_contents": "- A\n- B",
        "introduction": "Intro",
        "conclusion": "Outro",
        "sources": [
            "1. First source",
            "[7] Seventh source",
            "Plain source entry",
        ],
    }

    normalized = agent._normalize_layout(
        payload=payload,
        query="Sample",
        data=["https://example.com"],
        citation_style="IEEE",
    )

    assert normalized["sources"][0].startswith("[1]")
    assert normalized["sources"][1].startswith("[2]")
    assert normalized["sources"][2].startswith("[3]")
