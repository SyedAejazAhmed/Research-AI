"""
Paper Drafting Agent for GPT Researcher
Transforms research findings into structured academic paper format
with proper sections, citations, and formatting.
"""

import re
from typing import Dict, List, Optional
from datetime import datetime


class PaperDraftingAgent:
    """
    Agent for drafting academic papers from research findings.
    Structures content into standard academic paper format.
    """
    
    PAPER_SECTIONS = {
        'abstract': 'Abstract',
        'introduction': 'Introduction',
        'literature_review': 'Literature Review',
        'methodology': 'Methodology',
        'results': 'Results and Findings',
        'discussion': 'Discussion',
        'conclusion': 'Conclusion',
        'references': 'References'
    }
    
    def __init__(self):
        self.paper_template = self._load_template()
    
    def _load_template(self) -> Dict[str, str]:
        """Load paper structure templates"""
        return {
            'ieee': {
                'format': 'IEEE',
                'title_format': '# {title}\n\n',
                'author_format': '**Authors:** {authors}\n\n',
                'abstract_format': '## Abstract\n\n{content}\n\n',
                'section_format': '## {section}\n\n{content}\n\n',
                'subsection_format': '### {subsection}\n\n{content}\n\n',
            },
            'acm': {
                'format': 'ACM',
                'title_format': '# {title}\n\n',
                'author_format': '{authors}\n\n',
                'abstract_format': '## ABSTRACT\n\n{content}\n\n',
                'section_format': '## {number}. {section}\n\n{content}\n\n',
                'subsection_format': '### {number} {subsection}\n\n{content}\n\n',
            },
            'springer': {
                'format': 'Springer',
                'title_format': '# {title}\n\n',
                'author_format': '*{authors}*\n\n',
                'abstract_format': '**Abstract:** {content}\n\n',
                'section_format': '## {section}\n\n{content}\n\n',
                'subsection_format': '### {subsection}\n\n{content}\n\n',
            }
        }
    
    def draft_paper(
        self,
        research_report: str,
        citations: List[Dict],
        title: str,
        paper_format: str = 'ieee',
        include_sections: Optional[List[str]] = None
    ) -> str:
        """
        Draft a complete academic paper from research findings.
        
        Args:
            research_report: The main research content
            citations: List of citation dictionaries
            title: Paper title
            paper_format: Format style (ieee, acm, springer)
            include_sections: Specific sections to include
            
        Returns:
            Formatted academic paper as markdown
        """
        template = self.paper_template.get(paper_format.lower(), self.paper_template['ieee'])
        
        if include_sections is None:
            include_sections = list(self.PAPER_SECTIONS.keys())
        
        # Parse research report into sections
        sections = self._parse_research_report(research_report)
        
        # Build paper
        paper = []
        
        # Title
        paper.append(template['title_format'].format(title=title))
        
        # Abstract
        if 'abstract' in include_sections:
            abstract = self._generate_abstract(sections, citations)
            paper.append(template['abstract_format'].format(content=abstract))
        
        # Keywords
        keywords = self._extract_keywords(sections)
        paper.append(f"**Keywords:** {', '.join(keywords)}\n\n")
        
        # Main sections
        section_number = 1
        for section_key in include_sections:
            if section_key in ['abstract', 'references']:
                continue
                
            section_title = self.PAPER_SECTIONS[section_key]
            section_content = self._generate_section_content(
                section_key,
                sections,
                citations
            )
            
            if section_content:
                if paper_format.lower() == 'acm':
                    formatted = template['section_format'].format(
                        number=section_number,
                        section=section_title.upper(),
                        content=section_content
                    )
                else:
                    formatted = template['section_format'].format(
                        section=section_title,
                        content=section_content
                    )
                paper.append(formatted)
                section_number += 1
        
        # References
        if 'references' in include_sections and citations:
            references = self._format_references(citations, paper_format)
            paper.append(template['section_format'].format(
                section='References',
                content=references
            ))
        
        return ''.join(paper)
    
    def _parse_research_report(self, report: str) -> Dict[str, str]:
        """Parse research report into logical sections"""
        sections = {}
        
        # Try to identify existing sections
        section_pattern = r'#{1,3}\s+([^\n]+)\n(.*?)(?=\n#{1,3}\s+|$)'
        matches = re.finditer(section_pattern, report, re.DOTALL)
        
        for match in matches:
            section_title = match.group(1).strip()
            section_content = match.group(2).strip()
            sections[section_title.lower()] = section_content
        
        # If no sections found, treat entire report as content
        if not sections:
            sections['content'] = report
        
        return sections
    
    def _generate_abstract(self, sections: Dict[str, str], citations: List[Dict]) -> str:
        """Generate abstract from research content"""
        # Extract first few paragraphs or introduction
        content = sections.get('introduction', sections.get('content', ''))
        
        # Take first 250-300 words
        words = content.split()[:250]
        abstract = ' '.join(words)
        
        # Add research scope statement
        num_sources = len(citations)
        abstract += f" This research synthesizes findings from {num_sources} academic sources to provide comprehensive insights."
        
        return abstract
    
    def _extract_keywords(self, sections: Dict[str, str]) -> List[str]:
        """Extract keywords from content"""
        # Simple keyword extraction - could be enhanced with NLP
        content = ' '.join(sections.values()).lower()
        
        # Common academic keywords to look for
        potential_keywords = [
            'machine learning', 'deep learning', 'neural networks',
            'artificial intelligence', 'natural language processing',
            'computer vision', 'reinforcement learning', 'optimization',
            'algorithm', 'model', 'framework', 'system', 'approach',
            'methodology', 'evaluation', 'performance', 'analysis'
        ]
        
        keywords = []
        for keyword in potential_keywords:
            if keyword in content:
                keywords.append(keyword)
                if len(keywords) >= 5:
                    break
        
        return keywords if keywords else ['research', 'analysis', 'study']
    
    def _generate_section_content(
        self,
        section_key: str,
        sections: Dict[str, str],
        citations: List[Dict]
    ) -> str:
        """Generate content for a specific paper section"""
        
        if section_key == 'introduction':
            return self._generate_introduction(sections, citations)
        
        elif section_key == 'literature_review':
            return self._generate_literature_review(sections, citations)
        
        elif section_key == 'methodology':
            return self._generate_methodology(sections)
        
        elif section_key == 'results':
            return self._generate_results(sections)
        
        elif section_key == 'discussion':
            return self._generate_discussion(sections, citations)
        
        elif section_key == 'conclusion':
            return self._generate_conclusion(sections)
        
        return sections.get(section_key, '')
    
    def _generate_introduction(self, sections: Dict[str, str], citations: List[Dict]) -> str:
        """Generate introduction section"""
        intro = sections.get('introduction', sections.get('content', ''))
        
        # Split into paragraphs
        paragraphs = [p.strip() for p in intro.split('\n\n') if p.strip()]
        
        # Take first 2-3 paragraphs for introduction
        intro_content = '\n\n'.join(paragraphs[:3])
        
        # Add research objective statement
        intro_content += f"\n\nThis paper presents a comprehensive review and analysis of current research in this domain, drawing from {len(citations)} authoritative sources."
        
        return intro_content
    
    def _generate_literature_review(self, sections: Dict[str, str], citations: List[Dict]) -> str:
        """Generate literature review section"""
        # Group citations by year
        citations_by_year = {}
        for citation in citations:
            year = citation.get('year', 'N/A')
            if year not in citations_by_year:
                citations_by_year[year] = []
            citations_by_year[year].append(citation)
        
        review = "Recent research in this field has demonstrated significant advancements.\n\n"
        
        # Summarize by year (recent first)
        sorted_years = sorted([y for y in citations_by_year.keys() if y != 'N/A'], reverse=True)
        
        for year in sorted_years[:5]:  # Last 5 years
            papers = citations_by_year[year]
            review += f"### Research from {year}\n\n"
            review += f"During {year}, researchers focused on multiple aspects of this domain:\n\n"
            
            for paper in papers[:5]:  # Top 5 papers per year
                title = paper.get('title', 'Untitled')
                authors = paper.get('authors', ['Unknown'])
                if isinstance(authors, list):
                    authors_str = authors[0] if authors else 'Unknown'
                else:
                    authors_str = authors
                    
                review += f"- **{title}** by {authors_str} explored important aspects of the field.\n"
            
            review += "\n"
        
        return review
    
    def _generate_methodology(self, sections: Dict[str, str]) -> str:
        """Generate methodology section"""
        methodology = "### Research Approach\n\n"
        methodology += "This study employs a systematic literature review methodology, combining:\n\n"
        methodology += "1. **Comprehensive Source Selection**: Academic papers from multiple authoritative databases\n"
        methodology += "2. **Multi-Source Validation**: Cross-referencing findings across sources\n"
        methodology += "3. **Temporal Analysis**: Examining research evolution over time\n"
        methodology += "4. **Thematic Synthesis**: Identifying key themes and patterns\n\n"
        
        # Add any methodology mentioned in original report
        if 'methodology' in sections or 'methods' in sections:
            methodology += sections.get('methodology', sections.get('methods', ''))
        
        return methodology
    
    def _generate_results(self, sections: Dict[str, str]) -> str:
        """Generate results section"""
        results = "### Key Findings\n\n"
        
        content = sections.get('results', sections.get('content', ''))
        
        # Extract bullet points or numbered lists
        lines = content.split('\n')
        findings = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('*') or line.startswith('-') or line.startswith('•'):
                findings.append(line)
            elif re.match(r'^\d+\.', line):
                findings.append(line)
        
        if findings:
            results += '\n'.join(findings[:10])  # Top 10 findings
        else:
            # Use first few paragraphs
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
            results += '\n\n'.join(paragraphs[:4])
        
        return results
    
    def _generate_discussion(self, sections: Dict[str, str], citations: List[Dict]) -> str:
        """Generate discussion section"""
        discussion = "### Implications and Significance\n\n"
        discussion += "The findings from this research reveal several important insights:\n\n"
        
        content = sections.get('discussion', sections.get('content', ''))
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        # Take middle section of content for discussion
        start_idx = len(paragraphs) // 3
        end_idx = 2 * len(paragraphs) // 3
        discussion_content = paragraphs[start_idx:end_idx]
        
        discussion += '\n\n'.join(discussion_content[:4])
        
        return discussion
    
    def _generate_conclusion(self, sections: Dict[str, str]) -> str:
        """Generate conclusion section"""
        conclusion = ""
        
        content = sections.get('conclusion', sections.get('content', ''))
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        # Take last few paragraphs
        conclusion_content = paragraphs[-3:] if len(paragraphs) >= 3 else paragraphs
        conclusion += '\n\n'.join(conclusion_content)
        
        conclusion += "\n\n### Future Directions\n\n"
        conclusion += "This research opens several avenues for future investigation, including enhanced methodologies, "
        conclusion += "broader dataset coverage, and deeper analysis of emerging trends in the field."
        
        return conclusion
    
    def _format_references(self, citations: List[Dict], paper_format: str) -> str:
        """Format references section"""
        # Sort citations alphabetically by author or year
        sorted_citations = sorted(
            citations,
            key=lambda x: (x.get('authors', [''])[0] if isinstance(x.get('authors'), list) else x.get('authors', ''), 
                          x.get('year', '9999'))
        )
        
        references = []
        for i, citation in enumerate(sorted_citations, 1):
            ref_text = citation.get('formatted_citation', '')
            
            # Add numbering for IEEE/ACM style
            if paper_format.lower() in ['ieee', 'acm']:
                references.append(f"[{i}] {ref_text}")
            else:
                references.append(ref_text)
        
        return '\n\n'.join(references)
    
    def generate_multiple_formats(
        self,
        research_report: str,
        citations: List[Dict],
        title: str
    ) -> Dict[str, str]:
        """Generate paper in multiple formats"""
        formats = {}
        
        for format_name in ['ieee', 'acm', 'springer']:
            formats[format_name] = self.draft_paper(
                research_report=research_report,
                citations=citations,
                title=title,
                paper_format=format_name
            )
        
        return formats


# Convenience function for quick paper generation
def draft_academic_paper(
    research_report: str,
    citations: List[Dict],
    title: str,
    paper_format: str = 'ieee',
    include_sections: Optional[List[str]] = None
) -> str:
    """
    Quick function to draft an academic paper.
    
    Args:
        research_report: Research findings content
        citations: List of citation dictionaries
        title: Paper title
        paper_format: Format style (ieee, acm, springer)
        include_sections: Sections to include
        
    Returns:
        Formatted academic paper as markdown
    """
    agent = PaperDraftingAgent()
    return agent.draft_paper(
        research_report=research_report,
        citations=citations,
        title=title,
        paper_format=paper_format,
        include_sections=include_sections
    )


if __name__ == '__main__':
    # Test the paper drafting agent
    sample_report = """
    # Introduction
    
    Machine learning has revolutionized how we approach data analysis and prediction tasks.
    Recent advances in deep learning have enabled breakthroughs in computer vision, natural language processing, and more.
    
    # Key Findings
    
    - Neural networks can learn complex patterns from data
    - Transfer learning enables efficient model training
    - Attention mechanisms improve model performance
    
    # Discussion
    
    These findings suggest that machine learning will continue to advance rapidly.
    Integration with other technologies opens new possibilities.
    """
    
    sample_citations = [
        {
            'title': 'Deep Learning in Neural Networks',
            'authors': ['Smith, J.'],
            'year': '2023',
            'formatted_citation': 'Smith, J. (2023). Deep Learning in Neural Networks. Journal of AI Research.'
        },
        {
            'title': 'Attention Mechanisms for NLP',
            'authors': ['Johnson, A.'],
            'year': '2024',
            'formatted_citation': 'Johnson, A. (2024). Attention Mechanisms for NLP. ACM Computing Surveys.'
        }
    ]
    
    print("=" * 80)
    print("Paper Drafting Agent Test")
    print("=" * 80)
    
    paper = draft_academic_paper(
        research_report=sample_report,
        citations=sample_citations,
        title="Advances in Machine Learning: A Comprehensive Review"
    )
    
    print(paper)
