"""
Yukti Research AI - FastAPI Server
====================================
Main server with REST API + WebSocket for real-time research progress.
"""

import asyncio
import json
import logging
import os
import re
import shutil
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, File, Form, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.orchestrator import ResearchOrchestrator
from app.agents.llm_client import OllamaClient
from app.utils.references import DEFAULT_LIMIT, DEFAULT_STYLE, generate_references, pyzotero_capabilities
from .repo_analysis_service import (
    RepoAnalysisError,
    analyze_github_repository,
    analyze_local_repository,
    analyze_repo_path,
)
from .writing_service import WritingService

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# ============================================================================
# App Initialization
# ============================================================================

app = FastAPI(
    title="Yukti Research AI",
    description="Autonomous AI System for Logical & Verified Academic Research",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static Files Configuration
BASE_DIR = Path(__file__).resolve().parent.parent  # project root
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
STATIC_DIR = FRONTEND_DIST if FRONTEND_DIST.exists() else BASE_DIR / "app" / "static"
OUTPUT_DIR = BASE_DIR / "outputs"
SESSIONS_DIR = BASE_DIR / "sessions"

# Ensure directories exist
STATIC_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Mount /assets so Vite-built bundles (e.g. /assets/index-xxx.js) are served correctly
_assets_dir = STATIC_DIR / "assets"
if _assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="assets")

# Initialize orchestrator
orchestrator = ResearchOrchestrator(output_dir=str(OUTPUT_DIR))

# Initialize writing service
writing_service = WritingService(output_dir=str(OUTPUT_DIR))

# WebSocket connections
active_connections: Dict[str, WebSocket] = {}

# Chat sessions (in-memory)
chat_sessions: Dict[str, Dict] = {}


# ============================================================================
# Models
# ============================================================================

class ResearchRequest(BaseModel):
    query: str
    citation_style: str = "IEEE"


class ReferencesRequest(BaseModel):
    query: str
    limit: int = DEFAULT_LIMIT
    style: str = DEFAULT_STYLE
    excluded_titles: List[str] = Field(default_factory=list)


class ReferencesFormatsResponse(BaseModel):
    available: bool
    formats: List[str]
    style_note: str

class ChatMessage(BaseModel):
    session_id: str
    message: str

class ExportRequest(BaseModel):
    session_id: str
    format: str = "markdown"  # markdown, html

class WriteRequest(BaseModel):
    session_id: str
    compile_pdf: bool = True
    template: str = "ieee"   # allowed: ieee
    author: str = ""
    use_multi_agent_writer: bool = False
    allow_fallback_pdf: bool = False


class PartialWriteRequest(BaseModel):
    """Write a partial paper from directly-supplied sections (no session required)."""
    title: str
    abstract: str = ""
    sections: List[Dict[str, str]]   # [{"title": ..., "content": ...}, ...]
    citations: Dict[str, Any] = {}
    compile_pdf: bool = True
    template: str = "ieee"
    author: str = ""
    session_id: str = ""            # optional, used only for output filename
    use_multi_agent_writer: bool = False
    allow_fallback_pdf: bool = False


ALLOWED_PAPER_TEMPLATES = {"ieee"}


def _normalize_paper_template(value: Any) -> str:
    normalized = str(value or "ieee").strip().lower()
    if normalized not in ALLOWED_PAPER_TEMPLATES:
        allowed = ", ".join(sorted(ALLOWED_PAPER_TEMPLATES))
        raise HTTPException(status_code=400, detail=f"Unsupported template. Allowed values: {allowed}.")
    return normalized


def _sanitize_context_summary(text: str) -> str:
    cleaned = str(text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not cleaned:
        return ""

    lowered = cleaned.lower()
    cut_markers = ["repository context summary", "##analysis", "analysis stats", "structure preview"]
    cut_points = [idx for idx in (lowered.find(marker) for marker in cut_markers) if idx != -1]
    if cut_points:
        cleaned = cleaned[: min(cut_points)].strip()

    cleaned = re.sub(r"^\s*abstract\s*[—:\-]\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned[:1200].strip()


class SectionRefineRequest(BaseModel):
    """Refine a single paper section via the LLM based on a user chat message."""
    section_key: str
    section_title: str
    current_content: str
    user_message: str
    paper_title: str = "Research Paper"
    context_summary: str = ""   # optional: brief abstract/keywords for context
    session_id: str = ""


# ============================================================================
# Models
# ============================================================================

class UserLogin(BaseModel):
    email: str
    password: str

class UserRegister(BaseModel):
    name: str
    email: str
    password: str

# ... (rest of models)

# ============================================================================
# Auth Endpoints (Mock)
# ============================================================================

@app.post("/api/auth/login")
async def login(user: UserLogin):
    """Mock login."""
    # In a real app, verify passwords
    return {
        "status": "success",
        "user": {
            "name": "Research Scholar",
            "email": user.email,
            "role": "academic"
        },
        "token": "mock-token-" + str(uuid.uuid4())
    }

@app.post("/api/auth/register")
async def register(user: UserRegister):
    """Mock register."""
    return {
        "status": "success",
        "user": {
            "name": user.name,
            "email": user.email,
            "role": "academic"
        },
        "token": "mock-token-" + str(uuid.uuid4())
    }


@app.on_event("startup")
async def startup():
    """Initialize on startup."""
    logger.info("🚀 Starting Yukti Research AI Server...")
    status = await orchestrator.initialize()
    logger.info(f"✓ System initialized: {json.dumps(status, indent=2)}")

# ============================================================================
# REST API Endpoints
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the main frontend."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return HTMLResponse("<h1>Yukti Research AI - Frontend not found</h1>")


@app.get("/api/status")
async def get_status():
    """Get system status."""
    return {
        "status": "online",
        "version": "1.0.0",
        "llm": orchestrator.llm_client.get_status(),
        "active_sessions": len(orchestrator.sessions),
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/system/setup")
async def setup_system():
    """Recommend and auto-setup Ollama model based on hardware."""
    try:
        # Perform auto-setup initialization
        success = await orchestrator.llm_client.initialize(auto_setup=True)
        return {
            "success": success,
            "status": orchestrator.llm_client.get_status(),
            "message": "Optimization complete" if success else "Ollama not reachable"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/references/formats", response_model=ReferencesFormatsResponse)
async def get_reference_formats():
    """Expose pyzotero-supported export formats and style note."""
    info = pyzotero_capabilities()
    return ReferencesFormatsResponse(
        available=bool(info.get("available", False)),
        formats=list(info.get("formats", [])),
        style_note=str(info.get("style_note", "")),
    )


@app.post("/api/references/generate")
async def generate_reference_section(req: ReferencesRequest):
    """Generate a reference section from scholarly web discovery + metadata enrichment."""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query is required")

    if req.limit < 1 or req.limit > 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")

    try:
        result = generate_references(req.query.strip(), req.limit, req.style, req.excluded_titles)
        return {"status": "success", "data": result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Reference generation failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate references")


@app.post("/api/research")
async def start_research(request: ResearchRequest):
    """Start a new research task (non-WebSocket fallback)."""
    session_id = str(uuid.uuid4())[:8]
    
    try:
        result = await orchestrator.run_research(
            query=request.query,
            session_id=session_id,
            citation_style=request.citation_style
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions")
async def get_sessions():
    """Get all research sessions."""
    return orchestrator.get_all_sessions()


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Get a specific session."""
    session = orchestrator.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.post("/api/chat")
async def chat(msg: ChatMessage):
    """Chat about a research report."""
    session = orchestrator.get_session(msg.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    result = session.get("result", {})
    report = result.get("report", "")
    
    # Initialize chat session if needed
    if msg.session_id not in chat_sessions:
        chat_sessions[msg.session_id] = {
            "messages": [],
            "report_context": report
        }
    
    chat = chat_sessions[msg.session_id]
    chat["messages"].append({"role": "user", "content": msg.message})
    
    # Generate response using LLM
    llm = orchestrator.llm_client
    
    if llm.is_available:
        system_prompt = f"""You are Yukti Research AI assistant. You are discussing a research report that was generated.
        
The report context (respond ONLY based on this):
{report[:4000]}

Rules:
1. Only answer questions based on the report content
2. If asked about something not in the report, say so
3. Use citations from the report where possible
4. Be concise and helpful
5. Respond in markdown format"""

        prompt = f"User question: {msg.message}"
        response = await llm.generate(prompt, system=system_prompt)
    else:
        response = (
            "I can see the report has been generated. However, the local LLM (Ollama) "
            "is not currently available for chat. Please install Ollama to enable chat functionality.\n\n"
            f"Your question was about: {msg.message}\n\n"
            "The report covers the key findings in the sections listed in the table of contents."
        )
    
    chat["messages"].append({"role": "assistant", "content": response})
    
    return {
        "response": response,
        "session_id": msg.session_id
    }


# ============================================================================
# Writing & LaTeX Endpoints
# ============================================================================

@app.post("/api/write")
async def write_report(req: WriteRequest):
    """
    Generate a LaTeX document (and optionally a PDF) for a completed session.
    The session must already have been completed via /api/research or /ws/research.
    """
    session = orchestrator.get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    result_data = session.get("result")
    if not result_data:
        raise HTTPException(
            status_code=400,
            detail="Session has no completed research result. Run research first."
        )

    template = _normalize_paper_template(req.template)

    try:
        write_result = await writing_service.write(
            research_result=result_data,
            session_id=req.session_id,
            compile_pdf=req.compile_pdf,
            template=template,
            author=req.author,
            use_multi_agent_writer=req.use_multi_agent_writer,
            allow_fallback_pdf=req.allow_fallback_pdf,
        )
        return {
            "status": "success",
            "session_id": req.session_id,
            "tex_path": write_result["tex_path"],
            "pdf_path": write_result.get("pdf_path"),
            "pdf_success": write_result["pdf_success"],
            "compile_errors": write_result["compile_errors"],
            "compile_warnings": write_result["compile_warnings"],
            "download_tex": f"/api/export/{req.session_id}/latex?download=1",
            "preview_pdf": f"/api/export/{req.session_id}/pdf" if write_result["pdf_success"] else None,
            "download_pdf": f"/api/export/{req.session_id}/pdf?download=1" if write_result["pdf_success"] else None,
        }
    except Exception as exc:
        logger.error(f"Writing service error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/write/partial")
async def write_partial_report(req: PartialWriteRequest):
    """
    Generate a LaTeX document (and optionally PDF) from directly-supplied sections.
    Does NOT require a prior research session — useful for progressive section review.
    """
    import uuid as _uuid
    sid = req.session_id.strip() or _uuid.uuid4().hex[:8]

    research_result = {
        "title":    req.title,
        "abstract": req.abstract,
        "sections": req.sections,
        "citations": req.citations,
        "report":   "",
    }
    template = _normalize_paper_template(req.template)

    try:
        write_result = await writing_service.write(
            research_result=research_result,
            session_id=f"{sid}_partial",
            compile_pdf=req.compile_pdf,
            template=template,
            author=req.author,
            use_multi_agent_writer=req.use_multi_agent_writer,
            allow_fallback_pdf=req.allow_fallback_pdf,
        )
        partial_sid = f"{sid}_partial"
        return {
            "status": "success",
            "session_id": partial_sid,
            "tex_path": write_result["tex_path"],
            "pdf_path": write_result.get("pdf_path"),
            "pdf_success": write_result["pdf_success"],
            "compile_errors": write_result["compile_errors"],
            "compile_warnings": write_result["compile_warnings"],
            "download_tex": f"/api/export/{partial_sid}/latex?download=1",
            "preview_pdf": f"/api/export/{partial_sid}/pdf" if write_result["pdf_success"] else None,
            "download_pdf": f"/api/export/{partial_sid}/pdf?download=1" if write_result["pdf_success"] else None,
        }
    except Exception as exc:
        logger.error(f"Partial write error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/write/raw")
async def write_raw_report(request: ResearchRequest):
    """
    Run a full research pipeline AND generate LaTeX/PDF in one call.
    """
    session_id = str(uuid.uuid4())[:8]
    try:
        result = await orchestrator.run_research(
            query=request.query,
            session_id=session_id,
            citation_style=request.citation_style,
        )
        write_result = await writing_service.write(
            research_result=result,
            session_id=session_id,
            compile_pdf=True,
            use_multi_agent_writer=False,
            allow_fallback_pdf=False,
        )
        return {
            "status": "success",
            "session_id": session_id,
            **write_result,
            "download_tex": f"/api/export/{session_id}/latex?download=1",
            "preview_pdf": f"/api/export/{session_id}/pdf" if write_result["pdf_success"] else None,
            "download_pdf": f"/api/export/{session_id}/pdf?download=1" if write_result["pdf_success"] else None,
        }
    except Exception as exc:
        logger.error(f"Write-raw error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================================
# Section Refine Endpoint
# ============================================================================

@app.post("/api/section/refine")
async def section_refine(req: SectionRefineRequest):
    """
    Refine a single academic paper section via Ollama.

    The user's chat message is used as an instruction; the LLM rewrites the
    section and returns the improved content.
    """
    # IEEE word-count targets per section
    word_targets = {
        "abstract":         "150–250",
        "introduction":     "400–600",
        "related_studies":  "600–900",
        "methodology":      "500–800",
        "result_discussion": "800–1200",
        "conclusion":       "200–350",
    }
    target = word_targets.get(req.section_key, "400–700")

    context_summary = _sanitize_context_summary(req.context_summary)
    context_block = (
        f"\nPaper context/abstract:\n{context_summary}\n"
        if context_summary else ""
    )

    prompt = (
        f"You are an expert academic writer helping prepare an IEEE-format research paper.\n"
        f"Paper title: {req.paper_title}\n"
        f"Section: {req.section_title} (target word count: {target} words){context_block}\n"
        f"--- Current section content ---\n{req.current_content}\n"
        f"--- End of current content ---\n\n"
        f"User instruction: {req.user_message}\n\n"
        f"Rewrite the {req.section_title} section following the user's instruction. "
        f"Keep a formal academic tone suitable for IEEE publication. "
        f"Return ONLY the revised section text with no extra preamble or labels."
    )

    try:
        client = OllamaClient()
        refined = await client.generate(prompt, max_tokens=2048)
        return {
            "status": "success",
            "section_key": req.section_key,
            "content": refined.strip(),
        }
    except Exception as exc:
        logger.error(f"Section refine error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================================
# GitHub Intelligence Endpoints
# ============================================================================

class GithubAnalyzeRequest(BaseModel):
    repo_url: str
    existing_title: Optional[str] = None
    output_dir: str = "./outputs/GitHub"
    github_token: Optional[str] = None   # optional PAT for higher rate limits


class RepoAnalyzeRequest(BaseModel):
    repo_url: Optional[str] = None
    folder_path: Optional[str] = None
    existing_title: Optional[str] = None
    output_dir: str = "./outputs/GitHub"


def _resolve_output_dir(raw_output_dir: str) -> Path:
    path = Path(raw_output_dir).expanduser()
    if not path.is_absolute():
        path = (BASE_DIR / path).resolve()
    return path


def _sanitize_uploaded_relative_path(filename: str) -> Path:
    normalized = (filename or "").replace("\\", "/")
    parts = [part for part in normalized.split("/") if part and part not in {".", ".."}]
    if not parts:
        raise ValueError("Invalid upload filename")
    return Path(*parts)


@app.post("/api/github/analyze")
async def github_analyze(req: GithubAnalyzeRequest):
    """
    Analyze a public GitHub repository via the repo_analyzer pipeline.
    """
    try:
        result = await asyncio.to_thread(
            analyze_github_repository,
            req.repo_url.strip(),
            _resolve_output_dir(req.output_dir),
            req.existing_title,
        )
        return {"status": "success", "data": result}
    except RepoAnalysisError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("GitHub analyze error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/repo/analyze")
async def repo_analyze(req: RepoAnalyzeRequest):
    """
    Analyze either a GitHub repository URL or a local folder path,
    returning structure + summary + generated title.
    """
    if not (req.repo_url or req.folder_path):
        raise HTTPException(status_code=400, detail="Provide either repo_url or folder_path")

    try:
        output_dir = _resolve_output_dir(req.output_dir)
        if req.repo_url:
            result = await asyncio.to_thread(
                analyze_github_repository,
                req.repo_url.strip(),
                output_dir,
                req.existing_title,
            )
        else:
            result = await asyncio.to_thread(
                analyze_local_repository,
                (req.folder_path or "").strip(),
                output_dir,
                req.existing_title,
            )

        return {"status": "success", "data": result}
    except RepoAnalysisError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Repository analyze error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/repo/analyze-folder")
async def repo_analyze_folder_upload(
    files: List[UploadFile] = File(...),
    existing_title: str = Form(""),
    output_dir: str = Form("./outputs/GitHub"),
):
    """
    Analyze a browser-selected folder (uploaded as many files), without zip.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files were uploaded")
    if len(files) > 5000:
        raise HTTPException(status_code=400, detail="Too many files uploaded (max 5000)")

    temp_root = Path(tempfile.mkdtemp(prefix="repo_upload_"))
    written_paths: List[Path] = []

    try:
        for idx, upload in enumerate(files):
            raw_name = upload.filename or f"file_{idx}"
            try:
                relative_path = _sanitize_uploaded_relative_path(raw_name)
            except ValueError:
                continue

            target_path = temp_root / relative_path
            target_path.parent.mkdir(parents=True, exist_ok=True)

            content = await upload.read()
            target_path.write_bytes(content)
            written_paths.append(relative_path)
            await upload.close()

        if not written_paths:
            raise HTTPException(status_code=400, detail="Uploaded files were invalid or empty")

        all_nested = all(len(p.parts) > 1 for p in written_paths)
        top_levels = {p.parts[0] for p in written_paths if len(p.parts) > 1}

        repo_root = temp_root
        if all_nested and len(top_levels) == 1:
            candidate = temp_root / next(iter(top_levels))
            if candidate.exists() and candidate.is_dir():
                repo_root = candidate

        result = await asyncio.to_thread(
            analyze_repo_path,
            repo_root,
            _resolve_output_dir(output_dir),
            existing_title.strip() or None,
            "uploaded_folder",
            "browser_folder_upload",
        )
        return {"status": "success", "data": result}
    except RepoAnalysisError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Folder upload analyze error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


@app.get("/api/github/analyze/{job_id}")
async def github_status(job_id: str):
    """Placeholder for future async job status tracking."""
    return {"status": "not_implemented", "message": "Use POST /api/github/analyze (synchronous)"}


@app.get("/api/export/{session_id}/{format}")
async def export_report(session_id: str, format: str, download: bool = False):
    """Export report in specified format."""
    output_dir = Path("outputs")
    
    if format == "markdown":
        file_path = output_dir / f"{session_id}_report.md"
        media_type = "text/markdown"
        filename = f"yukti_report_{session_id}.md"
    elif format == "html":
        file_path = output_dir / f"{session_id}_report.html"
        media_type = "text/html"
        filename = f"yukti_report_{session_id}.html"
    elif format == "pdf":
        file_path = output_dir / f"{session_id}_report.pdf"
        media_type = "application/pdf"
        filename = f"yukti_report_{session_id}.pdf"
    elif format == "latex":
        file_path = output_dir / f"{session_id}_report.tex"
        media_type = "application/x-tex"
        filename = f"yukti_report_{session_id}.tex"
    else:
        raise HTTPException(status_code=400, detail="Unsupported format. Use 'markdown', 'html', 'pdf', or 'latex'")
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found. Run research first.")

    disposition = "attachment" if download else "inline"
    
    return FileResponse(
        str(file_path),
        media_type=media_type,
        filename=filename,
        content_disposition_type=disposition,
    )


# ============================================================================
# WebSocket Endpoint
# ============================================================================

@app.websocket("/ws/research")
async def websocket_research(websocket: WebSocket):
    """
    WebSocket endpoint for real-time research with progress updates.
    
    Client sends: {"query": "...", "citation_style": "IEEE"}
    Server sends progress updates and final result.
    """
    await websocket.accept()
    session_id = str(uuid.uuid4())[:8]
    active_connections[session_id] = websocket
    
    logger.info(f"WebSocket connected: {session_id}")
    
    try:
        while True:
            # Receive research request
            data = await websocket.receive_text()
            request = json.loads(data)
            
            action = request.get("action", "research")
            
            if action == "research":
                query = request.get("query", "")
                citation_style = request.get("citation_style", "IEEE")
                
                if not query:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Query is required"
                    })
                    continue
                
                # Send session info
                await websocket.send_json({
                    "type": "session",
                    "session_id": session_id,
                    "query": query
                })
                
                # Define progress callback (supports optional 4th `data` arg for section_ready)
                async def progress_callback(agent: str, status: str, message: str, data=None):
                    try:
                        if status == "section_ready" and data:
                            await websocket.send_json({
                                "type": "section_ready",
                                "section": data,
                                "timestamp": datetime.now().isoformat()
                            })
                        else:
                            await websocket.send_json({
                                "type": "progress",
                                "agent": agent,
                                "status": status,
                                "message": message,
                                "timestamp": datetime.now().isoformat()
                            })
                    except Exception:
                        pass  # Connection may have closed
                
                # Run research with progress updates
                try:
                    result = await orchestrator.run_research(
                        query=query,
                        session_id=session_id,
                        callback=progress_callback,
                        citation_style=citation_style
                    )
                    
                    # Send final result — guard against WS closing during research
                    try:
                        await websocket.send_json({
                            "type": "result",
                            "data": result
                        })
                    except (RuntimeError, Exception):
                        pass  # Client disconnected before result arrived
                    
                except Exception as e:
                    try:
                        await websocket.send_json({
                            "type": "error",
                            "message": str(e) or repr(e)
                        })
                    except (RuntimeError, Exception):
                        pass  # Client disconnected
            
            elif action == "chat":
                message = request.get("message", "")
                
                session = orchestrator.get_session(session_id)
                report = ""
                if session and session.get("result"):
                    report = session["result"].get("report", "")
                
                llm = orchestrator.llm_client
                if llm.is_available and report:
                    system_prompt = f"""You are Yukti Research AI. Answer based on the research report:
{report[:4000]}

Rules: Only answer from report context. Use citations. Be concise. Markdown format."""
                    response = await llm.generate(f"User: {message}", system=system_prompt)
                else:
                    response = "Please run a research query first, and ensure Ollama is available for chat."
                
                await websocket.send_json({
                    "type": "chat_response",
                    "message": response,
                    "session_id": session_id
                })
            
            elif action == "write":
                session = orchestrator.get_session(session_id)
                result_data = session.get("result") if session else None
                if not result_data:
                    await websocket.send_json({
                        "type": "error",
                        "message": "No completed research in this session. Run research first."
                    })
                    continue

                await websocket.send_json({
                    "type": "progress",
                    "agent": "writer",
                    "status": "started",
                    "message": "Generating LaTeX document…"
                })

                try:
                    template = _normalize_paper_template(request.get("template", "ieee"))
                except HTTPException as exc:
                    await websocket.send_json({
                        "type": "error",
                        "message": exc.detail,
                    })
                    continue

                try:
                    write_result = await writing_service.write(
                        research_result=result_data,
                        session_id=session_id,
                        compile_pdf=request.get("compile_pdf", True),
                        template=template,
                        author=request.get("author", ""),
                        use_multi_agent_writer=request.get("use_multi_agent_writer", False),
                        allow_fallback_pdf=request.get("allow_fallback_pdf", False),
                    )
                    await websocket.send_json({
                        "type": "write_result",
                        "data": {
                            **write_result,
                            "download_tex": f"/api/export/{session_id}/latex?download=1",
                            "preview_pdf": (
                                f"/api/export/{session_id}/pdf"
                                if write_result["pdf_success"] else None
                            ),
                            "download_pdf": (
                                f"/api/export/{session_id}/pdf?download=1"
                                if write_result["pdf_success"] else None
                            ),
                        }
                    })
                except Exception as exc:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Writing failed: {exc}"
                    })

            elif action == "status":
                await websocket.send_json({
                    "type": "status",
                    "data": {
                        "llm": orchestrator.llm_client.get_status(),
                        "session": orchestrator.get_session(session_id)
                    }
                })
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except RuntimeError as e:
        logger.info(f"WebSocket closed before completion ({session_id}): {e}")
    except Exception as e:
        if "WebSocket is not connected" in str(e):
            logger.info(f"WebSocket connection already closed: {session_id}")
        else:
            logger.error(f"WebSocket error: {e}")
    finally:
        active_connections.pop(session_id, None)

# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
