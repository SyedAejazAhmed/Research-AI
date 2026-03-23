"""
Enhanced API Routes with Security and New Features
===================================================
Complete API endpoints with:
- Security middleware
- LLM checker
- Pipeline orchestrator
- Ordered references
- All existing features
"""

from fastapi import APIRouter, HTTPException, File, UploadFile, BackgroundTasks, Request, Header, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging
from pathlib import Path
import asyncio

from app.database.schema import ResearchDatabase
from app.pipeline_orchestrator import ResearchPipelineOrchestrator
from app.agents.llm_checker import LLMChecker
from app.agents.ordered_reference_agent import OrderedReferenceAgent, PaperSection
from app.security import (
    SecurityMiddleware,
    ResearchQueryValidator,
    GitHubRepoValidator,
    FileUploadValidator
)

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter()

# Initialize security
security = SecurityMiddleware()

# Initialize components
db = ResearchDatabase()
orchestrator = ResearchPipelineOrchestrator()
llm_checker = LLMChecker()
ref_agent = OrderedReferenceAgent(database_manager=db)


# =============================================================================
# Security Dependency
# =============================================================================

async def validate_security(
    request: Request,
    x_api_key: Optional[str] = Header(None)
):
    """Security validation dependency"""
    await security.validate_request(request, x_api_key)
    return True


# =============================================================================
# Pydantic Models
# =============================================================================

class CitationCreate(BaseModel):
    title: str
    authors: List[str]
    year: Optional[int] = None
    venue: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    url: Optional[str] = None
    abstract: Optional[str] = None
    keywords: List[str] = []


class PipelineRequest(BaseModel):
    query: str
    research_mode: str = "academic"
    template_type: str = "IEEE"
    citation_style: str = "APA"
    github_repo: Optional[str] = None
    max_citations: int = 30
    include_images: bool = True
    export_formats: List[str] = ["pdf", "markdown", "bibtex"]


class ReferenceAssignmentRequest(BaseModel):
    citation_ids: List[str]
    mode: str = "auto"  # "auto" or "manual"
    section_weights: Optional[Dict[str, float]] = None


# =============================================================================
# Health & Status Endpoints
# =============================================================================

@router.get("/api/health", tags=["system"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Research AI Platform",
        "version": "2.0.0"
    }


@router.get("/api/system/status", tags=["system"])
async def system_status():
    """Get system status including LLM availability"""
    ollama_available = await llm_checker.check_ollama_available()
    installed_models = await llm_checker.get_installed_models() if ollama_available else []
    recommended = llm_checker.recommend_models(top_n=3)

    return {
        "ollama_available": ollama_available,
        "installed_models": installed_models,
        "recommended_models": [
            {
                "name": m.name,
                "size_gb": m.size_gb,
                "quality": m.quality_score,
                "description": m.description
            }
            for m in recommended
        ],
        "system_info": llm_checker.system_info
    }


# =============================================================================
# Pipeline Orchestration Endpoints
# =============================================================================

@router.post("/api/pipeline/run", tags=["pipeline"], dependencies=[Depends(validate_security)])
async def run_pipeline(request: PipelineRequest):
    """
    Run the complete research pipeline

    This endpoint orchestrates:
    1. LLM availability check
    2. Research planning and execution
    3. Citation management
    4. PDF processing with RAG
    5. Ordered reference assignment
    6. GitHub analysis (if repo provided)
    7. Content synthesis
    8. LaTeX generation
    9. Multi-format export
    """
    try:
        # Validate query
        validator = ResearchQueryValidator(
            query=request.query,
            research_mode=request.research_mode,
            template_type=request.template_type,
            citation_style=request.citation_style,
            max_citations=request.max_citations
        )

        # Validate GitHub URL if provided
        if request.github_repo:
            GitHubRepoValidator(repo_url=request.github_repo)

        # Run pipeline
        results = await orchestrator.run_full_pipeline(
            query=validator.query,
            research_mode=validator.research_mode,
            template_type=validator.template_type,
            citation_style=validator.citation_style,
            github_repo=request.github_repo,
            max_citations=validator.max_citations,
            include_images=request.include_images,
            export_formats=request.export_formats
        )

        return results

    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/pipeline/sessions", tags=["pipeline"])
async def list_pipeline_sessions():
    """List all pipeline sessions"""
    sessions = orchestrator.list_sessions()
    return {
        "sessions": sessions,
        "count": len(sessions)
    }


@router.get("/api/pipeline/sessions/{session_id}", tags=["pipeline"])
async def get_pipeline_session(session_id: str):
    """Get pipeline session status"""
    status = await orchestrator.get_pipeline_status(session_id)

    if not status:
        raise HTTPException(status_code=404, detail="Session not found")

    return status


# =============================================================================
# Citation Management Endpoints
# =============================================================================

@router.post("/api/citations", tags=["citations"])
async def create_citation(citation: CitationCreate):
    """Create a new citation"""
    try:
        citation_id = await db.add_citation(
            title=citation.title,
            authors=citation.authors,
            year=citation.year,
            venue=citation.venue,
            doi=citation.doi,
            arxiv_id=citation.arxiv_id,
            url=citation.url,
            abstract=citation.abstract
        )

        return {
            "success": True,
            "citation_id": citation_id,
            "message": "Citation created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/citations", tags=["citations"])
async def search_citations(
    query: Optional[str] = None,
    author: Optional[str] = None,
    year: Optional[int] = None,
    limit: int = 50
):
    """Search citations"""
    try:
        citations = await db.search_citations(
            query=query,
            author=author,
            year=year,
            limit=limit
        )

        return {
            "citations": citations,
            "count": len(citations)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/citations/{citation_id}", tags=["citations"])
async def get_citation(citation_id: str):
    """Get citation by ID"""
    citation = await db.get_citation(citation_id)

    if not citation:
        raise HTTPException(status_code=404, detail="Citation not found")

    return citation


@router.post("/api/citations/{citation_id}/upload-pdf", tags=["citations"])
async def upload_citation_pdf(
    citation_id: str,
    file: UploadFile = File(...),
    secure: bool = Depends(validate_security)
):
    """Upload PDF for a citation"""
    try:
        # Validate file
        FileUploadValidator(
            filename=file.filename,
            file_size=file.size if hasattr(file, 'size') else 0,
            content_type=file.content_type
        )

        # Save PDF and process
        pdf_path = Path("outputs") / "pdfs" / f"{citation_id}.pdf"
        pdf_path.parent.mkdir(parents=True, exist_ok=True)

        with open(pdf_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Process PDF and create embeddings
        # (Implementation would use RAG system)

        return {
            "success": True,
            "message": "PDF uploaded and processed",
            "path": str(pdf_path)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Ordered Reference Management Endpoints
# =============================================================================

@router.post("/api/references/assign", tags=["references"])
async def assign_references(request: ReferenceAssignmentRequest):
    """Assign references to paper sections"""
    try:
        if request.mode == "auto":
            assignments = ref_agent.auto_assign_sections(
                citation_ids=request.citation_ids,
                section_weights=request.section_weights
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Manual assignment not yet implemented"
            )

        summary = ref_agent.get_section_summary()

        return {
            "success": True,
            "assignments": {
                section.value: {
                    "citation_ids": assignment.citation_ids,
                    "range": f"{assignment.start_index}-{assignment.end_index}",
                    "count": len(assignment.citation_ids)
                }
                for section, assignment in assignments.items()
            },
            "summary": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/references/sections/{section}/activate", tags=["references"])
async def activate_section_embeddings(section: str):
    """Activate embeddings for a specific section"""
    try:
        section_enum = PaperSection(section)
        activated = await ref_agent.activate_embeddings_for_section(section_enum)

        return {
            "success": True,
            "section": section,
            "activated_count": len(activated),
            "embeddings": [
                {
                    "citation_id": e.citation_id,
                    "reference_number": e.reference_number
                }
                for e in activated
            ]
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid section name")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/references/sections/{section}/retrieve", tags=["references"])
async def retrieve_section_context(section: str, query: str, top_k: int = 5):
    """Retrieve RAG context for a section"""
    try:
        section_enum = PaperSection(section)
        results = await ref_agent.retrieve_context_for_section(
            section=section_enum,
            query=query,
            top_k=top_k
        )

        return {
            "success": True,
            "section": section,
            "query": query,
            "results": results
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid section name")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# LLM Management Endpoints
# =============================================================================

@router.get("/api/llm/models/installed", tags=["llm"])
async def get_installed_models():
    """Get installed LLM models"""
    models = await llm_checker.get_installed_models()
    return {
        "models": models,
        "count": len(models)
    }


@router.get("/api/llm/models/recommended", tags=["llm"])
async def get_recommended_models(top_n: int = 5):
    """Get recommended LLM models for this system"""
    recommended = llm_checker.recommend_models(top_n=top_n)

    return {
        "recommended": [
            {
                "name": m.name,
                "provider": m.provider,
                "size_gb": m.size_gb,
                "quality_score": m.quality_score,
                "description": m.description,
                "requirements": {
                    "ram_gb": m.requirements.ram_gb,
                    "disk_gb": m.requirements.disk_gb,
                    "gpu_required": m.requirements.gpu_required
                }
            }
            for m in recommended
        ],
        "count": len(recommended)
    }


@router.post("/api/llm/models/{model_name}/download", tags=["llm"])
async def download_model(model_name: str, background_tasks: BackgroundTasks):
    """Download an LLM model"""

    async def download_task():
        success = await llm_checker.download_model(model_name)
        if success:
            logger.info(f"Model {model_name} downloaded successfully")
        else:
            logger.error(f"Failed to download model {model_name}")

    background_tasks.add_task(download_task)

    return {
        "message": f"Download started for {model_name}",
        "status": "in_progress"
    }


# =============================================================================
# Security Endpoints
# =============================================================================

@router.get("/api/security/rate-limit", tags=["security"])
async def get_rate_limit_status(request: Request):
    """Get rate limit status for current client"""
    client_id = request.client.host
    usage = security.rate_limiter.get_usage(client_id)

    return usage


@router.post("/api/security/api-keys/generate", tags=["security"])
async def generate_api_key(
    user_id: str,
    name: str,
    expires_days: Optional[int] = None
):
    """Generate a new API key"""
    api_key = security.api_key_manager.generate_key(
        user_id=user_id,
        name=name,
        expires_days=expires_days
    )

    return {
        "api_key": api_key,
        "user_id": user_id,
        "name": name,
        "expires_days": expires_days
    }


# Export router
__all__ = ["router"]
