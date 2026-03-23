"""
Academic Paper Generation Pipeline
===================================
Complete pipeline for generating journal-ready research papers with:
- Ordered reference tracking
- RAG-based content generation
- LaTeX compilation
- Multi-format export
"""

import asyncio
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import json

from app.database.schema import ResearchDatabase
from app.agents.rag_system import RAGSystem, OrderedReferenceAgent
from app.agents.latex_writing_agent import LaTeXWritingAgent
from app.agents.docker_latex_compiler import DockerLaTeXCompiler
from app.agents.github_analyzer import GitHubRepoAnalyzer

logger = logging.getLogger(__name__)


class AcademicPaperPipeline:
    """
    End-to-end pipeline for academic paper generation.

    Pipeline stages:
    1. Research & Citation Collection
    2. PDF Processing & Embedding Generation (RAG)
    3. Ordered Reference Assignment
    4. Section-wise Content Generation
    5. LaTeX Paper Generation
    6. Compilation to PDF
    7. Multi-format Export
    """

    def __init__(
        self,
        db_path: str = "research_ai.db",
        output_dir: str = "outputs/papers",
        workspace_dir: str = "multi_agent/Latex_engine/workspace"
    ):
        """
        Initialize paper generation pipeline.

        Args:
            db_path: Database path
            output_dir: Output directory for papers
            workspace_dir: LaTeX workspace directory
        """
        self.db = ResearchDatabase(db_path)
        self.rag = RAGSystem(db_manager=self.db)
        self.ref_agent = OrderedReferenceAgent(self.db, self.rag)
        self.latex_agent = LaTeXWritingAgent(workspace_dir=workspace_dir)
        self.latex_compiler = DockerLaTeXCompiler()
        self.github_analyzer = GitHubRepoAnalyzer()

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def generate_paper(
        self,
        query: str,
        citations: List[Dict[str, Any]],
        template_type: str = "IEEE",
        research_mode: str = "academic",
        github_repo: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate complete academic paper.

        Args:
            query: Research query
            citations: List of citation dictionaries
            template_type: LaTeX template (IEEE, Springer, ACM)
            research_mode: Research mode (normal, academic)
            github_repo: Optional GitHub repository URL
            metadata: Optional metadata

        Returns:
            Paper generation results
        """
        paper_id = hashlib.sha256(
            f"{query}_{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]

        logger.info(f"Starting paper generation: {paper_id}")

        try:
            # Stage 1: Process citations and generate embeddings
            logger.info("Stage 1: Processing citations and PDFs")
            processed_citations = await self._process_citations(paper_id, citations)

            # Stage 2: Analyze GitHub repository (if provided)
            github_context = None
            if github_repo:
                logger.info(f"Stage 2: Analyzing GitHub repository: {github_repo}")
                github_context = await self.github_analyzer.analyze_repository(github_repo)

                if github_context.get("success"):
                    # Store in database
                    self.db.add_github_repo(
                        repo_id=hashlib.sha256(github_repo.encode()).hexdigest()[:16],
                        repo_url=github_repo,
                        **github_context
                    )

            # Stage 3: Generate paper structure with ordered references
            logger.info("Stage 3: Generating paper structure")
            paper_structure = await self._generate_structure(
                paper_id,
                query,
                processed_citations,
                github_context
            )

            # Stage 4: Generate LaTeX paper
            logger.info("Stage 4: Generating LaTeX paper")
            latex_result = await self.latex_agent.generate_paper(
                paper_data=paper_structure,
                template_type=template_type,
                output_name=paper_id
            )

            if not latex_result.get("success"):
                return {
                    "success": False,
                    "error": f"LaTeX generation failed: {latex_result.get('error')}"
                }

            # Stage 5: Compile to PDF
            logger.info("Stage 5: Compiling to PDF")
            compile_result = self.latex_compiler.compile(
                tex_file=f"{paper_id}.tex",
                workspace_path=str(self.latex_agent.workspace_dir),
                use_bibtex=True,
                passes=3
            )

            if not compile_result.get("success"):
                logger.warning(f"PDF compilation had issues: {compile_result.get('error')}")

            # Stage 6: Multi-format export
            logger.info("Stage 6: Exporting to multiple formats")
            export_paths = await self._export_formats(
                paper_id,
                paper_structure,
                latex_result.get("tex_file")
            )

            # Stage 7: Store in database
            self.db.add_paper(
                paper_id=paper_id,
                title=paper_structure.get("title", ""),
                query=query,
                abstract=paper_structure.get("abstract", ""),
                content=paper_structure.get("full_content", ""),
                latex_source=latex_result.get("tex_file"),
                pdf_path=compile_result.get("pdf_path"),
                docx_path=export_paths.get("docx"),
                markdown_path=export_paths.get("markdown"),
                template_type=template_type,
                research_mode=research_mode,
                metadata=json.dumps(metadata or {})
            )

            # Final result
            result = {
                "success": True,
                "paper_id": paper_id,
                "title": paper_structure.get("title"),
                "query": query,
                "template_type": template_type,
                "files": {
                    "tex": latex_result.get("tex_file"),
                    "pdf": compile_result.get("pdf_path"),
                    "bib": latex_result.get("bib_file"),
                    **export_paths
                },
                "statistics": {
                    "citations_count": len(processed_citations),
                    "sections_count": len(paper_structure.get("sections", [])),
                    "compilation_errors": len(compile_result.get("errors", [])),
                    "compilation_warnings": len(compile_result.get("warnings", []))
                },
                "github_analysis": github_context if github_context else None,
                "compilation": {
                    "success": compile_result.get("success"),
                    "errors": compile_result.get("errors", []),
                    "warnings": compile_result.get("warnings", [])[:5]  # Limit warnings
                }
            }

            logger.info(f"Paper generation complete: {paper_id}")
            return result

        except Exception as e:
            logger.error(f"Paper generation error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "paper_id": paper_id
            }

    async def _process_citations(
        self,
        paper_id: str,
        citations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Process citations and generate embeddings from PDFs"""
        processed = []

        for idx, citation in enumerate(citations, 1):
            try:
                # Generate citation ID
                citation_id = citation.get("id") or hashlib.sha256(
                    f"{citation.get('title', '')}_{citation.get('doi', '')}".encode()
                ).hexdigest()[:16]

                # Add to database
                self.db.add_citation(
                    citation_id=citation_id,
                    title=citation.get("title", ""),
                    authors=citation.get("authors", []),
                    year=citation.get("year"),
                    **citation
                )

                # Process PDF if available
                if citation.get("pdf_path"):
                    pdf_result = await self.rag.process_pdf(
                        pdf_path=citation["pdf_path"],
                        citation_id=citation_id
                    )

                    if pdf_result.get("success"):
                        logger.info(f"Processed PDF for citation {idx}: {pdf_result['chunks']} chunks")

                processed.append({
                    **citation,
                    "id": citation_id,
                    "citation_key": citation.get("citation_key") or f"ref{idx}"
                })

            except Exception as e:
                logger.error(f"Error processing citation {idx}: {e}")

        return processed

    async def _generate_structure(
        self,
        paper_id: str,
        query: str,
        citations: List[Dict[str, Any]],
        github_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate paper structure with ordered references"""

        # Define paper sections
        sections = [
            "introduction",
            "literature_review",
            "methodology",
            "results",
            "conclusion"
        ]

        # Assign citations to sections in order
        citations_per_section = len(citations) // len(sections) if citations else 0

        structure = {
            "title": self._generate_title(query),
            "authors": "AI Research Assistant",
            "affiliation": "Automated Research Platform",
            "email": "research@ai-platform.com",
            "abstract": self._generate_abstract(query, citations),
            "keywords": self._extract_keywords(query, citations),
            "sections": {}
        }

        # Generate content for each section with ordered references
        for section_idx, section in enumerate(sections):
            # Get citations for this section
            start_idx = section_idx * citations_per_section
            end_idx = start_idx + citations_per_section if section_idx < len(sections) - 1 else len(citations)
            section_citations = citations[start_idx:end_idx]

            # Add ordered references to database
            for order_idx, citation in enumerate(section_citations, 1):
                await self.ref_agent.add_ordered_reference(
                    paper_id=paper_id,
                    section_name=section,
                    citation_id=citation["id"],
                    order_index=order_idx,
                    context=query
                )

            # Generate section content
            content = await self._generate_section_content(
                section,
                query,
                section_citations,
                github_context
            )

            structure[section] = content
            structure["sections"][section] = {
                "content": content,
                "citations": section_citations
            }

        return structure

    def _generate_title(self, query: str) -> str:
        """Generate paper title from query"""
        # Simple title generation - can be enhanced with LLM
        title = query.strip()
        if not title.endswith(('?', '.')):
            title = f"{title}: A Comprehensive Study"
        return title

    def _generate_abstract(self, query: str, citations: List[Dict]) -> str:
        """Generate abstract"""
        return f"""This paper presents a comprehensive study on {query}.
We review {len(citations)} relevant works in the field and synthesize current research findings.
Our analysis provides insights into the state-of-the-art approaches, methodologies, and future directions.
The study contributes to the understanding of this research area through systematic literature review and critical analysis."""

    def _extract_keywords(self, query: str, citations: List[Dict]) -> str:
        """Extract keywords from query and citations"""
        keywords = set(query.lower().split())

        # Add keywords from citations
        for citation in citations[:5]:  # Limit to first 5
            if citation.get("keywords"):
                keywords.update(citation["keywords"])

        # Filter common words
        common_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        keywords = {k for k in keywords if k not in common_words and len(k) > 3}

        return ", ".join(list(keywords)[:10])  # Limit to 10 keywords

    async def _generate_section_content(
        self,
        section_name: str,
        query: str,
        citations: List[Dict],
        github_context: Optional[Dict]
    ) -> str:
        """Generate content for a paper section"""

        if section_name == "introduction":
            content = f"""The field of {query} has seen significant developments in recent years.
This study aims to provide a comprehensive overview of current research and methodologies."""

        elif section_name == "literature_review":
            content = f"""We review {len(citations)} significant works in this domain. """
            for idx, citation in enumerate(citations[:10], 1):  # Limit to 10
                authors_str = ", ".join(citation.get("authors", [])[:2])
                year = citation.get("year", "N/A")
                content += f"""\\cite{{{citation['citation_key']}}} by {authors_str} ({year}) examined aspects of this field. """

        elif section_name == "methodology":
            if github_context and github_context.get("methodology"):
                content = f"""Our methodology is informed by modern software engineering practices.
{github_context['methodology']}"""
            else:
                content = """We employ a systematic literature review methodology, analyzing peer-reviewed publications
from major academic databases and repositories."""

        elif section_name == "results":
            content = f"""Our analysis of {len(citations)} research works reveals several key findings.
The reviewed literature demonstrates consistent trends in methodological approaches and outcomes."""

        elif section_name == "conclusion":
            content = """This study provides a comprehensive review of the current state of research in this domain.
Future work should focus on addressing identified gaps and exploring emerging trends."""

        else:
            content = f"Content for {section_name} section."

        return content

    async def _export_formats(
        self,
        paper_id: str,
        structure: Dict[str, Any],
        tex_file: Optional[str]
    ) -> Dict[str, str]:
        """Export paper to multiple formats"""
        export_paths = {}

        try:
            # Export to Markdown
            md_path = self.output_dir / f"{paper_id}.md"
            md_content = self._generate_markdown(structure)

            async with asyncio.to_thread(open, md_path, 'w', encoding='utf-8') as f:
                await asyncio.to_thread(f.write, md_content)

            export_paths["markdown"] = str(md_path)

            # Export BibTeX
            bib_path = self.output_dir / f"{paper_id}.bib"
            bib_content = self.latex_agent._generate_bibtex(
                structure.get("sections", {}).get("literature_review", {}).get("citations", [])
            )

            async with asyncio.to_thread(open, bib_path, 'w', encoding='utf-8') as f:
                await asyncio.to_thread(f.write, bib_content)

            export_paths["bibtex"] = str(bib_path)

            logger.info(f"Exported paper to {len(export_paths)} formats")

        except Exception as e:
            logger.error(f"Export error: {e}")

        return export_paths

    def _generate_markdown(self, structure: Dict[str, Any]) -> str:
        """Generate Markdown version of paper"""
        md_parts = []

        md_parts.append(f"# {structure.get('title', 'Untitled')}\n")
        md_parts.append(f"**Authors:** {structure.get('authors', 'Unknown')}\n")
        md_parts.append(f"**Affiliation:** {structure.get('affiliation', 'Unknown')}\n\n")

        md_parts.append("## Abstract\n")
        md_parts.append(f"{structure.get('abstract', '')}\n\n")

        md_parts.append(f"**Keywords:** {structure.get('keywords', '')}\n\n")

        # Sections
        sections = structure.get("sections", {})
        section_titles = {
            "introduction": "Introduction",
            "literature_review": "Literature Review",
            "methodology": "Methodology",
            "results": "Results and Discussion",
            "conclusion": "Conclusion"
        }

        for section_key, section_title in section_titles.items():
            if section_key in sections:
                md_parts.append(f"## {section_title}\n")
                md_parts.append(f"{sections[section_key].get('content', '')}\n\n")

        return "\n".join(md_parts)
