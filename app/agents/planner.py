"""
Yukti Research AI - Planner Agent
==================================
Breaks user query into sub-questions, defines scope & structure,
and outputs a research plan.
"""

import json
import logging
import asyncio
import re
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class PlannerAgent:
    """
    Planner Agent: Breaks research query into structured sub-questions.
    
    Responsibilities:
    - Analyze the research query
    - Break into meaningful sub-questions
    - Define research scope and structure
    - Output a structured research plan
    """
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
    
    async def create_plan(self, query: str, callback=None) -> Dict[str, Any]:
        """
        Create a structured research plan from a user query.
        
        Args:
            query: The research topic/question
            callback: Optional async callback for progress updates
            
        Returns:
            Dictionary with research plan
        """
        if callback:
            await callback("planner", "analyzing", "Analyzing research query...")
        
        normalized_query = self._sanitize_query(query)
        plan = await self._generate_plan(normalized_query)
        
        if callback:
            await callback("planner", "completed", f"Research plan created with {len(plan.get('sub_questions', []))} sub-questions. Plan: {json.dumps(plan)}")
        
        return plan
    
    async def _generate_plan(self, query: str) -> Dict[str, Any]:
        """Generate research plan using LLM or fallback to heuristic."""
        query = self._sanitize_query(query)
        
        if self.llm_client:
            try:
                prompt = f"""You are a research planning agent. Given the following research query, 
break it down into a structured research plan. Return ONLY valid JSON.

Research Query: {query}

Return JSON with this exact structure:
{{
    "title": "A concise research title",
    "abstract_scope": "Brief description of what this research covers",
    "sub_questions": [
        "Sub-question 1 that needs to be researched",
        "Sub-question 2 that needs to be researched",
        "Sub-question 3 that needs to be researched"
    ],
    "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
    "sections": [
        {{
            "title": "Section Title",
            "description": "What this section should cover",
            "research_focus": "Specific focus area for research"
        }}
    ],
    "methodology": "Brief description of research approach",
    "expected_sources": ["ArXiv", "PubMed", "Semantic Scholar", "Web"]
}}

Use this section order exactly:
1. Abstract
2. Introduction
3. Related Studies
4. Methodology
5. Result and Discussion
6. Conclusion
7. References
"""
                response = await self.llm_client.generate(prompt, max_tokens=1024)
                
                # Try to parse JSON from response
                json_str = response
                if "```json" in json_str:
                    json_str = json_str.split("```json")[1].split("```")[0]
                elif "```" in json_str:
                    json_str = json_str.split("```")[1].split("```")[0]
                
                plan = json.loads(json_str.strip())
                
                # Ensure required fields
                if "sub_questions" not in plan:
                    plan["sub_questions"] = [query]
                if "title" not in plan:
                    plan["title"] = query
                plan["title"] = self._sanitize_title(plan.get("title", query))
                if "sections" not in plan:
                    plan["sections"] = self._default_sections(query)
                if "keywords" not in plan:
                    plan["keywords"] = self._extract_keywords(query)
                    
                return plan
                
            except Exception as e:
                logger.warning(f"LLM plan generation failed: {e}, using heuristic fallback")
        
        # Fallback: heuristic-based planning
        return self._heuristic_plan(query)
    
    def _heuristic_plan(self, query: str) -> Dict[str, Any]:
        """Generate a research plan using heuristics when LLM is unavailable."""
        query = self._sanitize_query(query)
        keywords = self._extract_keywords(query)
        
        sub_questions = [
            f"What is the current state of research on {query}?",
            f"What are the key methodologies used in {query}?",
            f"What are the recent advancements and breakthroughs in {query}?",
            f"What are the challenges and limitations in {query}?",
            f"What are the future directions for {query}?",
        ]
        
        sections = self._default_sections(query)
        
        return {
            "title": f"Research Report: {query}",
            "abstract_scope": f"A comprehensive analysis of {query}, covering current methodologies, recent advancements, challenges, and future directions.",
            "sub_questions": sub_questions,
            "keywords": keywords,
            "sections": sections,
            "methodology": "Multi-source academic research with cross-referencing and citation verification",
            "expected_sources": ["ArXiv", "PubMed", "Semantic Scholar", "Web"]
        }
    
    def _default_sections(self, query: str) -> List[Dict[str, str]]:
        """Generate default report sections."""
        query = self._sanitize_query(query)
        return [
            {
                "title": "Abstract",
                "description": f"Concise summary of {query} including objective, method, findings, and significance",
                "research_focus": "Research objective, methods, key findings"
            },
            {
                "title": "Introduction",
                "description": f"Background and context for {query}",
                "research_focus": "Overview, motivation, and problem definition"
            },
            {
                "title": "Related Studies",
                "description": "Review of existing research and key findings",
                "research_focus": "Academic papers and prior work"
            },
            {
                "title": "Methodology",
                "description": "Current methods and techniques in the field",
                "research_focus": "Technical approaches and frameworks"
            },
            {
                "title": "Result and Discussion",
                "description": "Major discoveries and their implications",
                "research_focus": "Results and analytical interpretation"
            },
            {
                "title": "Conclusion",
                "description": "Summary of key insights and recommendations",
                "research_focus": "Synthesis, limitations, and takeaways"
            },
            {
                "title": "References",
                "description": "Curated scholarly references supporting the paper",
                "research_focus": "IEEE/Harvard-ready citations, source credibility, and citation coverage"
            }
        ]
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract keywords from query using simple heuristics."""
        query = self._sanitize_query(query)
        # Remove common stop words
        stop_words = {
            'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'can', 'shall',
            'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
            'as', 'into', 'through', 'during', 'before', 'after', 'about',
            'between', 'under', 'above', 'and', 'but', 'or', 'nor', 'not',
            'so', 'yet', 'both', 'either', 'neither', 'each', 'every',
            'all', 'any', 'few', 'more', 'most', 'other', 'some', 'such',
            'no', 'only', 'own', 'same', 'than', 'too', 'very', 'what',
            'which', 'who', 'whom', 'this', 'that', 'these', 'those',
            'how', 'why', 'when', 'where', 'if', 'then', 'it', 'its'
        }
        
        words = query.lower().split()
        keywords = [w.strip('.,!?;:') for w in words if w.lower().strip('.,!?;:') not in stop_words and len(w) > 2]
        
        # Also add the full query as a keyword phrase
        return list(set(keywords))[:8]

    def _sanitize_query(self, query: str) -> str:
        """Keep only the core research topic from mixed instruction/context prompts."""
        text = str(query or "").replace("\r\n", "\n").replace("\r", "\n").strip()
        if not text:
            return ""

        text = re.sub(r"`[^`]*`", " ", text)

        lines = []
        stop_markers = (
            "repository context summary",
            "##analysis",
            "analysis stats",
            "structure preview",
            "future scope",
        )
        for raw in text.split("\n"):
            line = raw.strip()
            if not line:
                continue

            lowered = line.lower()
            if any(marker in lowered for marker in stop_markers):
                break
            if lowered.startswith("don't let ai write"):
                continue
            if lowered.startswith("we don't need repository context summary"):
                continue
            lines.append(line)

        candidate = lines[0] if lines else text.split("\n", 1)[0].strip()
        return self._sanitize_title(candidate)

    @staticmethod
    def _sanitize_title(title: str) -> str:
        cleaned = str(title or "").strip()
        if not cleaned:
            return "Research Topic"

        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = re.sub(r"^[\-:#\s]+", "", cleaned)
        cleaned = cleaned.replace("##", "").strip()
        if cleaned.lower().startswith("research report:"):
            cleaned = cleaned.split(":", 1)[1].strip() or cleaned
        return cleaned[:220]
