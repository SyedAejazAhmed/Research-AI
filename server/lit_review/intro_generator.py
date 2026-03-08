"""
Introduction Generator
======================

Generates project-aligned introductions with:
- Background of the field
- Problem gap identification
- Research objectives aligned with project
- Citations integrated naturally
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class IntroductionSection:
    """Generated introduction section."""
    background: str
    problem_gap: str
    objectives: str
    full_text: str
    word_count: int
    citations_used: List[str]
    contribution: str = ""
    organization: str = ""
    citation_count: int = 0


class IntroductionGenerator:
    """
    Generates project-aligned introduction sections.
    
    Features:
    - Background contextualization
    - Problem gap identification
    - Research objectives alignment
    - Natural citation integration
    """
    
    # Introduction structure templates
    INTRO_TEMPLATE = """
## Introduction

{background}

{problem_gap}

{objectives}

{scope}
"""

    BACKGROUND_PROMPTS = [
        "The field of {domain} has seen significant advances in recent years",
        "Recent developments in {domain} have opened new possibilities",
        "{domain} has emerged as a critical area of research",
    ]
    
    def __init__(self, llm_provider=None):
        """
        Initialize the generator.
        
        Args:
            llm_provider: LLM provider for text generation (optional)
        """
        self.llm_provider = llm_provider
    
    async def generate(
        self,
        project_overview: Dict[str, Any],
        citations: List[Dict[str, Any]],
        target_words: int = 500,
        style: str = "academic_formal"
    ) -> IntroductionSection:
        """
        Generate an introduction section.
        
        Args:
            project_overview: Project context from ProjectContextRetriever
            citations: List of relevant citations
            target_words: Target word count
            style: Writing style
            
        Returns:
            IntroductionSection with generated content
        """
        # Get title for logging (handle both dict and object)
        if hasattr(project_overview, 'title'):
            log_title = project_overview.title
        else:
            log_title = project_overview.get('title', 'Untitled')
        logger.info(f"Generating introduction for: {log_title}")
        
        # Handle both dict and ProjectOverview object
        if hasattr(project_overview, 'title'):
            title = project_overview.title
            problem = getattr(project_overview, 'problem', '')
            motivation = getattr(project_overview, 'motivation', '')
            method = getattr(project_overview, 'method', '')
            keywords = getattr(project_overview, 'keywords', []) or []
            contributions = getattr(project_overview, 'contributions', []) or []
        else:
            title = project_overview.get('title', '')
            problem = project_overview.get('problem', '')
            motivation = project_overview.get('motivation', '')
            method = project_overview.get('method', '')
            keywords = project_overview.get('keywords', []) or []
            contributions = project_overview.get('contributions', []) or []
        
        # Generate each part
        background = self._generate_background(keywords, citations[:5])
        problem_gap = self._generate_problem_gap(problem, motivation, citations[5:10])
        objectives = self._generate_objectives(title, method, contributions)
        scope = self._generate_scope(keywords)
        contribution = self._generate_contribution(contributions)
        organization = self._generate_organization()
        
        # Combine into full introduction
        full_text = self.INTRO_TEMPLATE.format(
            background=background,
            problem_gap=problem_gap,
            objectives=objectives,
            scope=scope
        ).strip()
        
        # Track citations used
        citations_used = [c.get('title', '') for c in citations[:10] if c.get('title')]
        
        return IntroductionSection(
            background=background,
            problem_gap=problem_gap,
            objectives=objectives,
            full_text=full_text,
            word_count=len(full_text.split()),
            citations_used=citations_used,
            contribution=contribution,
            organization=organization,
            citation_count=len(citations_used)
        )
    
    def _generate_contribution(self, contributions: List[str]) -> str:
        """Generate the contribution statement."""
        if contributions:
            return "This work makes the following contributions: " + "; ".join(contributions[:3]) + "."
        return "This work contributes novel insights to the research area."
    
    def _generate_organization(self) -> str:
        """Generate paper organization paragraph."""
        return ("The remainder of this paper is organized as follows: Section II reviews related work, "
                "Section III describes the methodology, Section IV presents results, "
                "and Section V concludes with future directions.")
    
    def _generate_background(self, keywords: List[str], citations: List[Dict]) -> str:
        """Generate the background/context paragraph."""
        domain = ', '.join(keywords[:3]) if keywords else 'this research area'
        
        # Build background with citations
        parts = []
        
        # Opening statement
        parts.append(f"The field of {domain} has witnessed remarkable progress in recent years, "
                    f"driven by advances in computational methods and increasing availability of data.")
        
        # Add citation-backed statements
        for i, citation in enumerate(citations[:3]):
            author = citation.get('authors', ['Researchers'])[0] if citation.get('authors') else 'Researchers'
            year = citation.get('year', '')
            title = citation.get('title', '')
            
            if year:
                parts.append(f"{author} et al. [{i+1}] demonstrated significant progress in this domain, "
                           f"contributing to our understanding of {keywords[i % len(keywords)] if keywords else 'the field'}.")
        
        # Closing context
        parts.append(f"These developments have established a strong foundation for further research "
                    f"in {domain}.")
        
        return ' '.join(parts)
    
    def _generate_problem_gap(self, problem: str, motivation: str, citations: List[Dict]) -> str:
        """Generate the problem/gap identification paragraph."""
        parts = []
        
        # State the problem
        if problem and problem != "Problem not clearly stated":
            parts.append(f"Despite these advances, significant challenges remain. {problem}")
        else:
            parts.append("Despite these advances, several important challenges remain unaddressed "
                       "in the current literature.")
        
        # Add gap analysis with citations
        for i, citation in enumerate(citations[:2]):
            author = citation.get('authors', ['Prior work'])[0] if citation.get('authors') else 'Prior work'
            year = citation.get('year', '')
            
            if year:
                parts.append(f"While {author} et al. [{i+4}] made important contributions, "
                           f"their approach does not fully address the complexity of real-world scenarios.")
        
        # State the motivation
        if motivation:
            parts.append(f"{motivation}")
        else:
            parts.append("This gap motivates the need for novel approaches that can effectively "
                       "address these limitations.")
        
        return ' '.join(parts)
    
    def _generate_objectives(self, title: str, method: str, contributions: List[str]) -> str:
        """Generate the research objectives paragraph."""
        parts = []
        
        # Main objective
        parts.append(f"This work aims to address these challenges through {title.lower() if title else 'a novel approach'}.")
        
        # Method overview
        if method and method != "Method to be determined based on literature review":
            parts.append(f"Our approach leverages {method}")
        
        # List contributions
        if contributions:
            parts.append("The main contributions of this work include:")
            for i, contrib in enumerate(contributions[:3], 1):
                parts.append(f"({i}) {contrib.lower() if not contrib[0].isupper() else contrib};")
        else:
            parts.append("We present a comprehensive solution that advances the state-of-the-art "
                       "in this domain.")
        
        return ' '.join(parts)
    
    def _generate_scope(self, keywords: List[str]) -> str:
        """Generate the scope/paper structure paragraph."""
        domain = keywords[0] if keywords else 'this topic'
        
        return (f"The remainder of this paper is organized as follows: Section II reviews "
               f"related work in {domain}. Section III presents our methodology. "
               f"Section IV describes the experimental setup and results. "
               f"Finally, Section V concludes with a discussion of implications and future directions.")
    
    async def regenerate_section(
        self,
        section_name: str,
        current_content: str,
        feedback: str,
        project_overview: Dict[str, Any],
        citations: List[Dict[str, Any]]
    ) -> str:
        """
        Regenerate a specific section based on feedback.
        
        Args:
            section_name: Name of section to regenerate
            current_content: Current section content
            feedback: User feedback for revision
            project_overview: Project context
            citations: Available citations
            
        Returns:
            Regenerated section content
        """
        logger.info(f"Regenerating section: {section_name}")
        
        if section_name == 'background':
            return self._generate_background(
                project_overview.get('keywords', []),
                citations[:5]
            )
        elif section_name == 'problem_gap':
            return self._generate_problem_gap(
                project_overview.get('problem', ''),
                project_overview.get('motivation', ''),
                citations[5:10]
            )
        elif section_name == 'objectives':
            return self._generate_objectives(
                project_overview.get('title', ''),
                project_overview.get('method', ''),
                project_overview.get('contributions', [])
            )
        else:
            return current_content
