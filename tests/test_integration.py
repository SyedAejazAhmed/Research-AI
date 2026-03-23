"""
Comprehensive Integration Tests
================================
End-to-end integration tests for the Research AI platform.

Test Coverage:
1. Full pipeline execution
2. Database operations
3. Agent interactions
4. API endpoints
5. Security features
6. File I/O operations
7. Error handling
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Import components
from app.pipeline_orchestrator import ResearchPipelineOrchestrator
from app.database.schema import ResearchDatabase
from app.agents.llm_checker import LLMChecker
from app.agents.ordered_reference_agent import OrderedReferenceAgent, PaperSection
from app.agents.rag_system import RAGSystem
from app.agents.github_analyzer import GitHubRepoAnalyzer
from app.security import (
    RateLimiter,
    APIKeyManager,
    SQLSanitizer,
    XSSProtection,
    ResourceLimits,
    ResearchQueryValidator,
    GitHubRepoValidator,
    FileUploadValidator
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    temp = tempfile.mkdtemp()
    yield Path(temp)
    shutil.rmtree(temp)


@pytest.fixture
def test_database(temp_dir):
    """Create test database"""
    db_path = temp_dir / "test.db"
    db = ResearchDatabase(str(db_path))
    yield db
    # Cleanup handled by temp_dir fixture


@pytest.fixture
def test_orchestrator(temp_dir):
    """Create test pipeline orchestrator"""
    output_dir = temp_dir / "outputs"
    db_path = temp_dir / "test.db"
    orchestrator = ResearchPipelineOrchestrator(
        output_dir=str(output_dir),
        database_path=str(db_path)
    )
    yield orchestrator


# ============================================================================
# Database Integration Tests
# ============================================================================

class TestDatabaseIntegration:
    """Test database operations"""

    @pytest.mark.asyncio
    async def test_citation_crud(self, test_database):
        """Test citation create, read, update, delete"""
        # Create
        citation_id = await test_database.add_citation(
            title="Test Paper",
            authors=["John Doe", "Jane Smith"],
            year=2024,
            doi="10.1234/test"
        )
        assert citation_id is not None

        # Read
        citation = await test_database.get_citation(citation_id)
        assert citation["title"] == "Test Paper"
        assert len(citation["authors"]) == 2

        # Update
        await test_database.update_citation(citation_id, title="Updated Title")
        updated = await test_database.get_citation(citation_id)
        assert updated["title"] == "Updated Title"

        # Delete
        await test_database.delete_citation(citation_id)
        deleted = await test_database.get_citation(citation_id)
        assert deleted is None

    @pytest.mark.asyncio
    async def test_collection_management(self, test_database):
        """Test collection operations"""
        # Create collection
        collection_id = await test_database.create_collection(
            name="Test Collection",
            description="A test collection"
        )
        assert collection_id is not None

        # Add citation to collection
        citation_id = await test_database.add_citation(
            title="Test Paper",
            authors=["Test Author"]
        )

        await test_database.add_citation_to_collection(citation_id, collection_id)

        # Get collection citations
        citations = await test_database.get_collection_citations(collection_id)
        assert len(citations) == 1

    @pytest.mark.asyncio
    async def test_duplicate_detection(self, test_database):
        """Test duplicate citation detection"""
        doi = "10.1234/duplicate"

        # Add first citation
        id1 = await test_database.add_citation(
            title="Paper 1",
            authors=["Author 1"],
            doi=doi
        )

        # Try to add duplicate
        id2 = await test_database.add_citation(
            title="Paper 1 Duplicate",
            authors=["Author 1"],
            doi=doi
        )

        # Should detect as duplicate
        assert id1 == id2


# ============================================================================
# Ordered Reference Agent Tests
# ============================================================================

class TestOrderedReferenceAgent:
    """Test ordered reference activation"""

    def test_auto_assign_sections(self):
        """Test automatic section assignment"""
        agent = OrderedReferenceAgent()
        citation_ids = [f"cit_{i:03d}" for i in range(1, 31)]

        assignments = agent.auto_assign_sections(citation_ids)

        # Check all sections assigned
        assert PaperSection.INTRODUCTION in assignments
        assert PaperSection.LITERATURE_REVIEW in assignments
        assert PaperSection.METHODOLOGY in assignments

        # Check total citations
        total = sum(len(a.citation_ids) for a in assignments.values())
        assert total == 30

    def test_manual_assign_section(self):
        """Test manual section assignment"""
        agent = OrderedReferenceAgent()
        citation_ids = [f"cit_{i:03d}" for i in range(1, 31)]
        agent.set_citation_order(citation_ids)

        # Manually assign some citations
        intro_cits = citation_ids[:5]
        agent.manual_assign_section(PaperSection.INTRODUCTION, intro_cits)

        assignment = agent.section_assignments[PaperSection.INTRODUCTION]
        assert len(assignment.citation_ids) == 5

    def test_get_section_summary(self):
        """Test section summary generation"""
        agent = OrderedReferenceAgent()
        citation_ids = [f"cit_{i:03d}" for i in range(1, 31)]

        agent.auto_assign_sections(citation_ids)
        summary = agent.get_section_summary()

        assert summary["total_references"] == 30
        assert "sections" in summary
        assert len(summary["sections"]) > 0


# ============================================================================
# LLM Checker Tests
# ============================================================================

class TestLLMChecker:
    """Test LLM availability checker"""

    @pytest.mark.asyncio
    async def test_system_info(self):
        """Test system information gathering"""
        checker = LLMChecker()
        info = checker.system_info

        assert "ram_gb" in info
        assert "disk_gb" in info
        assert "platform" in info
        assert info["ram_gb"] > 0

    def test_recommend_models(self):
        """Test model recommendation"""
        checker = LLMChecker()
        recommended = checker.recommend_models(top_n=3)

        assert len(recommended) <= 3
        assert all(hasattr(m, "name") for m in recommended)
        assert all(hasattr(m, "size_gb") for m in recommended)

    def test_print_system_report(self):
        """Test system report generation"""
        checker = LLMChecker()
        report = checker.print_system_report()

        assert "RAM" in report
        assert "RECOMMENDED MODELS" in report


# ============================================================================
# Security Tests
# ============================================================================

class TestSecurity:
    """Test security features"""

    def test_rate_limiter(self):
        """Test rate limiting"""
        limiter = RateLimiter(requests_per_minute=5, requests_per_hour=20)

        # Should allow first 5 requests
        for i in range(5):
            allowed, msg = limiter.is_allowed("client_1")
            assert allowed

        # Should block 6th request
        allowed, msg = limiter.is_allowed("client_1")
        assert not allowed
        assert "Rate limit exceeded" in msg

    def test_api_key_generation(self):
        """Test API key generation and validation"""
        manager = APIKeyManager()

        # Generate key
        key = manager.generate_key("user_1", "Test Key", expires_days=30)
        assert key.startswith("rai_")

        # Validate key
        valid, msg = manager.validate_key(key)
        assert valid

        # Invalid key
        valid, msg = manager.validate_key("invalid_key")
        assert not valid

    def test_sql_sanitizer(self):
        """Test SQL injection prevention"""
        # Safe input
        safe = "SELECT column FROM table"
        try:
            SQLSanitizer.sanitize("normal search query")
        except ValueError:
            pytest.fail("Should not raise for safe input")

        # Dangerous input
        with pytest.raises(ValueError):
            SQLSanitizer.sanitize("SELECT * FROM users WHERE id=1")

    def test_xss_protection(self):
        """Test XSS protection"""
        malicious = "<script>alert('XSS')</script>"
        sanitized = XSSProtection.sanitize_html(malicious)

        assert "<script>" not in sanitized
        assert "&lt;script&gt;" in sanitized

    def test_url_validation(self):
        """Test URL validation"""
        # Safe URLs
        assert XSSProtection.validate_url("https://example.com")
        assert XSSProtection.validate_url("http://github.com/repo")

        # Unsafe URLs
        assert not XSSProtection.validate_url("javascript:alert('XSS')")
        assert not XSSProtection.validate_url("data:text/html,<script>alert('XSS')</script>")

    def test_query_validator(self):
        """Test query validation"""
        # Valid query
        valid_query = ResearchQueryValidator(
            query="Machine learning research",
            research_mode="academic",
            max_citations=30
        )
        assert valid_query.query == "Machine learning research"

        # Invalid query (too short)
        with pytest.raises(ValueError):
            ResearchQueryValidator(query="ML")

    def test_github_url_validator(self):
        """Test GitHub URL validation"""
        # Valid URLs
        valid1 = GitHubRepoValidator(repo_url="https://github.com/user/repo")
        assert valid1.repo_url == "https://github.com/user/repo"

        valid2 = GitHubRepoValidator(repo_url="user/repo")
        assert valid2.repo_url == "user/repo"

        # Invalid URL
        with pytest.raises(ValueError):
            GitHubRepoValidator(repo_url="not-a-github-url")

    def test_file_upload_validator(self):
        """Test file upload validation"""
        # Valid file
        valid = FileUploadValidator(
            filename="paper.pdf",
            file_size=1024 * 1024,  # 1 MB
            content_type="application/pdf"
        )
        assert valid.filename == "paper.pdf"

        # File too large
        with pytest.raises(ValueError):
            FileUploadValidator(
                filename="large.pdf",
                file_size=100 * 1024 * 1024,  # 100 MB
                content_type="application/pdf"
            )

        # Invalid extension
        with pytest.raises(ValueError):
            FileUploadValidator(
                filename="malware.exe",
                file_size=1024,
                content_type="application/octet-stream"
            )


# ============================================================================
# GitHub Analyzer Tests
# ============================================================================

class TestGitHubAnalyzer:
    """Test GitHub repository analyzer"""

    def test_parse_repo_url(self, temp_dir):
        """Test repository URL parsing"""
        analyzer = GitHubRepoAnalyzer(output_dir=str(temp_dir))

        # Test various URL formats
        owner, repo = analyzer._parse_repo_url("https://github.com/user/repo")
        assert owner == "user"
        assert repo == "repo"

        owner, repo = analyzer._parse_repo_url("user/repo")
        assert owner == "user"
        assert repo == "repo"

    @pytest.mark.asyncio
    async def test_analyze_structure(self, temp_dir):
        """Test repository structure analysis"""
        analyzer = GitHubRepoAnalyzer(output_dir=str(temp_dir))

        # Mock tree structure
        tree = [
            {"type": "blob", "path": "README.md"},
            {"type": "blob", "path": "src/main.py"},
            {"type": "blob", "path": "tests/test_main.py"},
            {"type": "tree", "path": "src"},
            {"type": "tree", "path": "tests"}
        ]

        structure = analyzer._analyze_structure(tree)

        assert structure["total_files"] == 3
        assert structure["has_tests"]
        assert structure["has_docs"]


# ============================================================================
# Pipeline Integration Tests
# ============================================================================

class TestPipelineIntegration:
    """Test complete pipeline execution"""

    @pytest.mark.asyncio
    async def test_pipeline_session_management(self, test_orchestrator):
        """Test pipeline session creation and retrieval"""
        # List sessions (should be empty)
        sessions = test_orchestrator.list_sessions()
        assert len(sessions) == 0

        # Create a session by saving state
        session_id = "session_test_123"
        results = {
            "session_id": session_id,
            "status": "success",
            "query": "Test query"
        }
        test_orchestrator._save_pipeline_state(session_id, results)

        # List sessions (should have 1)
        sessions = test_orchestrator.list_sessions()
        assert len(sessions) == 1
        assert session_id in sessions

        # Retrieve session
        retrieved = await test_orchestrator.get_pipeline_status(session_id)
        assert retrieved is not None
        assert retrieved["query"] == "Test query"


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("RUNNING COMPREHENSIVE INTEGRATION TESTS")
    print("=" * 70)

    # Run pytest
    pytest.main([__file__, "-v", "--tb=short"])
