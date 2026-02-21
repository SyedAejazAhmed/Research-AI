"""
Yukti Research AI - Content Aggregator
=======================================
Removes duplicates, filters low-quality sources,
ranks relevance, and prepares clean research input for LLM.
"""

import logging
import re
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class ContentAggregator:
    """
    Content Aggregator: Combines, deduplicates, and ranks research
    from all agents into a unified, clean dataset.
    """
    
    def __init__(self):
        self.name = "Content Aggregator"
    
    async def aggregate(
        self,
        web_results: Dict[str, Any],
        academic_results: Dict[str, Any],
        processed_results: Dict[str, Any],
        citation_results: Dict[str, Any],
        plan: Dict[str, Any],
        callback=None
    ) -> Dict[str, Any]:
        """
        Aggregate all research data into a unified dataset.
        """
        if callback:
            await callback("aggregator", "aggregating", "Combining research from all agents...")
        
        # Collect all content
        all_content = []
        
        # Web results
        for item in web_results.get("results", []):
            all_content.append({
                "title": item.get("title", ""),
                "content": item.get("content", ""),
                "source": item.get("source", "Web"),
                "url": item.get("url", ""),
                "type": "web",
                "relevance": 0.5
            })
        
        # Academic results
        for item in processed_results.get("processed_documents", []):
            all_content.append({
                "title": item.get("title", ""),
                "content": item.get("abstract", "") or item.get("content", ""),
                "source": item.get("source", "Academic"),
                "url": item.get("url", ""),
                "doi": item.get("doi", ""),
                "authors": item.get("authors", []),
                "year": item.get("year", ""),
                "type": "academic",
                "relevance": item.get("relevance_score", 0.5)
            })
        
        # Sort by relevance
        all_content.sort(key=lambda x: x.get("relevance", 0), reverse=True)
        
        # Build structured context for LLM
        sections_context = self._build_section_contexts(all_content, plan)
        
        # Build citation map
        citation_map = {}
        for cite in citation_results.get("citations", []):
            citation_map[cite["number"]] = cite
        
        if callback:
            await callback("aggregator", "completed", f"Aggregated {len(all_content)} sources into {len(sections_context)} sections")
        
        return {
            "agent": self.name,
            "all_content": all_content,
            "sections_context": sections_context,
            "citation_map": citation_map,
            "citations_text": citation_results.get("formatted_text", ""),
            "total_sources": len(all_content),
            "academic_sources": sum(1 for c in all_content if c["type"] == "academic"),
            "web_sources": sum(1 for c in all_content if c["type"] == "web"),
            "plan": plan,
            "timestamp": datetime.now().isoformat()
        }
    
    def _build_section_contexts(self, content: List[Dict], plan: Dict) -> List[Dict[str, Any]]:
        """Build context for each section of the report."""
        sections = plan.get("sections", [])
        section_contexts = []
        
        for section in sections:
            section_title = section.get("title", "")
            section_focus = section.get("research_focus", "").lower()
            section_desc = section.get("description", "").lower()
            
            # Find relevant content for this section
            relevant = []
            for item in content:
                title_lower = item.get("title", "").lower()
                content_lower = item.get("content", "").lower()
                
                # Check relevance to section
                relevance = 0
                for keyword in section_focus.split() + section_desc.split():
                    if len(keyword) > 3:
                        if keyword in title_lower:
                            relevance += 2
                        if keyword in content_lower:
                            relevance += 1
                
                if relevance > 0:
                    relevant.append({**item, "section_relevance": relevance})
            
            # Sort by section relevance and take top items
            relevant.sort(key=lambda x: x.get("section_relevance", 0), reverse=True)
            
            section_contexts.append({
                "title": section_title,
                "description": section.get("description", ""),
                "research_focus": section.get("research_focus", ""),
                "relevant_content": relevant[:10],  # Top 10 per section
                "source_count": len(relevant)
            })
        
        return section_contexts
