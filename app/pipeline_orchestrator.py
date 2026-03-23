"""
Comprehensive Research Pipeline Orchestrator
=============================================
End-to-end pipeline that orchestrates all agents and components:
- Research planning and execution
- Citation management (Zotero-like)
- PDF processing with RAG embeddings
- Ordered reference activation per section
- GitHub repository analysis
- LaTeX paper generation
- Multi-format export
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
import json

from app.agents.planner import PlannerAgent
from app.agents.researchers import AcademicResearchAgent, WebContextAgent
from app.agents.aggregator import ContentAggregator
from app.agents.synthesizer import SynthesizerAgent
from app.agents.publisher import PublisherAgent
from app.agents.rag_system import RAGSystem
from app.agents.github_analyzer import GitHubRepoAnalyzer
from app.agents.latex_writing_agent import LaTeXWritingAgent
from app.agents.ordered_reference_agent import OrderedReferenceAgent, PaperSection
from app.agents.llm_checker import LLMChecker
from app.database.schema import ResearchDatabase

logger = logging.getLogger(__name__)


class ResearchPipelineOrchestrator:
    """
    Master orchestrator for the complete research workflow.

    Pipeline stages:
    1. LLM Availability Check
    2. Research Planning (break down query)
    3. Research Execution (gather sources)
    4. Citation Management (store in database)
    5. PDF Processing (extract text, generate embeddings)
    6. Ordered Reference Assignment (assign citations to sections)
    7. GitHub Analysis (if repo provided)
    8. Content Synthesis (generate sections with RAG)
    9. LaTeX Generation (create journal-ready paper)
    10. Export (PDF, DOCX, Markdown, BibTeX)
    """

    def __init__(
        self,
        output_dir: str = "outputs",
        database_path: str = "research_ai.db",
        ollama_host: str = "http://localhost:11434"
    ):
        """
        Initialize the pipeline orchestrator

        Args:
            output_dir: Output directory for results
            database_path: Path to SQLite database
            ollama_host: Ollama API endpoint
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self.db = ResearchDatabase(database_path)

        # Initialize agents
        self.llm_checker = LLMChecker(ollama_host=ollama_host)
        self.planner = PlannerAgent()
        self.academic_researcher = AcademicResearchAgent()
        self.web_researcher = WebContextAgent()
        self.aggregator = ContentAggregator()
        self.synthesizer = SynthesizerAgent(ollama_host=ollama_host)
        self.publisher = PublisherAgent(output_dir=str(self.output_dir))
        self.rag_system = RAGSystem(database=self.db)
        self.github_analyzer = GitHubRepoAnalyzer(
            output_dir=str(self.output_dir / "github_analysis"),
            images_dir=str(self.output_dir / "images")
        )
        self.latex_agent = LaTeXWritingAgent(output_dir=str(self.output_dir))
        self.reference_agent = OrderedReferenceAgent(database_manager=self.db)

        # Pipeline state
        self.current_session_id = None
        self.pipeline_state = {}

    async def run_full_pipeline(
        self,
        query: str,
        research_mode: str = "academic",  # "academic" or "normal"
        template_type: str = "IEEE",
        citation_style: str = "APA",
        github_repo: Optional[str] = None,
        max_citations: int = 30,
        include_images: bool = True,
        export_formats: List[str] = ["pdf", "markdown", "docx", "bibtex"]
    ) -> Dict[str, Any]:
        """
        Run the complete research pipeline

        Args:
            query: Research query
            research_mode: "academic" (scholarly sources) or "normal" (web sources)
            template_type: LaTeX template ("IEEE", "Springer", "ACM")
            citation_style: Citation format ("APA", "MLA", "IEEE", etc.)
            github_repo: Optional GitHub repository URL
            max_citations: Maximum number of citations
            include_images: Extract images from GitHub repo
            export_formats: List of export formats

        Returns:
            Pipeline results dictionary
        """
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.current_session_id = session_id

        logger.info(f"Starting research pipeline for query: {query}")
        logger.info(f"Session ID: {session_id}")

        results = {
            "session_id": session_id,
            "query": query,
            "research_mode": research_mode,
            "template_type": template_type,
            "citation_style": citation_style,
            "timestamp": datetime.now().isoformat(),
            "stages": {}
        }

        try:
            # Stage 1: LLM Availability Check
            logger.info("Stage 1: Checking LLM availability...")
            llm_available, model_name = await self.llm_checker.ensure_model_available()
            if not llm_available:
                raise Exception("No LLM model available. Please install Ollama and download a model.")
            results["stages"]["llm_check"] = {
                "status": "success",
                "model": model_name
            }

            # Stage 2: Research Planning
            logger.info("Stage 2: Planning research strategy...")
            sub_queries = await self.planner.plan(query)
            results["stages"]["planning"] = {
                "status": "success",
                "sub_queries": sub_queries,
                "count": len(sub_queries)
            }

            # Stage 3: Research Execution
            logger.info(f"Stage 3: Executing research ({research_mode} mode)...")
            all_sources = []

            if research_mode == "academic":
                # Use academic sources only
                for sq in sub_queries:
                    sources = await self.academic_researcher.research(sq)
                    all_sources.extend(sources)
            else:
                # Use web sources
                for sq in sub_queries:
                    sources = await self.web_researcher.search(sq)
                    all_sources.extend(sources)

            results["stages"]["research"] = {
                "status": "success",
                "sources_found": len(all_sources)
            }

            # Stage 4: Citation Management
            logger.info("Stage 4: Managing citations...")
            citation_ids = []

            for source in all_sources[:max_citations]:
                citation_id = await self.db.add_citation(
                    title=source.get("title", "Untitled"),
                    authors=source.get("authors", []),
                    year=source.get("year"),
                    venue=source.get("venue"),
                    doi=source.get("doi"),
                    arxiv_id=source.get("arxiv_id"),
                    url=source.get("url"),
                    abstract=source.get("abstract"),
                    metadata=source
                )
                citation_ids.append(citation_id)

            results["stages"]["citations"] = {
                "status": "success",
                "citation_ids": citation_ids,
                "count": len(citation_ids)
            }

            # Stage 5: PDF Processing & RAG Embeddings
            logger.info("Stage 5: Processing PDFs and generating embeddings...")
            embeddings_created = 0

            for citation_id in citation_ids:
                # Try to download PDF and process
                try:
                    # This would ideally download the PDF from the source
                    # For now, we'll simulate with text from abstract
                    citation = await self.db.get_citation(citation_id)
                    text = citation.get("abstract", "")

                    if text:
                        await self.rag_system.add_document(
                            citation_id=citation_id,
                            text=text
                        )
                        embeddings_created += 1
                except Exception as e:
                    logger.warning(f"Could not create embedding for {citation_id}: {e}")

            results["stages"]["embeddings"] = {
                "status": "success",
                "embeddings_created": embeddings_created
            }

            # Stage 6: Ordered Reference Assignment
            logger.info("Stage 6: Assigning references to paper sections...")
            section_assignments = self.reference_agent.auto_assign_sections(citation_ids)

            results["stages"]["reference_assignment"] = {
                "status": "success",
                "assignments": {
                    section.value: {
                        "count": len(assignment.citation_ids),
                        "range": f"{assignment.start_index}-{assignment.end_index}"
                    }
                    for section, assignment in section_assignments.items()
                }
            }

            # Stage 7: GitHub Analysis (if provided)
            github_analysis = None
            if github_repo:
                logger.info(f"Stage 7: Analyzing GitHub repository: {github_repo}")
                github_analysis = await self.github_analyzer.analyze_repository(
                    repo_url=github_repo,
                    extract_images=include_images
                )
                results["stages"]["github_analysis"] = {
                    "status": "success" if github_analysis.get("success") else "failed",
                    "repo": github_repo,
                    "images_extracted": len(github_analysis.get("extracted_images", []))
                }

            # Stage 8: Content Synthesis with RAG
            logger.info("Stage 8: Synthesizing paper content with RAG...")
            paper_sections = {}

            for section in PaperSection:
                if section in [PaperSection.ABSTRACT, PaperSection.REFERENCES]:
                    continue  # Skip these for now

                logger.info(f"Generating {section.value}...")

                # Activate embeddings for this section
                activated = await self.reference_agent.activate_embeddings_for_section(section)

                # Generate content using RAG context
                if activated:
                    # Get RAG context
                    rag_context = await self.reference_agent.retrieve_context_for_section(
                        section=section,
                        query=query,
                        top_k=5
                    )

                    # Synthesize section content
                    section_content = await self.synthesizer.synthesize_section(
                        section_name=section.value,
                        query=query,
                        context=rag_context,
                        github_analysis=github_analysis
                    )

                    paper_sections[section.value] = section_content

            results["stages"]["synthesis"] = {
                "status": "success",
                "sections_generated": len(paper_sections)
            }

            # Stage 9: LaTeX Generation
            logger.info(f"Stage 9: Generating LaTeX paper ({template_type} template)...")
            latex_output = await self.latex_agent.generate_paper(
                title=query,
                sections=paper_sections,
                references=self.reference_agent.get_full_reference_list(format=citation_style),
                template_type=template_type,
                github_analysis=github_analysis
            )

            results["stages"]["latex"] = {
                "status": "success",
                "template": template_type,
                "output_path": latex_output.get("tex_file")
            }

            # Stage 10: Export
            logger.info("Stage 10: Exporting to multiple formats...")
            export_results = {}

            for fmt in export_formats:
                export_path = await self.publisher.export(
                    content=paper_sections,
                    format=fmt,
                    session_id=session_id,
                    latex_file=latex_output.get("tex_file")
                )
                export_results[fmt] = export_path

            results["stages"]["export"] = {
                "status": "success",
                "formats": export_results
            }

            # Final results
            results["status"] = "success"
            results["output_files"] = export_results
            results["session_dir"] = str(self.output_dir / session_id)

            # Save pipeline state
            self._save_pipeline_state(session_id, results)

            logger.info("Pipeline completed successfully!")
            return results

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            results["status"] = "failed"
            results["error"] = str(e)
            return results

    def _save_pipeline_state(self, session_id: str, results: Dict):
        """Save pipeline state to disk"""
        session_dir = self.output_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        state_file = session_dir / "pipeline_state.json"
        with open(state_file, 'w') as f:
            json.dump(results, f, indent=2)

        logger.info(f"Pipeline state saved to {state_file}")

    async def get_pipeline_status(self, session_id: str) -> Optional[Dict]:
        """Get status of a pipeline session"""
        state_file = self.output_dir / session_id / "pipeline_state.json"

        if state_file.exists():
            with open(state_file, 'r') as f:
                return json.load(f)

        return None

    def list_sessions(self) -> List[str]:
        """List all pipeline sessions"""
        sessions = []
        for item in self.output_dir.iterdir():
            if item.is_dir() and item.name.startswith("session_"):
                sessions.append(item.name)
        return sorted(sessions, reverse=True)


# CLI interface
async def main():
    """CLI interface for the pipeline orchestrator"""
    print("=" * 70)
    print("COMPREHENSIVE RESEARCH PIPELINE ORCHESTRATOR")
    print("=" * 70)

    orchestrator = ResearchPipelineOrchestrator()

    # Example usage
    query = "Recent advances in transformer models for natural language processing"

    print(f"\nQuery: {query}")
    print("Mode: Academic Research")
    print("Template: IEEE Conference")
    print("Citations: Up to 30")
    print("\nStarting pipeline...\n")

    results = await orchestrator.run_full_pipeline(
        query=query,
        research_mode="academic",
        template_type="IEEE",
        citation_style="IEEE",
        max_citations=30,
        export_formats=["pdf", "markdown", "bibtex"]
    )

    print("\n" + "=" * 70)
    print("PIPELINE RESULTS")
    print("=" * 70)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
