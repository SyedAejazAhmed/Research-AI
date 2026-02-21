"""
Yukti Research AI - Synthesizer Agent
=======================================
Uses Local LLM (Ollama) to produce an academic paper with fixed structure:

  Title → Abstract → Introduction → Related Studies →
  Methodology → Result and Discussion → Conclusion → References

Features:
- Fixed 7-section academic format (not planner-driven)
- Each section fires a ``section_ready`` callback for frontend review
- Parallel LLM generation (abstract + 5 body sections simultaneously)
- Citation-aware generation
- Source grounding to prevent hallucination
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)

# Fixed academic sections (excluding Abstract and References — handled separately)
ACADEMIC_SECTIONS = [
    {
        "key": "introduction",
        "title": "Introduction",
        "focus": "background, problem statement, motivation, and research objectives",
        "instructions": (
            "Write the Introduction covering: (1) background and context of the topic, "
            "(2) the problem being addressed, (3) motivation for the research, "
            "(4) research objectives. Cite relevant sources."
        ),
    },
    {
        "key": "related_studies",
        "title": "Related Studies",
        "focus": "existing literature, prior work, and comparative analysis",
        "instructions": (
            "Review and synthesise related work. Discuss prior approaches, "
            "existing methodologies, and their limitations. Group by theme or approach. "
            "Use numbered citations."
        ),
    },
    {
        "key": "methodology",
        "title": "Methodology",
        "focus": "approach, methods, datasets, models, and experimental setup",
        "instructions": (
            "Describe the methodology: data sources, research approach, any models "
            "or algorithms referenced, and the analytical framework. Be precise and structured."
        ),
    },
    {
        "key": "result_discussion",
        "title": "Result and Discussion",
        "focus": "findings, analysis, comparisons, and interpretation",
        "instructions": (
            "Present and discuss the findings from the research. Highlight key "
            "results, compare with related work, and interpret their significance. "
            "Reference supporting sources."
        ),
    },
    {
        "key": "conclusion",
        "title": "Conclusion",
        "focus": "summary, contributions, limitations, and future directions",
        "instructions": (
            "Summarise the main findings and contributions. State limitations of the "
            "current study and suggest future research directions. Keep to 150–250 words."
        ),
    },
]


class SynthesizerAgent:
    """
    LLM Synthesis Layer: produces a structured academic paper from aggregated data.

    Fixed academic sections: Abstract, Introduction, Related Studies,
    Methodology, Result and Discussion, Conclusion, References.

    Each completed section fires a ``section_ready`` callback so the frontend
    can display sections one-by-one for review.
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.name = "Synthesizer Agent"

    # -----------------------------------------------------------------------
    # Public entry point
    # -----------------------------------------------------------------------

    async def synthesize(
        self,
        aggregated_data: Dict[str, Any],
        callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """
        Synthesize a full academic research paper from aggregated data.

        Extended callback signature (4th param is optional)::

            await callback(agent, status, message, data=None)

        Special statuses emitted:
          - ``"section_ready"``  — once per section; ``data`` = section dict
          - ``"completed"``      — when all sections are assembled
        """
        if callback:
            await callback("synthesizer", "starting", "Starting academic paper synthesis …")

        plan = aggregated_data.get("plan", {})
        all_content = aggregated_data.get("all_content", [])
        sections_context = aggregated_data.get("sections_context", [])
        citations_text = aggregated_data.get("citations_text", "")

        title = plan.get("title", "Research Report")
        keywords = plan.get("keywords", [])

        unified_context = self._build_unified_context(all_content, sections_context)

        if callback:
            await callback(
                "synthesizer", "generating",
                f"Generating Abstract + {len(ACADEMIC_SECTIONS)} sections in parallel …"
            )

        # ── Parallel generation ─────────────────────────────────────────────
        async def _gen_with_callback(idx: int, section_def: Dict) -> Dict:
            content = await self._generate_section(section_def, plan, unified_context)
            section = {
                "index": idx,
                "key": section_def["key"],
                "title": section_def["title"],
                "content": content,
            }
            if callback:
                await self._safe_callback(callback, "synthesizer", "section_ready",
                                          f"Section ready: {section_def['title']}", section)
            return section

        tasks = [self._generate_abstract(plan, aggregated_data)] + [
            _gen_with_callback(i, sec) for i, sec in enumerate(ACADEMIC_SECTIONS)
        ]
        results = await asyncio.gather(*tasks)

        abstract: str = results[0]
        body_sections: List[Dict] = list(results[1:])

        # Send abstract as a section_ready event too
        abstract_section = {"index": -1, "key": "abstract", "title": "Abstract", "content": abstract}
        if callback:
            await self._safe_callback(callback, "synthesizer", "section_ready",
                                      "Section ready: Abstract", abstract_section)

        if callback:
            await callback("synthesizer", "compiling", "Compiling full report …")

        full_report = self._compile_report(title, abstract, body_sections, citations_text, keywords)

        if callback:
            await callback("synthesizer", "completed", "Report synthesis complete!")

        return {
            "agent": self.name,
            "title": title,
            "abstract": abstract,
            "sections": body_sections,
            "full_report": full_report,
            "citations": citations_text,
            "keywords": keywords,
            "word_count": len(full_report.split()),
            "timestamp": datetime.now().isoformat(),
        }

    # -----------------------------------------------------------------------
    # Abstract
    # -----------------------------------------------------------------------

    async def _generate_abstract(self, plan: Dict, data: Dict) -> str:
        if self.llm_client and self.llm_client.is_available:
            prompt = f"""Write a concise academic abstract (150–250 words) for a research paper on:

Title: {plan.get('title', '')}
Key Topics: {', '.join(plan.get('keywords', []))}
Total Sources: {data.get('total_sources', 0)}
Academic Sources: {data.get('academic_sources', 0)}

State the objective, methodology, key findings, and significance.
Academic third-person tone. Do NOT include headers or labels."""
            return await self.llm_client.generate(prompt, max_tokens=400)

        return (
            f"This paper presents a comprehensive analysis of {plan.get('title', 'the research topic')}. "
            f"Systematic research across multiple academic databases identified "
            f"{data.get('total_sources', 0)} sources, of which "
            f"{data.get('academic_sources', 0)} are verified peer-reviewed publications. "
            f"The study examines current methodologies, recent advancements, challenges, and future directions."
        )

    # -----------------------------------------------------------------------
    # Body section
    # -----------------------------------------------------------------------

    async def _generate_section(
        self, section_def: Dict, plan: Dict, unified_context: str
    ) -> str:
        if self.llm_client and self.llm_client.is_available:
            prompt = f"""Write the "{section_def['title']}" section for an academic research paper.

Research Topic: {plan.get('title', '')}
Section Focus: {section_def['focus']}

{section_def['instructions']}

Available Source Material:
{unified_context[:3000] if unified_context else 'No specific sources available.'}

Rules:
1. Write 250–450 words in academic prose
2. Use [number] citation format where applicable
3. Objective, scholarly tone — no first-person
4. Do NOT include the section title (added separately)
5. Only reference provided sources — never fabricate citations"""
            return await self.llm_client.generate(prompt, max_tokens=600)

        return (
            f"This section covers {section_def['focus']}. "
            f"Based on analysis of available literature, key findings are presented "
            f"following a systematic review of {section_def['title'].lower()} aspects. "
            f"Further investigation is recommended to provide comprehensive coverage."
        )

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _build_unified_context(all_content: List[Dict], sections_context: List[Dict]) -> str:
        """Combine and deduplicate all available research content into one context string."""
        items = list(all_content)
        for sc in sections_context:
            items.extend(sc.get("relevant_content", []))

        seen, deduped = set(), []
        for item in items:
            key = item.get("title", "") or (item.get("content", "") or "")[:50]
            if key and key not in seen:
                seen.add(key)
                deduped.append(item)

        lines = []
        for i, item in enumerate(deduped[:15], start=1):
            snippet = (item.get("content") or item.get("abstract") or "")[:400]
            doi_part = f", DOI: {item['doi']}" if item.get("doi") else ""
            lines.append(
                f"[{i}] {item.get('title', 'Untitled')} "
                f"({item.get('source', 'Unknown')}{doi_part})\n{snippet}"
            )
        return "\n\n".join(lines)

    @staticmethod
    async def _safe_callback(callback, agent, status, message, data=None):
        """Call callback with optional 4th arg, catching any errors."""
        try:
            await callback(agent, status, message, data)
        except TypeError:
            # Fallback: old 3-arg callback signature
            try:
                await callback(agent, status, message)
            except Exception:
                pass
        except Exception:
            pass

    def _compile_report(
        self,
        title: str,
        abstract: str,
        sections: List[Dict],
        citations: str,
        keywords: List[str],
    ) -> str:
        lines = [
            f"# {title}",
            "",
            f"*Generated by Yukti Research AI on {datetime.now().strftime('%B %d, %Y')}*",
            "",
            "---",
            "",
            "## Abstract",
            "",
            abstract,
            "",
        ]
        if keywords:
            lines += [f"**Keywords:** {', '.join(keywords)}", ""]

        lines += ["---", "", "## Table of Contents", ""]
        toc_entries = ["Abstract"] + [s["title"] for s in sections] + ["References"]
        for idx, name in enumerate(toc_entries, start=1):
            anchor = name.lower().replace(" ", "-")
            lines.append(f"{idx}. [{name}](#{anchor})")
        lines += ["", "---", ""]

        for i, section in enumerate(sections, start=1):
            lines += [f"## {i}. {section['title']}", "", section["content"], ""]

        lines += [
            "---",
            "",
            citations if citations else "## References\n\nNo references available.",
            "",
        ]
        return "\n".join(lines)

