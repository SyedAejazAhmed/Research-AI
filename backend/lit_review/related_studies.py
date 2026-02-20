"""
Related Studies Generator
=========================

Generates project-aligned Related Work sections with:
- Theme-based grouping of citations
- Explicit connection to project
- Year-sorted references
- Differentiation from existing work
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class CitationGroup:
    """A group of related citations by theme."""
    theme: str
    description: str
    citations: List[Dict[str, Any]]
    connection_to_project: str


@dataclass
class RelatedStudiesSection:
    """Generated related studies section."""
    groups: List[CitationGroup]
    full_text: str
    word_count: int
    total_citations: int
    year_range: Tuple[int, int]


class RelatedStudiesGenerator:
    """
    Generates project-aligned Related Studies sections.
    
    Features:
    - Automatic theme detection and grouping
    - Explicit project connections
    - Year-sorted citations within groups
    - Gap analysis and differentiation
    """
    
    # Common research themes for grouping
    THEME_KEYWORDS = {
        'deep_learning': ['deep learning', 'neural network', 'CNN', 'RNN', 'transformer', 'attention'],
        'nlp': ['natural language', 'NLP', 'text', 'language model', 'BERT', 'GPT', 'sentiment'],
        'computer_vision': ['image', 'vision', 'object detection', 'segmentation', 'recognition'],
        'optimization': ['optimization', 'training', 'convergence', 'gradient', 'loss function'],
        'applications': ['application', 'system', 'framework', 'implementation', 'deployment'],
        'evaluation': ['evaluation', 'benchmark', 'dataset', 'metric', 'comparison'],
        'theoretical': ['theory', 'analysis', 'proof', 'bound', 'complexity'],
    }
    
    SECTION_TEMPLATE = """
## Related Work

{introduction}

{grouped_content}

{summary}
"""

    GROUP_TEMPLATE = """
### {theme_title}

{content}
"""
    
    def __init__(self, llm_provider=None):
        """
        Initialize the generator.
        
        Args:
            llm_provider: LLM provider for text generation (optional)
        """
        self.llm_provider = llm_provider
    
    def _get_overview_attr(self, project_overview, attr: str, default=None):
        """Get attribute from project_overview whether it's a dict or dataclass."""
        if hasattr(project_overview, attr):
            return getattr(project_overview, attr, default)
        elif isinstance(project_overview, dict):
            return project_overview.get(attr, default)
        return default
    
    async def generate(
        self,
        project_overview: Dict[str, Any],
        citations: List[Dict[str, Any]],
        min_citations: int = 10,
        max_citations: int = 30
    ) -> RelatedStudiesSection:
        """
        Generate a Related Studies section.
        
        Args:
            project_overview: Project context from ProjectContextRetriever
            citations: List of citations from academic search
            min_citations: Minimum citations to include
            max_citations: Maximum citations to include
            
        Returns:
            RelatedStudiesSection with generated content
        """
        logger.info(f"Generating related studies for: {self._get_overview_attr(project_overview, 'title', 'Untitled')}")
        
        # Filter and sort citations
        filtered_citations = self._filter_citations(citations, project_overview)
        sorted_citations = self._sort_by_year(filtered_citations[:max_citations])
        
        # Group by theme
        groups = self._group_by_theme(sorted_citations, project_overview)
        
        # Generate section text
        introduction = self._generate_introduction(project_overview)
        grouped_content = self._generate_grouped_content(groups, project_overview)
        summary = self._generate_summary(groups, project_overview)
        
        # Combine
        full_text = self.SECTION_TEMPLATE.format(
            introduction=introduction,
            grouped_content=grouped_content,
            summary=summary
        ).strip()
        
        # Calculate year range
        years = [c.get('year', 0) for c in sorted_citations if c.get('year')]
        year_range = (min(years) if years else 0, max(years) if years else 0)
        
        return RelatedStudiesSection(
            groups=groups,
            full_text=full_text,
            word_count=len(full_text.split()),
            total_citations=len(sorted_citations),
            year_range=year_range
        )
    
    def _filter_citations(
        self,
        citations: List[Dict[str, Any]],
        project_overview
    ) -> List[Dict[str, Any]]:
        """Filter citations by relevance to project."""
        keywords = self._get_overview_attr(project_overview, 'keywords', []) or []
        keywords = set(k.lower() for k in keywords)
        title = self._get_overview_attr(project_overview, 'title', '') or ''
        title_words = set(title.lower().split())
        
        scored_citations = []
        for citation in citations:
            score = self._calculate_relevance_score(citation, keywords, title_words)
            if score > 0:
                citation['_relevance_score'] = score
                scored_citations.append(citation)
        
        # Sort by relevance and return top citations
        scored_citations.sort(key=lambda x: x.get('_relevance_score', 0), reverse=True)
        return scored_citations
    
    def _calculate_relevance_score(
        self,
        citation: Dict[str, Any],
        keywords: set,
        title_words: set
    ) -> float:
        """Calculate relevance score for a citation."""
        score = 0.0
        
        # Check title
        citation_title = citation.get('title', '').lower()
        for keyword in keywords:
            if keyword in citation_title:
                score += 2.0
        
        for word in title_words:
            if len(word) > 3 and word in citation_title:
                score += 1.0
        
        # Check abstract
        abstract = citation.get('abstract', '').lower()
        for keyword in keywords:
            if keyword in abstract:
                score += 1.0
        
        # Bonus for recent papers
        year = citation.get('year', 0)
        if year:
            try:
                year_int = int(year)
                if year_int >= 2023:
                    score += 1.5
                elif year_int >= 2021:
                    score += 1.0
                elif year_int >= 2019:
                    score += 0.5
            except:
                pass
        
        # Bonus for high citation count
        citation_count = citation.get('citation_count', 0)
        if citation_count:
            try:
                count = int(citation_count)
                if count > 100:
                    score += 1.5
                elif count > 50:
                    score += 1.0
                elif count > 10:
                    score += 0.5
            except:
                pass
        
        return score
    
    def _sort_by_year(self, citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort citations by year ascending."""
        def get_year(c):
            try:
                return int(c.get('year', 9999))
            except:
                return 9999
        
        return sorted(citations, key=get_year)
    
    def _group_by_theme(
        self,
        citations: List[Dict[str, Any]],
        project_overview
    ) -> List[CitationGroup]:
        """Group citations by detected themes."""
        theme_citations = defaultdict(list)
        
        for citation in citations:
            theme = self._detect_theme(citation)
            theme_citations[theme].append(citation)
        
        # Create CitationGroup objects
        groups = []
        for theme, cites in theme_citations.items():
            if cites:
                group = CitationGroup(
                    theme=theme,
                    description=self._get_theme_description(theme),
                    citations=cites,
                    connection_to_project=self._generate_connection(theme, project_overview)
                )
                groups.append(group)
        
        # Sort groups by citation count
        groups.sort(key=lambda g: len(g.citations), reverse=True)
        
        return groups
    
    def _detect_theme(self, citation: Dict[str, Any]) -> str:
        """Detect the theme of a citation."""
        text = f"{citation.get('title', '')} {citation.get('abstract', '')}".lower()
        
        theme_scores = {}
        for theme, keywords in self.THEME_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in text)
            theme_scores[theme] = score
        
        # Return theme with highest score
        if theme_scores:
            best_theme = max(theme_scores.items(), key=lambda x: x[1])
            if best_theme[1] > 0:
                return best_theme[0]
        
        return 'general'
    
    def _get_theme_description(self, theme: str) -> str:
        """Get human-readable description of a theme."""
        descriptions = {
            'deep_learning': 'Deep Learning Approaches',
            'nlp': 'Natural Language Processing Methods',
            'computer_vision': 'Computer Vision Techniques',
            'optimization': 'Training and Optimization',
            'applications': 'Applications and Systems',
            'evaluation': 'Evaluation and Benchmarks',
            'theoretical': 'Theoretical Foundations',
            'general': 'Related Approaches',
        }
        return descriptions.get(theme, 'Related Work')
    
    def _generate_connection(self, theme: str, project_overview) -> str:
        """Generate connection statement between theme and project."""
        title = self._get_overview_attr(project_overview, 'title', 'our work')
        method = self._get_overview_attr(project_overview, 'method', '')
        
        connections = {
            'deep_learning': f"Our work builds upon these deep learning foundations while introducing novel {method or 'techniques'}.",
            'nlp': f"While these NLP methods provide valuable insights, {title} extends them to new domains.",
            'computer_vision': f"The vision techniques inspire our approach, though we address different challenges in {title}.",
            'optimization': f"These optimization strategies inform our training methodology in {title}.",
            'applications': f"Building on these applications, {title} provides a more comprehensive solution.",
            'evaluation': f"We adopt similar evaluation protocols while introducing new metrics specific to {title}.",
            'theoretical': f"Our theoretical contributions extend these foundational works.",
            'general': f"These works provide context for understanding the contribution of {title}.",
        }
        return connections.get(theme, f"These works inform the development of {title}.")
    
    def _generate_introduction(self, project_overview) -> str:
        """Generate introduction paragraph for Related Work section."""
        keywords = self._get_overview_attr(project_overview, 'keywords', []) or []
        domain = ', '.join(keywords[:3]) if keywords else 'this research area'
        
        return (f"This section reviews existing literature relevant to {domain}. "
               f"We organize the discussion by research themes, highlighting both "
               f"foundational contributions and recent advances that inform our approach.")
    
    def _generate_grouped_content(
        self,
        groups: List[CitationGroup],
        project_overview
    ) -> str:
        """Generate the main grouped content."""
        sections = []
        citation_index = 1
        
        for group in groups:
            content_parts = []
            
            # Generate discussion for each citation in group
            for citation in group.citations:
                author = self._format_author(citation)
                year = citation.get('year', '')
                title = citation.get('title', 'this work')
                
                # Create citation sentence
                if year:
                    sentence = f"{author} [{citation_index}] ({year}) presented {self._summarize_contribution(citation)}. "
                else:
                    sentence = f"{author} [{citation_index}] presented {self._summarize_contribution(citation)}. "
                
                content_parts.append(sentence)
                citation_index += 1
            
            # Add connection to project
            content_parts.append(f"\n{group.connection_to_project}")
            
            # Format group section
            group_text = self.GROUP_TEMPLATE.format(
                theme_title=group.description,
                content=' '.join(content_parts)
            )
            sections.append(group_text)
        
        return '\n'.join(sections)
    
    def _generate_summary(
        self,
        groups: List[CitationGroup],
        project_overview
    ) -> str:
        """Generate summary paragraph differentiating from existing work."""
        title = self._get_overview_attr(project_overview, 'title', 'Our approach')
        contributions = self._get_overview_attr(project_overview, 'contributions', []) or []
        
        summary_parts = [
            f"In summary, while existing work has made significant progress, "
            f"several gaps remain. {title} addresses these limitations by:"
        ]
        
        if contributions:
            for i, contrib in enumerate(contributions[:3], 1):
                summary_parts.append(f"({i}) {contrib};")
        else:
            summary_parts.append(
                "providing a novel approach that synthesizes insights from multiple "
                "research directions while addressing their individual limitations."
            )
        
        return ' '.join(summary_parts)
    
    def _format_author(self, citation: Dict[str, Any]) -> str:
        """Format author name for citation."""
        authors = citation.get('authors', [])
        if not authors:
            return "The authors"
        
        first_author = authors[0] if isinstance(authors, list) else str(authors)
        
        # Extract last name if full name provided
        if isinstance(first_author, str):
            parts = first_author.split()
            if len(parts) > 1:
                return f"{parts[-1]} et al."
            return first_author
        
        return "The authors"
    
    def _summarize_contribution(self, citation: Dict[str, Any]) -> str:
        """Generate a brief summary of citation's contribution."""
        title = citation.get('title', '')
        abstract = citation.get('abstract', '')
        
        # Extract key contribution from title
        if title:
            # Look for action words
            lower_title = title.lower()
            if 'novel' in lower_title or 'new' in lower_title:
                return f"a novel approach to {title.split(':')[-1].strip() if ':' in title else title}"
            elif 'improve' in lower_title or 'enhanc' in lower_title:
                return f"improvements in {title.split(':')[-1].strip() if ':' in title else title}"
            else:
                return f"work on {title.lower()}"
        
        return "relevant research in this area"
    
    async def extend_with_recent_papers(
        self,
        current_section: RelatedStudiesSection,
        new_citations: List[Dict[str, Any]],
        year_filter: int = 2024
    ) -> RelatedStudiesSection:
        """
        Extend existing Related Studies with newer papers.
        
        Args:
            current_section: Current related studies section
            new_citations: New citations to add
            year_filter: Minimum year for new citations
            
        Returns:
            Updated RelatedStudiesSection
        """
        # Filter for recent papers
        recent = [c for c in new_citations if c.get('year', 0) >= year_filter]
        
        # Add to existing groups or create new ones
        for citation in recent:
            theme = self._detect_theme(citation)
            
            # Find matching group
            matched = False
            for group in current_section.groups:
                if group.theme == theme:
                    group.citations.append(citation)
                    matched = True
                    break
            
            if not matched:
                # Create new group
                new_group = CitationGroup(
                    theme=theme,
                    description=self._get_theme_description(theme),
                    citations=[citation],
                    connection_to_project=""
                )
                current_section.groups.append(new_group)
        
        # Update total citations
        current_section.total_citations += len(recent)
        
        return current_section
