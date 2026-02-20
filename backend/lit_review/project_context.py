"""
Project Context Retriever
=========================

Extracts project information from:
- GitHub repositories (README, docs, paper directories)
- URLs (project homepages, documentation sites)
- Documents (PDF, DOCX, LaTeX, Markdown)

Generates a structured project overview JSON.
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from urllib.parse import urlparse
import asyncio

logger = logging.getLogger(__name__)

# Try to import optional dependencies
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    logger.warning("requests not available - HTTP fetching disabled")

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    logger.warning("BeautifulSoup not available - HTML parsing disabled")

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False
    logger.warning("PyMuPDF not available - PDF parsing disabled")


@dataclass
class ProjectOverview:
    """Structured project overview."""
    title: str
    description: str = ""
    keywords: List[str] = None
    objectives: List[str] = None
    domain: str = ""
    technologies: List[str] = None
    problem: str = ""
    motivation: str = ""
    method: str = ""
    contributions: List[str] = None
    source_type: str = "unknown"  # github, url, document, title_only
    confidence: float = 0.0
    
    def __post_init__(self):
        # Initialize lists if None
        if self.keywords is None:
            self.keywords = []
        if self.objectives is None:
            self.objectives = []
        if self.technologies is None:
            self.technologies = []
        if self.contributions is None:
            self.contributions = []
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


class ProjectContextRetriever:
    """
    Retrieves and parses project context from various sources.
    
    Supports:
    - GitHub repositories (via API or scraping)
    - Project URLs (documentation sites, homepages)
    - Document files (PDF, DOCX, LaTeX, Markdown)
    - Fallback to title-only extraction
    """
    
    # File patterns to look for in GitHub repos
    README_PATTERNS = ['README.md', 'README.rst', 'README.txt', 'README']
    DOCS_PATTERNS = ['docs/', 'documentation/', 'doc/']
    PAPER_PATTERNS = ['paper/', 'papers/', 'arxiv/', 'manuscript/']
    IGNORE_PATTERNS = ['.git', 'node_modules', '__pycache__', '.venv', 'venv']
    
    # Section headers to extract
    SECTION_HEADERS = {
        'problem': ['problem', 'challenge', 'issue', 'motivation', 'background'],
        'method': ['method', 'approach', 'solution', 'architecture', 'implementation', 'how it works'],
        'contributions': ['contribution', 'features', 'key points', 'highlights', 'what we offer'],
    }
    
    def __init__(self, github_token: Optional[str] = None, timeout: int = 30):
        """
        Initialize the retriever.
        
        Args:
            github_token: Optional GitHub API token for higher rate limits
            timeout: Request timeout in seconds
        """
        self.github_token = github_token
        self.timeout = timeout
        self.headers = {
            'User-Agent': 'GPT-Researcher-LitReview/1.0',
            'Accept': 'application/json, text/html, text/plain'
        }
        if github_token:
            self.headers['Authorization'] = f'token {github_token}'
    
    async def extract_from_github(self, repo_url: str) -> ProjectOverview:
        """
        Extract project context from a GitHub repository.
        
        Args:
            repo_url: GitHub repository URL
            
        Returns:
            ProjectOverview with extracted information
        """
        logger.info(f"Extracting context from GitHub: {repo_url}")
        
        # Parse GitHub URL
        owner, repo = self._parse_github_url(repo_url)
        if not owner or not repo:
            logger.warning(f"Invalid GitHub URL: {repo_url}")
            return self._create_fallback_overview(repo_url, "github")
        
        # Fetch README content
        readme_content = await self._fetch_github_readme(owner, repo)
        
        # Fetch additional docs if available
        docs_content = await self._fetch_github_docs(owner, repo)
        
        # Fetch repo metadata
        metadata = await self._fetch_github_metadata(owner, repo)
        
        # Combine and parse
        combined_content = f"{readme_content}\n\n{docs_content}"
        overview = self._parse_markdown_content(combined_content, metadata)
        overview.source_type = "github"
        
        return overview
    
    async def extract_from_url(self, url: str) -> ProjectOverview:
        """
        Extract project context from a URL (documentation site, homepage).
        
        Args:
            url: Project URL
            
        Returns:
            ProjectOverview with extracted information
        """
        logger.info(f"Extracting context from URL: {url}")
        
        if not HAS_REQUESTS or not HAS_BS4:
            logger.warning("Required dependencies not available for URL scraping")
            return self._create_fallback_overview(url, "url")
        
        try:
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract main content
            main_content = self._extract_main_content(soup)
            title = self._extract_title(soup)
            
            overview = self._parse_html_content(main_content, title)
            overview.source_type = "url"
            
            return overview
            
        except Exception as e:
            logger.error(f"Failed to extract from URL: {e}")
            return self._create_fallback_overview(url, "url")
    
    async def extract_from_document(self, file_path: str) -> ProjectOverview:
        """
        Extract project context from a document file.
        
        Args:
            file_path: Path to document (PDF, DOCX, MD, TEX)
            
        Returns:
            ProjectOverview with extracted information
        """
        logger.info(f"Extracting context from document: {file_path}")
        
        file_ext = file_path.lower().split('.')[-1]
        
        content = ""
        if file_ext == 'pdf':
            content = self._extract_from_pdf(file_path)
        elif file_ext == 'docx':
            content = self._extract_from_docx(file_path)
        elif file_ext in ['md', 'markdown']:
            content = self._extract_from_markdown(file_path)
        elif file_ext in ['tex', 'latex']:
            content = self._extract_from_latex(file_path)
        else:
            logger.warning(f"Unsupported file type: {file_ext}")
            return self._create_fallback_overview(file_path, "document")
        
        overview = self._parse_document_content(content)
        overview.source_type = "document"
        
        return overview
    
    async def extract_from_title(self, title: str, description: str = "") -> ProjectOverview:
        """
        Create a project overview from just the title (fallback).
        
        Args:
            title: Project title
            description: Optional description
            
        Returns:
            ProjectOverview with inferred information
        """
        logger.info(f"Creating overview from title: {title}")
        
        # Extract keywords from title
        keywords = self._extract_keywords_from_text(title + " " + description)
        
        # Infer domain from keywords
        domain = self._infer_domain(keywords)
        
        return ProjectOverview(
            title=title,
            description=description or f"Research on {title}",
            keywords=keywords[:10],
            objectives=[f"Investigate {title}", "Analyze related literature", "Propose improvements"],
            domain=domain,
            technologies=[],
            problem=f"Research problem related to: {title}",
            motivation=description or f"Advancing the field of {', '.join(keywords[:3]) if keywords else 'research'}",
            method="Method to be determined based on literature review",
            contributions=["Novel approach to " + title.lower()],
            source_type="title_only",
            confidence=0.3
        )
    
    def _infer_domain(self, keywords: List[str]) -> str:
        """Infer research domain from keywords."""
        domain_keywords = {
            'Machine Learning': ['machine learning', 'ml', 'deep learning', 'neural', 'ai', 'artificial intelligence'],
            'Natural Language Processing': ['nlp', 'language', 'text', 'sentiment', 'translation', 'bert', 'gpt'],
            'Computer Vision': ['vision', 'image', 'video', 'object detection', 'recognition', 'cnn'],
            'Healthcare': ['health', 'medical', 'clinical', 'patient', 'disease', 'diagnosis'],
            'Security': ['security', 'privacy', 'encryption', 'cyber', 'malware', 'authentication'],
            'Software Engineering': ['software', 'code', 'programming', 'development', 'testing'],
            'Data Science': ['data', 'analytics', 'statistics', 'visualization', 'big data'],
        }
        
        keywords_lower = [k.lower() for k in keywords]
        
        for domain, domain_kws in domain_keywords.items():
            if any(kw in ' '.join(keywords_lower) for kw in domain_kws):
                return domain
        
        return "General Research"
    
    async def extract(
        self,
        github_url: Optional[str] = None,
        project_url: Optional[str] = None,
        document_path: Optional[str] = None,
        title: Optional[str] = None,
        description: str = ""
    ) -> ProjectOverview:
        """
        Extract project context from the best available source.
        
        Priority: GitHub > Document > URL > Title
        
        Args:
            github_url: GitHub repository URL
            project_url: Project documentation URL
            document_path: Path to project document
            title: Project title (fallback)
            description: Optional project description
            
        Returns:
            ProjectOverview from the best source
        """
        # Try sources in priority order
        if github_url:
            try:
                overview = await self.extract_from_github(github_url)
                if overview.confidence > 0.5:
                    return overview
            except Exception as e:
                logger.warning(f"GitHub extraction failed: {e}")
        
        if document_path:
            try:
                overview = await self.extract_from_document(document_path)
                if overview.confidence > 0.5:
                    return overview
            except Exception as e:
                logger.warning(f"Document extraction failed: {e}")
        
        if project_url:
            try:
                overview = await self.extract_from_url(project_url)
                if overview.confidence > 0.4:
                    return overview
            except Exception as e:
                logger.warning(f"URL extraction failed: {e}")
        
        # Fallback to title
        if title:
            return await self.extract_from_title(title, description)
        
        # Last resort
        return ProjectOverview(
            title="Untitled Project",
            problem="Problem not specified",
            motivation="Motivation not specified",
            method="Method not specified",
            contributions=[],
            keywords=[],
            source_type="none",
            confidence=0.0
        )
    
    # =========================================================================
    # Private Helper Methods
    # =========================================================================
    
    def _parse_github_url(self, url: str) -> tuple:
        """Parse GitHub URL to extract owner and repo name."""
        patterns = [
            r'github\.com/([^/]+)/([^/]+?)(?:\.git)?(?:/.*)?$',
            r'github\.com:([^/]+)/([^/]+?)(?:\.git)?$',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1), match.group(2)
        
        return None, None
    
    async def _fetch_github_readme(self, owner: str, repo: str) -> str:
        """Fetch README from GitHub."""
        if not HAS_REQUESTS:
            return ""
        
        # Try GitHub API first
        api_url = f"https://api.github.com/repos/{owner}/{repo}/readme"
        
        try:
            response = requests.get(api_url, headers={
                **self.headers,
                'Accept': 'application/vnd.github.v3.raw'
            }, timeout=self.timeout)
            
            if response.status_code == 200:
                return response.text
                
        except Exception as e:
            logger.warning(f"GitHub API failed: {e}")
        
        # Fallback to raw URL
        for readme in self.README_PATTERNS:
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/{readme}"
            try:
                response = requests.get(raw_url, headers=self.headers, timeout=self.timeout)
                if response.status_code == 200:
                    return response.text
            except:
                pass
            
            # Try master branch
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/master/{readme}"
            try:
                response = requests.get(raw_url, headers=self.headers, timeout=self.timeout)
                if response.status_code == 200:
                    return response.text
            except:
                pass
        
        return ""
    
    async def _fetch_github_docs(self, owner: str, repo: str) -> str:
        """Fetch additional documentation from GitHub."""
        # This would fetch docs/ directory content
        # Simplified for now
        return ""
    
    async def _fetch_github_metadata(self, owner: str, repo: str) -> Dict[str, Any]:
        """Fetch repository metadata from GitHub API."""
        if not HAS_REQUESTS:
            return {}
        
        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        
        try:
            response = requests.get(api_url, headers=self.headers, timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                return {
                    'name': data.get('name', ''),
                    'description': data.get('description', ''),
                    'topics': data.get('topics', []),
                    'language': data.get('language', ''),
                    'stars': data.get('stargazers_count', 0),
                }
        except Exception as e:
            logger.warning(f"Failed to fetch metadata: {e}")
        
        return {}
    
    def _parse_markdown_content(self, content: str, metadata: Dict[str, Any] = None) -> ProjectOverview:
        """Parse markdown content to extract project information."""
        metadata = metadata or {}
        
        # Extract title
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        title = title_match.group(1) if title_match else metadata.get('name', 'Untitled')
        
        # Extract sections
        problem = self._extract_section(content, self.SECTION_HEADERS['problem'])
        method = self._extract_section(content, self.SECTION_HEADERS['method'])
        contributions = self._extract_list_section(content, self.SECTION_HEADERS['contributions'])
        
        # Extract keywords from topics or content
        keywords = metadata.get('topics', [])
        if not keywords:
            keywords = self._extract_keywords_from_text(content)
        
        # Calculate confidence based on what we found
        confidence = 0.3
        if title and title != 'Untitled':
            confidence += 0.2
        if problem:
            confidence += 0.15
        if method:
            confidence += 0.15
        if contributions:
            confidence += 0.1
        if keywords:
            confidence += 0.1
        
        return ProjectOverview(
            title=title,
            problem=problem or metadata.get('description', 'Problem not clearly stated'),
            motivation=self._extract_motivation(content) or metadata.get('description', ''),
            method=method or 'Method details in repository',
            contributions=contributions or ['See repository for details'],
            keywords=keywords[:10],
            confidence=min(confidence, 1.0)
        )
    
    def _parse_html_content(self, content: str, title: str) -> ProjectOverview:
        """Parse HTML content to extract project information."""
        # Clean HTML
        text = re.sub(r'<[^>]+>', ' ', content)
        text = re.sub(r'\s+', ' ', text).strip()
        
        keywords = self._extract_keywords_from_text(text)
        
        return ProjectOverview(
            title=title or "Untitled Project",
            problem=self._find_section_in_text(text, ['problem', 'challenge', 'issue']),
            motivation=self._find_section_in_text(text, ['motivation', 'why', 'background']),
            method=self._find_section_in_text(text, ['method', 'how', 'approach', 'solution']),
            contributions=[],
            keywords=keywords[:10],
            confidence=0.5
        )
    
    def _parse_document_content(self, content: str) -> ProjectOverview:
        """Parse document content to extract project information."""
        # Extract title (usually first line or heading)
        lines = content.strip().split('\n')
        title = lines[0].strip() if lines else "Untitled"
        
        keywords = self._extract_keywords_from_text(content)
        
        return ProjectOverview(
            title=title,
            problem=self._find_section_in_text(content, ['problem', 'introduction', 'abstract']),
            motivation=self._find_section_in_text(content, ['motivation', 'background']),
            method=self._find_section_in_text(content, ['method', 'methodology', 'approach']),
            contributions=self._find_contributions_in_text(content),
            keywords=keywords[:10],
            confidence=0.6
        )
    
    def _extract_section(self, content: str, headers: List[str]) -> str:
        """Extract content under a section header."""
        for header in headers:
            # Match markdown headers
            pattern = rf'^##?\s*{header}[^\n]*\n(.*?)(?=^##?\s|\Z)'
            match = re.search(pattern, content, re.MULTILINE | re.IGNORECASE | re.DOTALL)
            if match:
                section = match.group(1).strip()
                # Clean up and limit length
                section = re.sub(r'\n+', ' ', section)
                return section[:1000]
        return ""
    
    def _extract_list_section(self, content: str, headers: List[str]) -> List[str]:
        """Extract list items from a section."""
        section = self._extract_section(content, headers)
        if not section:
            return []
        
        # Extract bullet points
        items = re.findall(r'[-*•]\s*(.+?)(?=[-*•]|\Z)', section, re.DOTALL)
        return [item.strip()[:200] for item in items if item.strip()]
    
    def _extract_motivation(self, content: str) -> str:
        """Extract motivation/background section."""
        # Look for abstract or introduction first
        for header in ['abstract', 'introduction', 'background', 'motivation']:
            section = self._extract_section(content, [header])
            if section:
                return section[:500]
        return ""
    
    def _extract_keywords_from_text(self, text: str) -> List[str]:
        """Extract keywords from text using simple NLP."""
        # Common technical terms to look for
        tech_terms = [
            'machine learning', 'deep learning', 'neural network', 'transformer',
            'attention', 'CNN', 'RNN', 'LSTM', 'GRU', 'BERT', 'GPT',
            'NLP', 'computer vision', 'reinforcement learning', 'optimization',
            'classification', 'regression', 'clustering', 'segmentation',
            'detection', 'recognition', 'generation', 'synthesis',
            'embedding', 'representation', 'feature', 'model', 'algorithm'
        ]
        
        text_lower = text.lower()
        found_terms = []
        
        for term in tech_terms:
            if term.lower() in text_lower:
                found_terms.append(term)
        
        # Also extract capitalized words/phrases as potential keywords
        caps_pattern = r'\b[A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*\b'
        caps_words = re.findall(caps_pattern, text)
        for word in caps_words[:20]:
            if len(word) > 2 and word not in ['The', 'This', 'These', 'That']:
                if word.lower() not in [t.lower() for t in found_terms]:
                    found_terms.append(word)
        
        return list(set(found_terms))[:15]
    
    def _find_section_in_text(self, text: str, keywords: List[str]) -> str:
        """Find relevant section in plain text based on keywords."""
        sentences = re.split(r'[.!?]+', text)
        
        for keyword in keywords:
            for i, sentence in enumerate(sentences):
                if keyword.lower() in sentence.lower():
                    # Return this sentence and next few
                    context = ' '.join(sentences[i:i+3])
                    return context[:500]
        
        return ""
    
    def _find_contributions_in_text(self, text: str) -> List[str]:
        """Find contribution statements in text."""
        patterns = [
            r'we (?:propose|present|introduce|develop|contribute)\s+(.+?)[.]',
            r'our (?:main |key |primary )?contribution[s]?\s+(?:is|are|include)\s+(.+?)[.]',
            r'(?:•|-)(.+?)(?=•|-|\n\n|\Z)',
        ]
        
        contributions = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if len(match) > 10:
                    contributions.append(match.strip()[:200])
        
        return contributions[:5]
    
    def _extract_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file."""
        if not HAS_PYMUPDF:
            return ""
        
        try:
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text[:50000]  # Limit to ~50k chars
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            return ""
    
    def _extract_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX file."""
        try:
            from docx import Document
            doc = Document(file_path)
            text = '\n'.join([para.text for para in doc.paragraphs])
            return text[:50000]
        except Exception as e:
            logger.error(f"DOCX extraction failed: {e}")
            return ""
    
    def _extract_from_markdown(self, file_path: str) -> str:
        """Extract text from Markdown file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()[:50000]
        except Exception as e:
            logger.error(f"Markdown extraction failed: {e}")
            return ""
    
    def _extract_from_latex(self, file_path: str) -> str:
        """Extract text from LaTeX file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            # Remove LaTeX commands
            text = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', content)
            text = re.sub(r'\\[a-zA-Z]+', '', text)
            text = re.sub(r'[{}]', '', text)
            return text[:50000]
        except Exception as e:
            logger.error(f"LaTeX extraction failed: {e}")
            return ""
    
    def _extract_main_content(self, soup) -> str:
        """Extract main content from HTML soup."""
        # Remove script and style elements
        for script in soup(['script', 'style', 'nav', 'footer', 'header']):
            script.decompose()
        
        # Try to find main content area
        main = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
        if main:
            return main.get_text(separator=' ', strip=True)
        
        return soup.get_text(separator=' ', strip=True)
    
    def _extract_title(self, soup) -> str:
        """Extract title from HTML soup."""
        title = soup.find('h1')
        if title:
            return title.get_text(strip=True)
        
        title = soup.find('title')
        if title:
            return title.get_text(strip=True)
        
        return ""
    
    def _create_fallback_overview(self, source: str, source_type: str) -> ProjectOverview:
        """Create a minimal fallback overview."""
        return ProjectOverview(
            title=f"Project from {source_type}",
            problem="Unable to extract project details",
            motivation="Source processing failed",
            method="",
            contributions=[],
            keywords=[],
            source_type=source_type,
            confidence=0.1
        )
