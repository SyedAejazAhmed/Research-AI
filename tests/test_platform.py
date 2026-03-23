"""
Test Suite for Research AI Platform
====================================
Comprehensive tests for all major components.
"""

import pytest
import asyncio
from pathlib import Path
import tempfile
import os

# Import components to test
from app.database.schema import ResearchDatabase
from app.agents.rag_system import RAGSystem, OrderedReferenceAgent
from app.agents.latex_writing_agent import LaTeXWritingAgent
from app.agents.github_analyzer import GitHubRepoAnalyzer


@pytest.fixture
def temp_db():
    """Create temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    db = ResearchDatabase(db_path)
    yield db

    # Cleanup
    db.close()
    os.unlink(db_path)


@pytest.fixture
def rag_system(temp_db):
    """Create RAG system with temp database"""
    return RAGSystem(db_manager=temp_db, model_name="all-MiniLM-L6-v2")


# =============================================================================
# Database Tests
# =============================================================================

def test_database_initialization(temp_db):
    """Test database schema creation"""
    assert temp_db.conn is not None

    # Check tables exist
    cursor = temp_db.conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}

    expected_tables = {
        'citations', 'collections', 'citation_collections',
        'embeddings', 'reference_order', 'papers',
        'paper_citations', 'research_sessions', 'github_repos'
    }

    assert expected_tables.issubset(tables)


def test_add_citation(temp_db):
    """Test adding a citation"""
    success = temp_db.add_citation(
        citation_id="test123",
        title="Test Paper",
        authors=["John Doe", "Jane Smith"],
        year=2024,
        doi="10.1234/test"
    )

    assert success is True

    # Retrieve citation
    citation = temp_db.get_citation("test123")
    assert citation is not None
    assert citation["title"] == "Test Paper"
    assert citation["year"] == 2024


def test_duplicate_citation(temp_db):
    """Test duplicate citation handling"""
    temp_db.add_citation(
        citation_id="test123",
        title="Test Paper",
        authors=["John Doe"],
        year=2024
    )

    # Try to add duplicate
    success = temp_db.add_citation(
        citation_id="test123",
        title="Test Paper 2",
        authors=["Jane Doe"],
        year=2025
    )

    assert success is False


def test_search_citations(temp_db):
    """Test citation search"""
    # Add multiple citations
    temp_db.add_citation(
        citation_id="cit1",
        title="Machine Learning Paper",
        authors=["Alice"],
        year=2024
    )

    temp_db.add_citation(
        citation_id="cit2",
        title="Deep Learning Paper",
        authors=["Bob"],
        year=2023
    )

    # Search by title
    results = temp_db.search_citations(query="Learning")
    assert len(results) == 2

    # Search by year
    results = temp_db.search_citations(year=2024)
    assert len(results) == 1
    assert results[0]["title"] == "Machine Learning Paper"


# =============================================================================
# RAG System Tests
# =============================================================================

def test_text_chunking(rag_system):
    """Test text chunking"""
    text = "This is a test. " * 100  # Long text
    chunks = rag_system._chunk_text(text)

    assert len(chunks) > 1
    assert all(len(chunk) <= rag_system.chunk_size + 100 for chunk in chunks)


@pytest.mark.asyncio
async def test_pdf_processing(rag_system, temp_db):
    """Test PDF processing (mock)"""
    # This would require a real PDF file
    # For now, test the structure
    assert rag_system.db is not None
    assert rag_system.model_name == "all-MiniLM-L6-v2"


# =============================================================================
# LaTeX Writing Tests
# =============================================================================

def test_latex_template_loading():
    """Test LaTeX template exists"""
    latex_agent = LaTeXWritingAgent()
    assert "IEEE" in latex_agent.TEMPLATES
    assert "Springer" in latex_agent.TEMPLATES
    assert "ACM" in latex_agent.TEMPLATES


def test_latex_escape():
    """Test LaTeX special character escaping"""
    latex_agent = LaTeXWritingAgent()

    text = "Test $100 & 50% discount #special"
    escaped = latex_agent._escape_latex(text)

    assert r"\$" in escaped
    assert r"\&" in escaped
    assert r"\%" in escaped
    assert r"\#" in escaped


def test_bibtex_generation():
    """Test BibTeX generation"""
    latex_agent = LaTeXWritingAgent()

    citations = [
        {
            "citation_key": "smith2024",
            "title": "Test Paper",
            "authors": ["John Smith", "Jane Doe"],
            "year": 2024,
            "source": "Test Journal",
            "doi": "10.1234/test"
        }
    ]

    bibtex = latex_agent._generate_bibtex(citations)

    assert "@article{smith2024," in bibtex
    assert "title = {Test Paper}" in bibtex
    assert "author = {John Smith and Jane Doe}" in bibtex
    assert "year = {2024}" in bibtex


@pytest.mark.asyncio
async def test_paper_generation(tmp_path):
    """Test paper generation"""
    latex_agent = LaTeXWritingAgent(workspace_dir=str(tmp_path))

    paper_data = {
        "title": "Test Research Paper",
        "authors": "John Doe",
        "affiliation": "Test University",
        "email": "test@example.com",
        "abstract": "This is a test abstract.",
        "keywords": "test, research, paper",
        "introduction": "This is the introduction.",
        "literature_review": "This is the literature review.",
        "methodology": "This is the methodology.",
        "results": "These are the results.",
        "conclusion": "This is the conclusion.",
        "citations": []
    }

    result = await latex_agent.generate_paper(
        paper_data=paper_data,
        template_type="IEEE",
        output_name="test_paper"
    )

    assert result["success"] is True
    assert "tex_file" in result
    assert Path(result["tex_file"]).exists()


# =============================================================================
# GitHub Analyzer Tests
# =============================================================================

@pytest.mark.asyncio
async def test_github_url_parsing():
    """Test GitHub URL parsing"""
    analyzer = GitHubRepoAnalyzer()

    owner, repo = analyzer._parse_repo_url("https://github.com/microsoft/vscode")
    assert owner == "microsoft"
    assert repo == "vscode"

    owner, repo = analyzer._parse_repo_url("microsoft/vscode")
    assert owner == "microsoft"
    assert repo == "vscode"


# =============================================================================
# Integration Tests
# =============================================================================

@pytest.mark.asyncio
async def test_ordered_reference_workflow(temp_db, rag_system):
    """Test complete ordered reference workflow"""
    # Add citations
    temp_db.add_citation(
        citation_id="ref1",
        title="Paper 1",
        authors=["Author 1"],
        year=2024
    )

    temp_db.add_citation(
        citation_id="ref2",
        title="Paper 2",
        authors=["Author 2"],
        year=2024
    )

    # Create ordered reference agent
    ref_agent = OrderedReferenceAgent(temp_db, rag_system)

    # Add ordered references
    result1 = await ref_agent.add_ordered_reference(
        paper_id="paper123",
        section_name="introduction",
        citation_id="ref1",
        order_index=1,
        context="Background context"
    )

    assert result1["success"] is True

    result2 = await ref_agent.add_ordered_reference(
        paper_id="paper123",
        section_name="introduction",
        citation_id="ref2",
        order_index=2,
        context="Additional context"
    )

    assert result2["success"] is True

    # Get section references
    refs = await ref_agent.get_section_references(
        paper_id="paper123",
        section_name="introduction",
        with_embeddings=False
    )

    assert len(refs) == 2
    assert refs[0]["order_index"] == 1
    assert refs[1]["order_index"] == 2


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
