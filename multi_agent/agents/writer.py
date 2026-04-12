from datetime import datetime
import json5 as json
import re
from .utils.views import print_agent_output
from .utils.llms import call_model

sample_json = """
{
    "table_of_contents": "- Section 1\\n- Section 2",
    "introduction": "Academic introduction text with numeric citations like [1] and [2].",
    "conclusion": "Academic conclusion text with numeric citations like [1].",
    "sources": ["[1] A. Author, \"Title,\" Source, 2025.", "[2] B. Author, \"Title,\" Source, 2024."]
}
"""


class WriterAgent:
    def __init__(self, websocket=None, stream_output=None, headers=None):
        self.websocket = websocket
        self.stream_output = stream_output
        self.headers = headers

    def get_headers(self, research_state: dict):
        return {
            "title": research_state.get("title"),
            "date": "Date",
            "introduction": "Introduction",
            "table_of_contents": "Table of Contents",
            "conclusion": "Conclusion",
            "references": "References",
        }

    async def write_sections(self, research_state: dict):
        query = research_state.get("title")
        data = research_state.get("research_data")
        task = research_state.get("task") or {}
        follow_guidelines = bool(task.get("follow_guidelines"))
        guidelines = task.get("guidelines") or ""
        citation_style = str(task.get("citation_style", "IEEE") or "IEEE").upper()
        model = task.get("model")

        if not model:
            return self._fallback_layout(query=query, data=data, citation_style=citation_style)

        citation_instruction = (
            "Use IEEE references with numeric style [1], [2] in the sources list."
            if citation_style == "IEEE"
            else f"Use {citation_style} references in the sources list."
        )

        prompt = [
            {
                "role": "system",
                "content": "You are a research writer. Your sole purpose is to write a well-written "
                "research report about a "
                "topic based on research findings and information.\n ",
            },
            {
                "role": "user",
                "content": f"Today's date is {datetime.now().strftime('%d/%m/%Y')}\n."
                f"Query or Topic: {query}\n"
                f"Research data: {str(data)}\n"
                f"Your task is to write an in depth, well written and detailed "
                f"introduction and conclusion to the research report based on the provided research data. "
                f"Do not include headers in the results.\n"
                f"Use formal academic tone and keep citation markers numeric where applicable (for example: [1]).\n"
                f"{citation_instruction}\n\n"
                f"{f'You must follow the guidelines provided: {guidelines}' if follow_guidelines else ''}\n"
                f"You MUST return nothing but a JSON in the following format (without json markdown):\n"
                f"{sample_json}\n\n",
            },
        ]

        response = await call_model(
            prompt,
            model,
            response_format="json",
        )
        if not isinstance(response, dict):
            return self._fallback_layout(query=query, data=data, citation_style=citation_style)
        return self._normalize_layout(response, query=query, data=data, citation_style=citation_style)

    async def revise_headers(self, task: dict, headers: dict):
        task = task or {}
        model = task.get("model")
        if not model:
            return {"headers": headers}

        prompt = [
            {
                "role": "system",
                "content": """You are a research writer. 
Your sole purpose is to revise the headers data based on the given guidelines.""",
            },
            {
                "role": "user",
                "content": f"""Your task is to revise the given headers JSON based on the guidelines given.
You are to follow the guidelines but the values should be in simple strings, ignoring all markdown syntax.
You must return nothing but a JSON in the same format as given in headers data.
Guidelines: {task.get("guidelines")}\n
Headers Data: {headers}\n
""",
            },
        ]

        response = await call_model(
            prompt,
            model,
            response_format="json",
        )
        if not isinstance(response, dict):
            return {"headers": headers}
        return {"headers": response}

    async def run(self, research_state: dict):
        if self.websocket and self.stream_output:
            await self.stream_output(
                "logs",
                "writing_report",
                f"Writing final research report based on research data...",
                self.websocket,
            )
        else:
            print_agent_output(
                f"Writing final research report based on research data...",
                agent="WRITER",
            )

        research_layout_content = await self.write_sections(research_state)
        if not isinstance(research_layout_content, dict):
            citation_style = str((research_state.get("task") or {}).get("citation_style", "IEEE")).upper()
            research_layout_content = self._fallback_layout(
                query=research_state.get("title"),
                data=research_state.get("research_data"),
                citation_style=citation_style,
            )

        if (research_state.get("task") or {}).get("verbose"):
            if self.websocket and self.stream_output:
                research_layout_content_str = json.dumps(
                    research_layout_content, indent=2
                )
                await self.stream_output(
                    "logs",
                    "research_layout_content",
                    research_layout_content_str,
                    self.websocket,
                )
            else:
                print_agent_output(research_layout_content, agent="WRITER")

        headers = self.get_headers(research_state)
        if (research_state.get("task") or {}).get("follow_guidelines"):
            if self.websocket and self.stream_output:
                await self.stream_output(
                    "logs",
                    "rewriting_layout",
                    "Rewriting layout based on guidelines...",
                    self.websocket,
                )
            else:
                print_agent_output(
                    "Rewriting layout based on guidelines...", agent="WRITER"
                )
            headers = await self.revise_headers(
                task=research_state.get("task"), headers=headers
            )
            headers = headers.get("headers")

        return {**research_layout_content, "headers": headers}

    @staticmethod
    def _extract_links_from_text(text: str):
        if not text:
            return []
        return re.findall(r"https?://[^\s)]+", str(text))

    def _fallback_layout(self, query: str, data, citation_style: str) -> dict:
        """Deterministic fallback when model output is unavailable."""
        topic = (query or "Research Topic").strip()

        blocks = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    blocks.append(" ".join(str(v) for v in item.values() if v))
                else:
                    blocks.append(str(item))
        elif data:
            blocks.append(str(data))

        merged = "\n".join(blocks)
        links = self._extract_links_from_text(merged)

        intro = (
            f"This study examines {topic} using a structured review of available evidence. "
            f"The discussion consolidates background context, problem framing, and research objectives "
            f"to support an IEEE-style technical narrative."
        )
        conclusion = (
            f"In summary, the analysis of {topic} indicates clear opportunities for methodological refinement "
            f"and stronger empirical validation. Future work should prioritize reproducibility, benchmark-driven "
            f"evaluation, and domain-specific optimization."
        )

        sources = []
        for idx, link in enumerate(links[:30], start=1):
            if citation_style == "IEEE":
                sources.append(f"[{idx}] Source document, \"Retrieved resource,\" {link}.")
            else:
                sources.append(f"- Source document ({link})")

        toc = "- Introduction\n- Core Analysis\n- Conclusion\n- References"
        return {
            "table_of_contents": toc,
            "introduction": intro,
            "conclusion": conclusion,
            "sources": sources,
            "_writer_mode": "fallback",
        }

    def _normalize_layout(self, payload: dict, query: str, data, citation_style: str) -> dict:
        """Normalize model JSON output to expected schema."""
        fallback = self._fallback_layout(query=query, data=data, citation_style=citation_style)

        toc = str(payload.get("table_of_contents") or fallback["table_of_contents"]).strip()
        introduction = str(payload.get("introduction") or fallback["introduction"]).strip()
        conclusion = str(payload.get("conclusion") or fallback["conclusion"]).strip()
        raw_sources = payload.get("sources")

        if isinstance(raw_sources, list):
            sources = [str(s).strip() for s in raw_sources if str(s).strip()]
        elif isinstance(raw_sources, str):
            sources = [line.strip() for line in raw_sources.splitlines() if line.strip()]
        else:
            sources = fallback["sources"]

        if citation_style == "IEEE":
            normalized_sources = []
            for idx, src in enumerate(sources, start=1):
                cleaned = re.sub(r"^(\[\d+\]|\d+\.)\s*", "", src).strip()
                normalized_sources.append(f"[{idx}] {cleaned}")
            sources = normalized_sources

        return {
            "table_of_contents": toc,
            "introduction": introduction,
            "conclusion": conclusion,
            "sources": sources,
            "_writer_mode": "model",
        }
