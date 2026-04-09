"""
Yukti Research AI - Research Orchestrator
==========================================
Master orchestrator that coordinates all agents in the pipeline:
User Query → Planner → Parallel Research Agents → Aggregation →
LLM Synthesis → Publishing → Verified Research Output
"""

import asyncio
import logging
import uuid
import json
import re
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from pathlib import Path

from app.agents.planner import PlannerAgent
from app.agents.researchers import (
    WebContextAgent,
    AcademicResearchAgent,
    DocumentProcessingAgent,
    CitationAgent
)
from app.agents.aggregator import ContentAggregator
from app.agents.synthesizer import SynthesizerAgent
from app.agents.publisher import PublisherAgent
from app.agents.llm_client import OllamaClient
from app.utils.references import generate_references

logger = logging.getLogger(__name__)


class ResearchOrchestrator:
    """
    Master Orchestrator for the Yukti Research AI pipeline.
    
    Pipeline Flow:
    1. Planner Agent: Break query into sub-questions
    2. Parallel Research Agents: Gather data concurrently
    3. Content Aggregator: Combine and rank results
    4. Synthesizer: LLM-powered report generation
    5. Publisher: Final formatting and export
    """
    
    def __init__(self, output_dir: str = "outputs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize LLM client
        self.llm_client = OllamaClient()
        
        # Initialize agents
        self.planner = PlannerAgent(self.llm_client)
        self.web_agent = WebContextAgent()
        self.academic_agent = AcademicResearchAgent()
        self.doc_processor = DocumentProcessingAgent()
        self.citation_agent = CitationAgent()
        self.aggregator = ContentAggregator()
        self.synthesizer = SynthesizerAgent(self.llm_client)
        self.publisher = PublisherAgent(str(self.output_dir))
        
        # Session state
        self.sessions: Dict[str, Dict] = {}
        self.sessions_dir = Path("sessions")
        self.sessions_dir.mkdir(exist_ok=True)
        self._load_sessions()
    
    def _load_sessions(self):
        """Load persistent sessions from disk."""
        try:
            for session_file in self.sessions_dir.glob("*.json"):
                with open(session_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.sessions[session_file.stem] = data
            logger.info(f"💾 Loaded {len(self.sessions)} sessions from disk.")
        except Exception as e:
            logger.error(f"Error loading sessions: {e}")

    def _save_session(self, session_id: str):
        """Save a single session to disk."""
        if session_id in self.sessions:
            try:
                with open(self.sessions_dir / f"{session_id}.json", "w", encoding="utf-8") as f:
                    json.dump(self.sessions[session_id], f, indent=2)
            except Exception as e:
                logger.error(f"Error saving session {session_id}: {e}")

    async def initialize(self):
        """Initialize the orchestrator and all agents."""
        logger.info("Initializing Yukti Research AI...")
        
        # Try to initialize Ollama
        ollama_ready = await self.llm_client.initialize()
        if ollama_ready:
            logger.info(f"✓ Ollama ready with model: {self.llm_client.model}")
        else:
            logger.warning("⚠ Ollama not available - using fallback mode")
        
        return {
            "ollama": self.llm_client.get_status(),
            "agents": [
                "PlannerAgent", "WebContextAgent", "AcademicResearchAgent",
                "DocumentProcessingAgent", "CitationAgent", "ContentAggregator",
                "SynthesizerAgent", "PublisherAgent"
            ]
        }
    
    async def run_research(
        self,
        query: str,
        session_id: str = None,
        callback: Optional[Callable] = None,
        citation_style: str = "APA"
    ) -> Dict[str, Any]:
        """
        Run the complete research pipeline.
        
        Args:
            query: Research topic/question
            session_id: Optional session ID (generated if not provided)
            callback: Async callback for progress updates
            citation_style: Citation format (APA, IEEE, MLA)
            
        Returns:
            Complete research results with report and metadata
        """
        if not session_id:
            session_id = str(uuid.uuid4())[:8]
        
        start_time = datetime.now()
        
        # Initialize session
        self.sessions[session_id] = {
            "query": query,
            "status": "running",
            "started_at": start_time.isoformat(),
            "steps": []
        }
        
        try:
            # ========================================
            # Step 1: Planning
            # ========================================
            if callback:
                await callback("orchestrator", "step", "Step 1/5: Planning research...")
            
            plan = await self.planner.create_plan(query, callback)
            self._update_session(session_id, "planning_complete", plan)
            
            # ========================================
            # Step 2: Parallel Research
            # ========================================
            if callback:
                await callback("orchestrator", "step", "Step 2/5: Researching in parallel...")
            
            # Run all research agents in parallel
            web_task = self.web_agent.research(query, plan.get("keywords", []), callback)
            academic_task = self.academic_agent.research(query, plan.get("keywords", []), callback)
            
            web_results, academic_results = await asyncio.gather(
                web_task, academic_task, return_exceptions=True
            )
            
            # Handle exceptions
            if isinstance(web_results, Exception):
                logger.error(f"Web agent error: {web_results}")
                web_results = {"results": [], "count": 0}
            if isinstance(academic_results, Exception):
                logger.error(f"Academic agent error: {academic_results}")
                academic_results = {"results": [], "count": 0}
            
            self._update_session(session_id, "research_complete", {
                "web_count": web_results.get("count", 0),
                "academic_count": academic_results.get("count", 0)
            })
            
            # ========================================
            # Step 3: Process & Aggregate
            # ========================================
            if callback:
                await callback("orchestrator", "step", "Step 3/5: Curating 30 references and aggregating evidence...")
            
            # Process documents
            all_research = academic_results.get("results", []) + web_results.get("results", [])
            processed = await self.doc_processor.process(all_research, query, callback)
            
            # Generate citations (target: 30 formatted scholarly references first)
            academic_papers = [r for r in academic_results.get("results", []) if r.get("type") == "academic_paper"]
            citations = await self._build_targeted_citations(
                query=query,
                academic_papers=academic_papers,
                citation_style=citation_style,
                callback=callback,
            )
            
            # Aggregate everything
            aggregated = await self.aggregator.aggregate(
                web_results, academic_results, processed, citations, plan, callback
            )
            
            self._update_session(session_id, "aggregation_complete", {
                "total_sources": aggregated.get("total_sources", 0)
            })
            
            # ========================================
            # Step 4: LLM Synthesis
            # ========================================
            if callback:
                await callback("orchestrator", "step", "Step 4/5: Synthesizing report with AI...")
            
            synthesis = await self.synthesizer.synthesize(aggregated, callback)
            
            self._update_session(session_id, "synthesis_complete", {
                "word_count": synthesis.get("word_count", 0)
            })
            
            # ========================================
            # Step 5: Publishing
            # ========================================
            if callback:
                await callback("orchestrator", "step", "Step 5/5: Publishing report...")
            
            published = await self.publisher.publish(synthesis, session_id, callback)
            
            # Calculate duration
            duration = (datetime.now() - start_time).total_seconds()
            
            # Final result
            result = {
                "session_id": session_id,
                "query": query,
                "status": "completed",
                "title": synthesis.get("title", "Research Report"),
                "report": synthesis.get("full_report", ""),
                "abstract": synthesis.get("abstract", ""),
                "sections": synthesis.get("sections", []),
                "citations": citations,
                "statistics": {
                    "total_sources": aggregated.get("total_sources", 0),
                    "academic_sources": aggregated.get("academic_sources", 0),
                    "web_sources": aggregated.get("web_sources", 0),
                    "citations_count": citations.get("total", 0),
                    "verified_dois": citations.get("verified", 0),
                    "word_count": synthesis.get("word_count", 0),
                    "sections_count": len(synthesis.get("sections", [])),
                    "duration_seconds": round(duration, 1)
                },
                "files": published.get("files", {}),
                "plan": plan,
                "llm_status": self.llm_client.get_status(),
                "timestamp": datetime.now().isoformat()
            }
            
            # Update session
            self.sessions[session_id].update({
                "status": "completed",
                "completed_at": datetime.now().isoformat(),
                "result": result
            })
            self._save_session(session_id)
            
            if callback:
                await callback("orchestrator", "completed", "Research complete! 🎉")
            
            return result
            
        except Exception as e:
            logger.error(f"Research pipeline error: {e}", exc_info=True)
            
            self.sessions[session_id]["status"] = "error"
            self.sessions[session_id]["error"] = str(e)
            
            if callback:
                await callback("orchestrator", "error", f"Error: {str(e)}")
            
            raise
    
    def _update_session(self, session_id: str, step: str, data: Any):
        """Update session state."""
        if session_id in self.sessions:
            self.sessions[session_id]["steps"].append({
                "step": step,
                "data": data,
                "timestamp": datetime.now().isoformat()
            })

    async def _build_targeted_citations(
        self,
        query: str,
        academic_papers: list,
        citation_style: str,
        callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """Build citation output with a 30-reference target before synthesis."""
        if callback:
            await callback(
                "citation_agent",
                "searching",
                "Curating up to 30 scholarly references in the selected format...",
            )

        service_citations: Dict[str, Any] = {}
        try:
            reference_pack = await asyncio.to_thread(
                generate_references,
                query,
                30,
                citation_style,
            )
            service_citations = self._citations_from_reference_pack(reference_pack, citation_style)
            if callback:
                await callback(
                    "citation_agent",
                    "completed",
                    f"Reference curation complete: {service_citations.get('total', 0)} references.",
                )
        except Exception as exc:
            logger.warning("Reference curation via generate_references failed: %s", exc)

        if service_citations.get("total", 0) >= 30:
            return service_citations

        fallback_citations = await self.citation_agent.generate_citations(
            academic_papers,
            citation_style,
            callback,
        )

        if not service_citations.get("total", 0):
            return fallback_citations

        return self._merge_citation_results(service_citations, fallback_citations, target=30)

    @staticmethod
    def _citations_from_reference_pack(reference_pack: Dict[str, Any], citation_style: str) -> Dict[str, Any]:
        """Convert app.utils.references payload into orchestrator citation shape."""
        papers = reference_pack.get("papers", []) or []
        formatted = (reference_pack.get("formatted_references") or "").strip()
        blocks = [b.strip() for b in re.split(r"\n\s*\n", formatted) if b.strip()]

        citations = []
        verified = 0
        for idx, block in enumerate(blocks, start=1):
            paper = papers[idx - 1] if idx - 1 < len(papers) else {}
            doi = str(paper.get("DOI", "")).strip()
            if doi:
                verified += 1

            creators = paper.get("creators", []) or []
            authors = []
            for creator in creators:
                if creator.get("name"):
                    authors.append(str(creator.get("name", "")).strip())
                    continue
                first = str(creator.get("firstName", "")).strip()
                last = str(creator.get("lastName", "")).strip()
                full = f"{first} {last}".strip()
                if full:
                    authors.append(full)

            date_text = str(paper.get("date", ""))
            year_match = re.search(r"\b(19|20)\d{2}\b", date_text)
            year = year_match.group(0) if year_match else ""

            citations.append(
                {
                    "number": idx,
                    "formatted": block,
                    "doi": doi,
                    "verified": bool(doi),
                    "paper": {
                        "title": str(paper.get("title", "Untitled")),
                        "authors": authors,
                        "abstract": str(paper.get("abstractNote", "")),
                        "year": year,
                        "url": str(paper.get("url", "")),
                        "doi": doi,
                        "source": str(paper.get("publicationTitle", "")),
                        "type": "academic_paper",
                    },
                }
            )

        formatted_text = "## References\n\n" + "\n\n".join(c["formatted"] for c in citations)
        if not citations:
            formatted_text = "## References\n\nNo references found."

        return {
            "agent": "Reference Service",
            "citations": citations,
            "total": len(citations),
            "verified": verified,
            "style": citation_style,
            "formatted_text": formatted_text,
            "timestamp": datetime.now().isoformat(),
        }

    @staticmethod
    def _citation_identity(cite: Dict[str, Any]) -> str:
        paper = cite.get("paper", {}) or {}
        doi = str(cite.get("doi") or paper.get("doi") or "").strip().lower()
        if doi:
            return f"doi:{doi}"
        title = str(paper.get("title", "")).strip().lower()
        normalized_title = re.sub(r"[^a-z0-9\s]", "", title)
        return f"title:{normalized_title}"

    @staticmethod
    def _renumber_reference_text(text: str, number: int) -> str:
        stripped = (text or "").strip()
        stripped = re.sub(r"^(\[\d+\]|\d+\.)\s*", "", stripped)
        return f"[{number}] {stripped}" if stripped else f"[{number}]"

    def _merge_citation_results(
        self,
        primary: Dict[str, Any],
        secondary: Dict[str, Any],
        target: int = 30,
    ) -> Dict[str, Any]:
        """Merge two citation payloads, preserving primary ordering and deduplicating."""
        merged = []
        seen = set()

        for source in (primary.get("citations", []) or [], secondary.get("citations", []) or []):
            identity = self._citation_identity(source)
            if identity in seen:
                continue
            seen.add(identity)
            merged.append(dict(source))
            if len(merged) >= target:
                break

        for idx, cite in enumerate(merged, start=1):
            cite["number"] = idx
            cite["formatted"] = self._renumber_reference_text(cite.get("formatted", ""), idx)

        formatted_text = "## References\n\n" + "\n\n".join(c["formatted"] for c in merged)
        if not merged:
            formatted_text = "## References\n\nNo references found."

        verified = sum(1 for c in merged if c.get("verified") or c.get("doi"))

        return {
            "agent": "Citation Agent",
            "citations": merged,
            "total": len(merged),
            "verified": verified,
            "style": primary.get("style") or secondary.get("style"),
            "formatted_text": formatted_text,
            "timestamp": datetime.now().isoformat(),
        }
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session data."""
        return self.sessions.get(session_id)
    
    def get_all_sessions(self) -> Dict[str, Dict]:
        """Get all sessions."""
        return {
            sid: {
                "query": s.get("query", ""),
                "status": s.get("status", ""),
                "started_at": s.get("started_at", ""),
                "completed_at": s.get("completed_at", "")
            }
            for sid, s in self.sessions.items()
        }
