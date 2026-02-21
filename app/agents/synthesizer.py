"""
Yukti Research AI - Synthesizer Agent
=======================================
Uses Local LLM (Ollama) for chunk-based processing,
citation-aware generation, and source grounding.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SynthesizerAgent:
    """
    LLM Processing Layer: Synthesizes research into a structured report.
    
    Features:
    - Chunk-based processing for large content
    - Citation-aware generation
    - Source grounding to prevent hallucination
    - Academic tone and structure
    """
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.name = "Synthesizer Agent"
    
    async def synthesize(self, aggregated_data: Dict[str, Any], callback=None) -> Dict[str, Any]:
        """
        Synthesize a research report from aggregated data.
        """
        if callback:
            await callback("synthesizer", "starting", "Starting report synthesis...")
        
        plan = aggregated_data.get("plan", {})
        sections_context = aggregated_data.get("sections_context", [])
        citations_text = aggregated_data.get("citations_text", "")
        
        report_sections = []
        
        # Generate title
        title = plan.get("title", "Research Report")
        
        # Generate abstract
        if callback:
            await callback("synthesizer", "generating", "Generating abstract...")
        abstract = await self._generate_abstract(plan, aggregated_data)
        
        # Generate each section
        total_sections = len(sections_context)
        for i, section_ctx in enumerate(sections_context):
            section_title = section_ctx.get("title", f"Section {i+1}")
            
            if callback:
                progress = int(((i + 1) / total_sections) * 100)
                await callback("synthesizer", "generating", f"Writing section {i+1}/{total_sections}: {section_title} ({progress}%)")
            
            section_content = await self._generate_section(section_ctx, plan, aggregated_data)
            
            report_sections.append({
                "title": section_title,
                "content": section_content,
                "sources_used": len(section_ctx.get("relevant_content", []))
            })
        
        # Compile full report
        if callback:
            await callback("synthesizer", "compiling", "Compiling final report...")
        
        full_report = self._compile_report(title, abstract, report_sections, citations_text, plan)
        
        if callback:
            await callback("synthesizer", "completed", "Report synthesis complete!")
        
        return {
            "agent": self.name,
            "title": title,
            "abstract": abstract,
            "sections": report_sections,
            "full_report": full_report,
            "citations": citations_text,
            "word_count": len(full_report.split()),
            "timestamp": datetime.now().isoformat()
        }
    
    async def _generate_abstract(self, plan: Dict, data: Dict) -> str:
        """Generate report abstract."""
        if self.llm_client and self.llm_client.is_available:
            prompt = f"""Write a concise academic abstract (150-250 words) for a research report on:

Title: {plan.get('title', '')}
Scope: {plan.get('abstract_scope', '')}
Key Topics: {', '.join(plan.get('keywords', []))}
Total Sources Found: {data.get('total_sources', 0)}
Academic Sources: {data.get('academic_sources', 0)}

The abstract should:
1. State the research objective
2. Briefly describe the methodology
3. Summarize key findings
4. Note the significance

Write in academic third-person tone. Do NOT include any headers or labels."""
            
            return await self.llm_client.generate(prompt)
        
        # Fallback abstract
        return (
            f"This report presents a comprehensive analysis of {plan.get('title', 'the research topic')}. "
            f"Through systematic research across multiple academic databases including ArXiv, PubMed, "
            f"and Semantic Scholar, {data.get('total_sources', 0)} sources were identified and analyzed. "
            f"Of these, {data.get('academic_sources', 0)} are verified academic sources with DOI references. "
            f"The report covers {plan.get('abstract_scope', 'key aspects of the topic')}, "
            f"examining current methodologies, recent advancements, challenges, and future directions. "
            f"Key findings are synthesized from peer-reviewed literature to provide an evidence-based overview."
        )
    
    async def _generate_section(self, section_ctx: Dict, plan: Dict, data: Dict) -> str:
        """Generate a single report section."""
        relevant_content = section_ctx.get("relevant_content", [])
        
        if self.llm_client and self.llm_client.is_available:
            # Build context from relevant sources
            source_context = ""
            for i, item in enumerate(relevant_content[:8]):
                source_context += f"\n--- Source {i+1} ---\n"
                source_context += f"Title: {item.get('title', 'N/A')}\n"
                source_context += f"Content: {item.get('content', 'N/A')[:500]}\n"
                source_context += f"Source: {item.get('source', 'N/A')}\n"
                if item.get('doi'):
                    source_context += f"DOI: {item['doi']}\n"
            
            prompt = f"""Write the "{section_ctx.get('title', '')}" section for a research report on:

Research Topic: {plan.get('title', '')}
Section Focus: {section_ctx.get('research_focus', '')}
Section Description: {section_ctx.get('description', '')}

Available Source Material:
{source_context if source_context else 'No specific sources available for this section.'}

Instructions:
1. Write 200-400 words in academic prose
2. Reference sources using [number] format where applicable
3. Maintain an objective, scholarly tone
4. Include specific facts and findings from the sources
5. Do NOT include the section title (it will be added separately)
6. Do NOT make up citations - only reference provided sources
7. Focus on evidence-based analysis"""
            
            return await self.llm_client.generate(prompt)
        
        # Fallback: compile from sources
        return self._compile_section_from_sources(section_ctx)
    
    def _compile_section_from_sources(self, section_ctx: Dict) -> str:
        """Compile a section directly from source material when LLM is unavailable."""
        relevant = section_ctx.get("relevant_content", [])
        
        if not relevant:
            return (
                f"This section covers {section_ctx.get('description', 'the topic')}. "
                f"Further research is needed to provide comprehensive coverage of "
                f"{section_ctx.get('research_focus', 'this area')}."
            )
        
        paragraphs = []
        paragraphs.append(
            f"Research in {section_ctx.get('research_focus', 'this area')} "
            f"reveals several important findings from {len(relevant)} relevant sources."
        )
        
        for i, item in enumerate(relevant[:5]):
            authors = item.get("authors", [])
            author_str = f" by {authors[0]} et al." if authors else ""
            year = f" ({item.get('year', '')})" if item.get('year') else ""
            content = item.get("content", "") or item.get("abstract", "")
            
            if content:
                # Take first 2 sentences
                sentences = content.split('. ')[:2]
                summary = '. '.join(sentences)
                if not summary.endswith('.'):
                    summary += '.'
                
                paragraphs.append(
                    f"A study{author_str}{year} titled \"{item.get('title', 'Untitled')}\" "
                    f"from {item.get('source', 'academic sources')} found that {summary} [{i+1}]"
                )
        
        return "\n\n".join(paragraphs)
    
    def _compile_report(
        self,
        title: str,
        abstract: str,
        sections: List[Dict],
        citations: str,
        plan: Dict
    ) -> str:
        """Compile all sections into a complete report."""
        report = f"# {title}\n\n"
        report += f"*Generated by Yukti Research AI on {datetime.now().strftime('%B %d, %Y')}*\n\n"
        report += "---\n\n"
        
        # Abstract
        report += "## Abstract\n\n"
        report += abstract + "\n\n"
        
        # Keywords
        keywords = plan.get("keywords", [])
        if keywords:
            report += f"**Keywords:** {', '.join(keywords)}\n\n"
        
        report += "---\n\n"
        
        # Table of Contents
        report += "## Table of Contents\n\n"
        for i, section in enumerate(sections):
            report += f"{i+1}. [{section['title']}](#{section['title'].lower().replace(' ', '-')})\n"
        report += f"{len(sections)+1}. [References](#references)\n\n"
        report += "---\n\n"
        
        # Sections
        for i, section in enumerate(sections):
            report += f"## {i+1}. {section['title']}\n\n"
            report += section['content'] + "\n\n"
        
        # References
        report += "---\n\n"
        report += citations + "\n"
        
        return report
