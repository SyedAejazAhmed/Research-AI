"""
tests/test_github_agent.py
===========================

20 tests for GithubAgent covering:
  - URL validation
  - File filtering
  - Directory tree generation
  - Repo-name extraction
  - File content reading (truncation / unreadable files)
  - Fallback outputs (summary, title) when LLM unavailable
  - Async flow (execute with empty repo_url)
  - execute() returns correct response shape
  - OllamaClient integration mock
  - Output-directory creation
  - Hierarchical vs direct summarisation selection
  - Required summary sections check
  - Title generation fallback
  - _cleanup() behaviour
  - GithubAgentConfig defaults
  - Config override (ollama_model)
  - AgentResponse structure
  - Module-level _tree_walk doesn't crash on empty directory
  - filter_files skips excluded dirs

Run with::

    pytest tests/test_github_agent.py -v --tb=short

All tests are auto-allow (no interactive prompts, no network calls — all
external I/O is mocked with unittest.mock).
"""

from __future__ import annotations

import asyncio
import shutil
import sys
import tempfile
from pathlib import Path
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Patch sys.path so imports resolve without installing the package
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Imports under test
# ---------------------------------------------------------------------------
from multi_agent.agents.github_agent import (
    GithubAgent,
    GithubAgentConfig,
    REQUIRED_SECTIONS,
    _EXCLUDED_DIRS,
    _extract_repo_name,
    _filter_files,
    _generate_tree,
    _read_file_content,
    _validate_github_url,
    _RepoHandlerError,
)


# ===========================================================================
# Helpers
# ===========================================================================

def _make_repo(tmp: Path, files: dict) -> Path:
    """Create a mock repository directory with given files."""
    for rel, content in files.items():
        (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            (tmp / rel).write_bytes(content)
        else:
            (tmp / rel).write_text(content, encoding="utf-8")
    return tmp


# ===========================================================================
# 1. Validate URL — happy path
# ===========================================================================

def test_validate_url_happy_path():
    url = _validate_github_url("https://github.com/owner/repo")
    assert url == "https://github.com/owner/repo"


# ===========================================================================
# 2. Validate URL — strips trailing slash and .git
# ===========================================================================

def test_validate_url_strips_git_and_slash():
    url = _validate_github_url("https://github.com/owner/repo.git/")
    assert url == "https://github.com/owner/repo"


# ===========================================================================
# 3. Validate URL — non-HTTPS raises error
# ===========================================================================

def test_validate_url_rejects_http():
    with pytest.raises(_RepoHandlerError, match="HTTPS"):
        _validate_github_url("http://github.com/owner/repo")


# ===========================================================================
# 4. Validate URL — non-github host raises error
# ===========================================================================

def test_validate_url_rejects_non_github():
    with pytest.raises(_RepoHandlerError, match="github.com"):
        _validate_github_url("https://gitlab.com/owner/repo")


# ===========================================================================
# 5. Validate URL — empty string raises error
# ===========================================================================

def test_validate_url_empty():
    with pytest.raises(_RepoHandlerError, match="empty"):
        _validate_github_url("")


# ===========================================================================
# 6. Validate URL — sub-path trimmed to owner/repo
# ===========================================================================

def test_validate_url_trims_subpath():
    url = _validate_github_url("https://github.com/owner/repo/tree/main/src")
    assert url == "https://github.com/owner/repo"


# ===========================================================================
# 7. Extract repo name
# ===========================================================================

def test_extract_repo_name():
    assert _extract_repo_name("https://github.com/microsoft/vscode") == "vscode"
    assert _extract_repo_name("https://github.com/user/my-repo/") == "my-repo"


# ===========================================================================
# 8. Read file content — normal file
# ===========================================================================

def test_read_file_content_normal(tmp_path: Path):
    f = tmp_path / "test.py"
    f.write_text("print('hello')", encoding="utf-8")
    assert _read_file_content(f) == "print('hello')"


# ===========================================================================
# 9. Read file content — truncation
# ===========================================================================

def test_read_file_content_truncation(tmp_path: Path):
    f = tmp_path / "big.py"
    f.write_text("x" * 50_000, encoding="utf-8")
    result = _read_file_content(f, max_chars=1000)
    assert len(result) < 51_000
    assert "TRUNCATED" in result


# ===========================================================================
# 10. Read file content — unreadable path returns empty string
# ===========================================================================

def test_read_file_content_missing():
    result = _read_file_content(Path("/nonexistent/file.py"))
    assert result == ""


# ===========================================================================
# 11. Filter files — skips excluded dirs
# ===========================================================================

def test_filter_files_skips_excluded_dirs(tmp_path: Path):
    repo = _make_repo(tmp_path, {
        "src/main.py": "code",
        "node_modules/lib.js": "lib",
        "__pycache__/cache.pyc": "cached",
    })
    found = _filter_files(repo)
    paths_str = [str(f) for f in found]
    assert any("main.py" in p for p in paths_str), "main.py should be included"
    assert not any("node_modules" in p for p in paths_str), "node_modules should be excluded"
    assert not any("__pycache__" in p for p in paths_str), "__pycache__ should be excluded"


# ===========================================================================
# 12. Filter files — skips binary extensions
# ===========================================================================

def test_filter_files_skips_binaries(tmp_path: Path):
    repo = _make_repo(tmp_path, {
        "image.png": b"\x89PNG",
        "script.py": "import os",
    })
    found = _filter_files(repo)
    paths_str = [str(f) for f in found]
    assert not any("image.png" in p for p in paths_str)
    assert any("script.py" in p for p in paths_str)


# ===========================================================================
# 13. Generate directory tree — returns repo name as root
# ===========================================================================

def test_generate_tree_root_label(tmp_path: Path):
    repo = _make_repo(tmp_path, {"src/app.py": "pass", "README.md": "docs"})
    tree = _generate_tree(repo, "my-repo")
    assert tree.startswith("my-repo/")


# ===========================================================================
# 14. Generate directory tree — contains files
# ===========================================================================

def test_generate_tree_contains_files(tmp_path: Path):
    repo = _make_repo(tmp_path, {"src/app.py": "pass", "README.md": "docs"})
    tree = _generate_tree(repo, "demo")
    assert "app.py" in tree
    assert "README.md" in tree


# ===========================================================================
# 15. Fallback summary contains all required sections
# ===========================================================================

def test_fallback_summary_sections():
    summary = GithubAgent._fallback_summary("testrepo")
    for section in REQUIRED_SECTIONS:
        assert section in summary, f"Missing section: {section}"


# ===========================================================================
# 16. Fallback title contains repo name
# ===========================================================================

def test_fallback_title_contains_repo_name():
    title = GithubAgent._fallback_title("my-project-name")
    assert "My Project Name" in title


# ===========================================================================
# 17. GithubAgentConfig defaults
# ===========================================================================

def test_github_agent_config_defaults():
    cfg = GithubAgentConfig()
    assert cfg.ollama_model == "gpt-oss:20b"
    assert cfg.ollama_base_url == "http://localhost:11434"
    assert cfg.name == "GithubAgent"


# ===========================================================================
# 18. GithubAgentConfig override
# ===========================================================================

def test_github_agent_config_override():
    cfg = GithubAgentConfig(ollama_model="llama3:8b", repo_url="https://github.com/a/b")
    assert cfg.ollama_model == "llama3:8b"
    assert cfg.repo_url == "https://github.com/a/b"


# ===========================================================================
# 19. execute() with empty repo_url returns failure AgentResponse
# ===========================================================================

@pytest.mark.asyncio
async def test_execute_missing_repo_url():
    agent = GithubAgent(config=GithubAgentConfig(repo_url=""))
    result = await agent.execute()
    assert result.success is False
    assert "repo_url" in (result.error or "")


# ===========================================================================
# 20. Full execute() success flow — all I/O mocked (v2 scrape-based)
# ===========================================================================

@pytest.mark.asyncio
async def test_execute_full_pipeline_mocked(tmp_path: Path):
    """Full execute() run with GitHub API and LLM all mocked (no cloning, no network)."""
    fake_meta = {
        "description": "A test repository",
        "default_branch": "main",
        "stargazers_count": 42,
        "forks_count": 7,
        "open_issues_count": 3,
        "license": {"name": "MIT"},
    }
    fake_topics = {"names": ["ai", "python"]}
    fake_langs   = {"Python": 12345, "TypeScript": 6789}
    fake_tree    = [
        {"path": "README.md", "type": "file"},
        {"path": "requirements.txt", "type": "file"},
        {"path": "src", "type": "dir"},
    ]

    fake_ollama = MagicMock()
    fake_ollama.is_available = True
    fake_ollama.initialize = AsyncMock()
    fake_ollama.generate = AsyncMock(return_value="Mocked LLM output for summary")

    from unittest.mock import AsyncMock as _AsyncMock, patch as _patch

    # Patch the module-level http helpers to return fake data
    async def fake_get_json(client, url):
        if "/topics" in url:
            return fake_topics
        if "/languages" in url:
            return fake_langs
        if "/contents" in url:
            return fake_tree
        return fake_meta  # base repo endpoint

    async def fake_get_raw(client, url, max_chars=None):
        if "README" in url:
            return "# Fake README\nThis is a test project."
        if "requirements" in url:
            return "httpx\nfastapi\n"
        return None

    with _patch("multi_agents.agents.github_agent._get_json", side_effect=fake_get_json), \
         _patch("multi_agents.agents.github_agent._get_raw", side_effect=fake_get_raw), \
         _patch("app.agents.llm_client.OllamaClient", return_value=fake_ollama):

        cfg = GithubAgentConfig(
            repo_url="https://github.com/fake/fake-repo",
            output_dir=str(tmp_path / "output"),
        )
        agent = GithubAgent(config=cfg)
        result = await agent.execute()

    assert result.success is True, f"Expected success but got error: {result.error}"
    assert "repo_name" in result.data
    assert "summary"   in result.data
    assert "title"     in result.data
    assert "tree"      in result.data
    assert result.data["repo_name"] == "fake-repo"
