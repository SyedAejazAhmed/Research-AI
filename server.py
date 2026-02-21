"""
Yukti Research AI - FastAPI Server
====================================
Main server with REST API + WebSocket for real-time research progress.
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.orchestrator import ResearchOrchestrator
from app.agents.llm_client import OllamaClient

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

# Static files
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "app" / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Initialize orchestrator
orchestrator = ResearchOrchestrator(output_dir=str(BASE_DIR / "outputs"))

# WebSocket connections
active_connections: Dict[str, WebSocket] = {}

# Chat sessions (in-memory)
chat_sessions: Dict[str, Dict] = {}


# ============================================================================
# Models
# ============================================================================

class ResearchRequest(BaseModel):
    query: str
    citation_style: str = "APA"

class ChatMessage(BaseModel):
    session_id: str
    message: str

class ExportRequest(BaseModel):
    session_id: str
    format: str = "markdown"  # markdown, html


# ============================================================================
# Startup
# ============================================================================

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


@app.get("/api/export/{session_id}/{format}")
async def export_report(session_id: str, format: str):
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
    
    return FileResponse(
        str(file_path),
        media_type=media_type,
        filename=filename
    )


# ============================================================================
# WebSocket Endpoint
# ============================================================================

@app.websocket("/ws/research")
async def websocket_research(websocket: WebSocket):
    """
    WebSocket endpoint for real-time research with progress updates.
    
    Client sends: {"query": "...", "citation_style": "APA"}
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
                citation_style = request.get("citation_style", "APA")
                
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
                
                # Define progress callback
                async def progress_callback(agent: str, status: str, message: str):
                    try:
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
                    
                    # Send final result
                    await websocket.send_json({
                        "type": "result",
                        "data": result
                    })
                    
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })
            
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
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        active_connections.pop(session_id, None)


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
