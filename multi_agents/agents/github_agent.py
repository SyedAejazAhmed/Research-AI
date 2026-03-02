"""
GitHub Repository Intelligence Agent  (v2 — scrape, no clone)
==============================================================

Scrapes a public GitHub repository's concepts WITHOUT git-cloning:
  1. GitHub REST API  →  repo metadata (description, topics, language, stars)
  2. GitHub Contents API  →  root-level file tree
  3. Raw content  →  README.md + up to 6 key concept files
  4. Single LLM call  →  structured technical summary
  5. Single LLM call  →  academic title

Total runtime: typically 5–20 s (vs 300 s with cloning).
No git required.  No temp disk space consumed.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import httpx

from .base import AgentConfig, AgentResponse, AgentStatus, BaseAgent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_FILE_CHARS: int   = 3_000    # trimmed: less context, faster generation
_MAX_README_CHARS: int = 5_000    # readme is most useful, keep more of it
_MAX_FILES_TO_FETCH: int = 4      # 4 concept files max (fewer = faster)

_GITHUB_API = "https://api.github.com"
_RAW_BASE   = "https://raw.githubusercontent.com"
_HTTP_TIMEOUT = httpx.Timeout(25.0)

REQUIRED_SECTIONS: List[str] = [
    "# Project Overview",
    "# Problem Statement",
    "# Objectives",
    "# System Architecture",
    "# Core Components",
    "# Technologies Used",
    "# Data Flow / Execution Flow",
    "# Key Algorithms / Models",
    "# Configuration & Dependencies",
    "# Limitations",
    "# Future Scope",
]


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass
class GithubAgentConfig(AgentConfig):
    name: str = "GithubAgent"
    description: str = "GitHub Repository Intelligence Agent (scrape mode)"
    repo_url: str = ""
    existing_title: Optional[str] = None
    output_dir: str = "./outputs/GitHub"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gpt-oss:20b"
    github_token: Optional[str] = None
    summary_tokens: int = 500      # ~55s at 9 tok/s — fits in 180s budget
    title_tokens: int = 60           # ~7s
    timeout: int = 180    # scrape ~2s + summary ~55s + title ~7s + margin
    # legacy compat fields (ignored in v2)
    file_summary_tokens: int = 300
    module_summary_tokens: int = 400
    full_summary_tokens: int = 800


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------

class _AgentError(Exception):
    pass

# kept for backwards compat with tests
class _RepoHandlerError(_AgentError):
    pass


def _parse_github_url(url: str) -> Tuple[str, str]:
    url = url.strip().rstrip("/")
    if not url:
        raise _RepoHandlerError("Repository URL must not be empty.")
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise _RepoHandlerError(f"URL must use HTTPS. Got: '{parsed.scheme or 'none'}'.")
    if parsed.hostname != "github.com":
        raise _RepoHandlerError(f"URL must point to github.com. Got: '{parsed.hostname}'.")
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(parts) < 2:
        raise _RepoHandlerError(
            "URL must include owner AND repo name (e.g. https://github.com/owner/repo)."
        )
    owner, repo = parts[0], parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    return owner, repo


def _validate_github_url(url: str) -> str:
    owner, repo = _parse_github_url(url)
    return f"https://github.com/{owner}/{repo}"


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _api_headers(token: Optional[str]) -> Dict[str, str]:
    h = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Yukti-Research-AI/2.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


async def _get_json(client: httpx.AsyncClient, url: str) -> Optional[Any]:
    try:
        r = await client.get(url)
        if r.status_code == 200:
            return r.json()
        logger.debug("API %s → %d", url, r.status_code)
    except Exception as exc:
        logger.debug("HTTP error %s: %s", url, exc)
    return None


async def _get_raw(client: httpx.AsyncClient, url: str, max_chars: int = _MAX_FILE_CHARS) -> Optional[str]:
    try:
        r = await client.get(url)
        if r.status_code == 200:
            text = r.text
            if len(text) > max_chars:
                text = text[:max_chars] + "\n\n... [TRUNCATED]"
            return text
    except Exception as exc:
        logger.debug("Raw fetch %s: %s", url, exc)
    return None


# ---------------------------------------------------------------------------
# GithubAgent
# ---------------------------------------------------------------------------

class GithubAgent(BaseAgent):
    """
    Scrape-first GitHub agent. No cloning. Completes in ~10-25 seconds.

    Pipeline:
    1. Validate URL  →  extract owner/repo
    2. Parallel fetch: repo meta, topics, languages, root tree
    3. Parallel fetch: README + up to 6 concept files
    4. One LLM call → structured summary
    5. One LLM call → academic title
    6. Persist outputs
    """

    def __init__(
        self,
        config: Optional[GithubAgentConfig] = None,
        websocket=None,
        stream_output=None,
        headers=None,
    ) -> None:
        cfg = config or GithubAgentConfig()
        super().__init__(websocket=websocket, stream_output=stream_output,
                         headers=headers, config=cfg)
        self._cfg: GithubAgentConfig = cfg
        self._ollama: Optional[Any] = None

    # ── BaseAgent interface ────────────────────────────────────────────────

    async def execute(self, *args, **kwargs) -> AgentResponse:  # type: ignore[override]
        start = time.monotonic()
        cfg = self._cfg

        if not cfg.repo_url:
            return AgentResponse(success=False, error="repo_url is required", agent_name=cfg.name)

        # Init Ollama
        try:
            from app.agents.llm_client import OllamaClient
            self._ollama = OllamaClient(base_url=cfg.ollama_base_url, model=cfg.ollama_model)
            await self._ollama.initialize()
        except Exception as exc:
            logger.warning("OllamaClient init failed: %s — LLM disabled.", exc)
            self._ollama = None

        # Parse URL
        try:
            owner, repo_name = _parse_github_url(cfg.repo_url)
        except _AgentError as exc:
            return AgentResponse(success=False, error=str(exc), agent_name=cfg.name)

        http_hdrs = _api_headers(cfg.github_token)

        async with httpx.AsyncClient(headers=http_hdrs, timeout=_HTTP_TIMEOUT, follow_redirects=True) as http:
            try:
                # ── Phase 1: parallel API calls ────────────────────────
                await self._progress(f"Fetching {owner}/{repo_name} from GitHub …")
                meta, topics_data, lang_data, root_tree = await asyncio.gather(
                    _get_json(http, f"{_GITHUB_API}/repos/{owner}/{repo_name}"),
                    _get_json(http, f"{_GITHUB_API}/repos/{owner}/{repo_name}/topics"),
                    _get_json(http, f"{_GITHUB_API}/repos/{owner}/{repo_name}/languages"),
                    _get_json(http, f"{_GITHUB_API}/repos/{owner}/{repo_name}/contents"),
                )

                if meta is None:
                    return AgentResponse(
                        success=False,
                        error=(
                            f"Could not reach GitHub API for {owner}/{repo_name}. "
                            "Ensure the repository is public and the URL is correct."
                        ),
                        agent_name=cfg.name,
                    )

                description    = meta.get("description") or ""
                default_branch = meta.get("default_branch", "main")
                stars          = meta.get("stargazers_count", 0)
                forks          = meta.get("forks_count", 0)
                open_issues    = meta.get("open_issues_count", 0)
                license_name   = (meta.get("license") or {}).get("name", "Not specified")
                topics         = (topics_data or {}).get("names", [])
                languages      = list((lang_data or {}).keys())

                root_files: List[str] = []
                tree_lines: List[str] = [f"{repo_name}/"]
                if root_tree and isinstance(root_tree, list):
                    for item in root_tree:
                        if isinstance(item, dict):
                            root_files.append(item["path"])
                            icon = "📁 " if item.get("type") == "dir" else "📄 "
                            tree_lines.append(f"  {icon}{item['path']}")

                tree_str = "\n".join(tree_lines[:80])

                # ── Phase 2: README + concept files ───────────────────
                await self._progress("Fetching README and concept files …")

                # README (try common variants)
                readme_content: Optional[str] = None
                root_lower = {f.lower(): f for f in root_files}
                for candidate in ["README.md", "readme.md", "README.rst", "README.txt"]:
                    actual = root_lower.get(candidate.lower())
                    if actual:
                        url = f"{_RAW_BASE}/{owner}/{repo_name}/{default_branch}/{actual}"
                        readme_content = await _get_raw(http, url, max_chars=_MAX_README_CHARS)
                        if readme_content:
                            break

                # Concept files
                concept_candidates = [
                    f for f in [
                        "requirements.txt", "requirements-dev.txt",
                        "pyproject.toml", "setup.py", "setup.cfg",
                        "package.json",
                        "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
                        "ARCHITECTURE.md", "DESIGN.md",
                    ]
                    if f in root_files
                ]

                raw_tasks = [
                    _get_raw(http, f"{_RAW_BASE}/{owner}/{repo_name}/{default_branch}/{f}")
                    for f in concept_candidates[:_MAX_FILES_TO_FETCH]
                ]
                fetched = await asyncio.gather(*raw_tasks)

                concept_blocks: List[str] = []
                for fname, content in zip(concept_candidates, fetched):
                    if content:
                        concept_blocks.append(f"### `{fname}`\n```\n{content}\n```")

            except Exception as exc:
                logger.error("GitHub scrape error: %s", exc, exc_info=True)
                return AgentResponse(
                    success=False,
                    error=f"Failed to fetch repository data: {exc}",
                    agent_name=cfg.name,
                    execution_time=time.monotonic() - start,
                )

        # ── Phase 3: LLM synthesis ────────────────────────────────────
        await self._progress("Synthesising concepts with AI …")

        sections_list = "\n".join(REQUIRED_SECTIONS)
        meta_block = (
            f"**Repository:** [{owner}/{repo_name}]({cfg.repo_url})\n"
            f"**Description:** {description or 'Not provided'}\n"
            f"**Languages:** {', '.join(languages[:6]) or 'Unknown'}\n"
            f"**Topics:** {', '.join(topics) or 'None listed'}\n"
            f"**Stars:** {stars:,}  |  **License:** {license_name}\n"
        )
        # Trim aggressively — fewer input chars = faster generation
        readme_excerpt = (readme_content or "")[:4000]
        readme_block = f"\n### README (excerpt)\n{readme_excerpt}" if readme_excerpt else "\n### README\n*No README found.*"
        concept_text  = "\n\n".join(concept_blocks) if concept_blocks else "*No dependency/config files detected.*"

        # Cap combined context to keep prompt short (~7K chars total)
        combined_context = f"{readme_block}\n\n{concept_text}"
        if len(combined_context) > 5500:
            combined_context = combined_context[:5500] + "\n... [TRUNCATED]"

        prompt = (
            "You are a technical documentation expert. "
            "Analyse this GitHub repository and write a structured Markdown summary.\n\n"
            f"{meta_block}\n"
            f"**Root directory:**\n```\n{tree_str[:1000]}\n```\n"
            f"{combined_context}\n\n"
            "---\n"
            "Write a concise technical summary using EXACTLY these headings "
            "(2-3 sentences per section):\n\n"
            f"{sections_list}\n\n"
            'Rules: Use only facts present above. '
            'Write "Not defined in repository." if a section has no data. '
            'Do NOT invent metrics or datasets.'
        )

        summary = await self._llm(prompt, max_tokens=cfg.summary_tokens, label="summary")
        if not summary or summary.startswith("["):
            summary = self._fallback_summary(repo_name, description, topics, languages)

        # ── Phase 4: Title ────────────────────────────────────────────
        await self._progress("Generating academic title …")
        title = await self._generate_title(summary, repo_name, cfg.existing_title)

        # ── Phase 5: Persist ──────────────────────────────────────────
        await self._progress("Saving outputs …")
        output_dir = Path(cfg.output_dir)
        self._ensure_output_dirs(output_dir)
        (output_dir / "summary" / "summary.md").write_text(summary, encoding="utf-8")
        (output_dir / "title"   / "title.txt" ).write_text(title,   encoding="utf-8")

        elapsed = time.monotonic() - start
        await self._progress(f"Complete in {elapsed:.1f}s ✓")

        return AgentResponse(
            success=True,
            data={
                "repo_name":       repo_name,
                "repo_url":        cfg.repo_url,
                "description":     description,
                "languages":       languages,
                "topics":          topics,
                "stars":           stars,
                "tree":            tree_str,
                "summary":         summary,
                "title":           title,
                "output_dir":      str(output_dir.resolve()),
                "files_analysed":  len(concept_blocks),
                "elapsed_seconds": round(elapsed, 2),
            },
            agent_name=cfg.name,
            execution_time=elapsed,
        )

    # ── LLM wrapper ───────────────────────────────────────────────────────

    async def _llm(self, prompt: str, max_tokens: int = 300, label: str = "LLM") -> str:
        if self._ollama and self._ollama.is_available:
            try:
                return await self._ollama.generate(prompt, max_tokens=max_tokens)
            except Exception as exc:
                logger.error("LLM error [%s]: %s", label, exc)
                return f"[LLM generation failed: {exc}]"
        return "[Ollama not available]"

    # ── Title generation ──────────────────────────────────────────────────

    async def _generate_title(self, summary: str, repo_name: str, existing_title: Optional[str] = None) -> str:
        context = summary[:1200]   # short context is enough for a title
        if existing_title:
            prompt = (
                f"Improve this research paper title for academic clarity.\n"
                f"Original: {existing_title}\n\nContext:\n{context}\n\n"
                "Rules: Keep core meaning. 10–18 words. Return ONLY the title."
            )
        else:
            prompt = (
                f"Generate a research-paper title for this GitHub repository.\n"
                f"Repository name: {repo_name}\n\nContext:\n{context}\n\n"
                "Rules: Pattern = [Method/System] for [Problem] Using [Technology]. "
                "10–18 words. No buzzwords. Return ONLY the title — no explanation."
            )
        title = await self._llm(prompt, max_tokens=self._cfg.title_tokens, label="title")
        title = title.strip().strip('"\'').strip()
        return title if title and not title.startswith("[") else self._fallback_title(repo_name)

    # ── Fallbacks ─────────────────────────────────────────────────────────

    @staticmethod
    def _fallback_summary(repo_name: str, description: str = "",
                          topics: Optional[List[str]] = None,
                          languages: Optional[List[str]] = None) -> str:
        header = f"# Summary for {repo_name}\n\n"
        if description:
            header += f"**Description:** {description}\n\n"
        if languages:
            header += f"**Languages:** {', '.join(languages)}\n\n"
        if topics:
            header += f"**Topics:** {', '.join(topics)}\n\n"
        body = "\n\n".join(f"{s}\nNot explicitly defined in repository." for s in REQUIRED_SECTIONS)
        return header + body

    @staticmethod
    def _fallback_title(repo_name: str) -> str:
        clean = repo_name.replace("-", " ").replace("_", " ").title()
        return f"Technical Architecture and Implementation Analysis of the {clean} Software Repository"

    # ── Utilities ─────────────────────────────────────────────────────────

    async def _progress(self, message: str) -> None:
        logger.info("[GithubAgent] %s", message)
        await self.log_output(message, log_type="logs", event="github_agent")

    @staticmethod
    def _ensure_output_dirs(base: Path) -> None:
        for sub in ("summary", "title"):
            (base / sub).mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Backwards-compatibility shims
# (kept so existing tests and external imports don't break)
# ---------------------------------------------------------------------------

# v1 constants that tests reference
from typing import FrozenSet as _FrozenSet

_EXCLUDED_DIRS: _FrozenSet[str] = frozenset({
    ".git", "node_modules", "venv", ".venv", "env", ".env",
    "__pycache__", "build", "dist", ".tox", ".mypy_cache",
    ".pytest_cache", ".ruff_cache",
})

_INCLUDED_EXTENSIONS: _FrozenSet[str] = frozenset({
    ".py", ".js", ".ts", ".jsx", ".tsx", ".md", ".txt",
    ".json", ".yaml", ".yml", ".toml", ".cfg",
})

_BINARY_EXTENSIONS: _FrozenSet[str] = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",
    ".mp3", ".mp4", ".avi", ".mov", ".wav",
    ".zip", ".tar", ".gz", ".bz2", ".rar", ".7z",
    ".exe", ".dll", ".so", ".dylib", ".pyc", ".pyo",
})


def _extract_repo_name(url: str) -> str:
    """Return repo name from a GitHub URL. Compat shim for v1 tests."""
    return url.rstrip("/").rstrip(".git").split("/")[-1].rstrip(".git")


def _read_file_content(file_path: Path, max_chars: int = 40_000) -> str:
    """Read file content with truncation. Compat shim for v1 tests."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        if len(content) > max_chars:
            content = content[:max_chars] + "\n\n... [TRUNCATED — file exceeds size limit]"
        return content
    except Exception:
        return ""


def _filter_files(repo_path: Path) -> List[Path]:
    """Return relevant source/config files under repo_path. Compat shim for v1 tests."""
    result: List[Path] = []
    _MAX_FILE_SIZE = 1_048_576
    for entry in repo_path.rglob("*"):
        if not entry.is_file():
            continue
        if any(part in _EXCLUDED_DIRS for part in entry.relative_to(repo_path).parts):
            continue
        if entry.suffix.lower() in _BINARY_EXTENSIONS:
            continue
        name_lower = entry.name.lower()
        if name_lower.endswith(".min.js") or name_lower.endswith(".min.css"):
            continue
        try:
            if entry.stat().st_size > _MAX_FILE_SIZE:
                continue
        except OSError:
            continue
        if entry.suffix.lower() in _INCLUDED_EXTENSIONS:
            result.append(entry)
    return result


def _generate_tree(repo_path: Path, repo_name: str) -> str:
    """Generate directory tree string. Compat shim for v1 tests."""
    lines: List[str] = [f"{repo_name}/"]

    def _walk(directory: Path, prefix: str) -> None:
        try:
            entries = sorted(directory.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
        except PermissionError:
            return
        filtered = [e for e in entries if not (e.is_dir() and e.name in _EXCLUDED_DIRS)]
        for idx, entry in enumerate(filtered):
            is_last = idx == len(filtered) - 1
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{entry.name}")
            if entry.is_dir():
                ext = "    " if is_last else "│   "
                _walk(entry, prefix + ext)

    _walk(repo_path, "")
    return "\n".join(lines)
