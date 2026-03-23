"""
Enhanced API Routes for Research AI Platform
=============================================
Comprehensive API endpoints for all platform features.
"""

from fastapi import APIRouter, HTTPException, File, UploadFile, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging
from pathlib import Path
import shutil

from app.database.schema import ResearchDatabase
from app.agents.rag_system import RAGSystem, OrderedReferenceAgent
from app.agents.paper_pipeline import AcademicPaperPipeline
from app.agents.github_analyzer import GitHubRepoAnalyzer
from multi_agent.agents.zotero_integration import ZoteroIntegrationAgent, ZoteroConfig

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter()

# Initialize components
db = ResearchDatabase()
rag_system = RAGSystem(db_manager=db)
ref_agent = OrderedReferenceAgent(db, rag_system)
paper_pipeline = AcademicPaperPipeline(db_path="research_ai.db")
github_analyzer = GitHubRepoAnalyzer()


# =============================================================================
# Pydantic Models
# =============================================================================

class CitationCreate(BaseModel):
    title: str
    authors: List[str]
    year: Optional[int] = None
    source: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    abstract: Optional[str] = None
    keywords: List[str] = []


class CitationSearch(BaseModel):
    query: Optional[str] = None
    author: Optional[str] = None
    year: Optional[int] = None
    doi: Optional[str] = None
    limit: int = 50


class PaperGenerationRequest(BaseModel):
    query: str
    citation_ids: List[str]
    template_type: str = "IEEE"
    research_mode: str = "academic"
    github_repo: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class GitHubAnalysisRequest(BaseModel):
    repo_url: str
    extract_images: bool = True


# =============================================================================
# Citation Management Endpoints
# =============================================================================

@router.post("/api/citations", tags=["citations"])
async def create_citation(citation: CitationCreate):
    """Create a new citation"""
    try:
        import hashlib
        citation_id = hashlib.sha256(
            f"{citation.title}_{citation.doi or ''}".encode()
        ).hexdigest()[:16]

        success = db.add_citation(
            citation_id=citation_id,
            title=citation.title,
            authors=citation.authors,
            year=citation.year,
            source=citation.source,
            doi=citation.doi,
            url=citation.url,
            abstract=citation.abstract,
            keywords=citation.keywords
        )

        if success:
            return {
                "success": True,
                "citation_id": citation_id,
                "message": "Citation created successfully"
            }
        else:
            raise HTTPException(status_code=400, detail="Citation already exists")

    except Exception as e:
        logger.error(f"Error creating citation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/citations", tags=["citations"])
async def search_citations(
    q: Optional[str] = None,
    author: Optional[str] = None,
    year: Optional[int] = None,
    doi: Optional[str] = None,
    limit: int = 50
):
    """Search citations"""
    try:
        citations = db.search_citations(
            query=q,
            author=author,
            year=year,
            doi=doi,
            limit=limit
        )

        return {
            "success": True,
            "citations": citations,
            "count": len(citations)
        }

    except Exception as e:
        logger.error(f"Error searching citations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/citations/{citation_id}", tags=["citations"])
async def get_citation(citation_id: str):
    """Get citation by ID"""
    try:
        citation = db.get_citation(citation_id)

        if citation:
            return {
                "success": True,
                "citation": citation
            }
        else:
            raise HTTPException(status_code=404, detail="Citation not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting citation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/citations/upload-pdf/{citation_id}", tags=["citations"])
async def upload_citation_pdf(citation_id: str, file: UploadFile = File(...)):
    """Upload PDF for a citation and process embeddings"""
    try:
        # Save uploaded file
        upload_dir = Path("outputs/pdfs")
        upload_dir.mkdir(parents=True, exist_ok=True)

        pdf_path = upload_dir / f"{citation_id}.pdf"

        with open(pdf_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Process PDF and generate embeddings
        result = await rag_system.process_pdf(
            pdf_path=str(pdf_path),
            citation_id=citation_id
        )

        if result.get("success"):
            # Update citation with PDF path
            citation = db.get_citation(citation_id)
            if citation:
                db.add_citation(
                    citation_id=citation_id,
                    **{**citation, "pdf_path": str(pdf_path)}
                )

            return {
                "success": True,
                "message": "PDF processed successfully",
                "chunks": result.get("chunks", 0),
                "pdf_path": str(pdf_path)
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("error"))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/citations/export/bibtex", tags=["citations"])
async def export_bibtex(citation_ids: Optional[List[str]] = None):
    """Export citations as BibTeX"""
    try:
        # Get citations
        if citation_ids:
            citations = [db.get_citation(cid) for cid in citation_ids if db.get_citation(cid)]
        else:
            citations = db.search_citations(limit=1000)

        # Generate BibTeX from LaTeX agent
        from app.agents.latex_writing_agent import LaTeXWritingAgent
        latex_agent = LaTeXWritingAgent()
        bibtex = latex_agent._generate_bibtex(citations)

        return {
            "success": True,
            "bibtex": bibtex,
            "count": len(citations)
        }

    except Exception as e:
        logger.error(f"Error exporting BibTeX: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Paper Generation Endpoints
# =============================================================================

@router.post("/api/papers/generate", tags=["papers"])
async def generate_paper(request: PaperGenerationRequest, background_tasks: BackgroundTasks):
    """Generate complete academic paper"""
    try:
        # Get citations from database
        citations = [db.get_citation(cid) for cid in request.citation_ids]
        citations = [c for c in citations if c is not None]

        if not citations:
            raise HTTPException(status_code=400, detail="No valid citations found")

        # Generate paper
        result = await paper_pipeline.generate_paper(
            query=request.query,
            citations=citations,
            template_type=request.template_type,
            research_mode=request.research_mode,
            github_repo=request.github_repo,
            metadata=request.metadata
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating paper: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/papers/{paper_id}", tags=["papers"])
async def get_paper(paper_id: str):
    """Get paper by ID"""
    try:
        # Query from database
        cursor = db.conn.cursor()
        cursor.execute("SELECT * FROM papers WHERE id = ?", (paper_id,))
        row = cursor.fetchone()

        if row:
            return {
                "success": True,
                "paper": dict(row)
            }
        else:
            raise HTTPException(status_code=404, detail="Paper not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting paper: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# GitHub Analysis Endpoints
# =============================================================================

@router.post("/api/github/analyze", tags=["github"])
async def analyze_github_repo(request: GitHubAnalysisRequest):
    """Analyze GitHub repository"""
    try:
        result = await github_analyzer.analyze_repository(
            repo_url=request.repo_url,
            extract_images=request.extract_images
        )

        return result

    except Exception as e:
        logger.error(f"Error analyzing GitHub repo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# RAG & Embeddings Endpoints
# =============================================================================

@router.get("/api/citations/{citation_id}/embeddings", tags=["rag"])
async def get_citation_embeddings(citation_id: str):
    """Get embeddings for a citation"""
    try:
        embeddings = db.get_embeddings(citation_id)

        return {
            "success": True,
            "citation_id": citation_id,
            "embeddings": [
                {
                    "chunk_index": e["chunk_index"],
                    "content_preview": e["content"][:200]
                }
                for e in embeddings
            ],
            "count": len(embeddings)
        }

    except Exception as e:
        logger.error(f"Error getting embeddings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/rag/search", tags=["rag"])
async def semantic_search(query: str, citation_ids: Optional[List[str]] = None, top_k: int = 5):
    """Perform semantic search across embeddings"""
    try:
        results = await rag_system.search_similar(
            query=query,
            citation_ids=citation_ids,
            top_k=top_k
        )

        return {
            "success": True,
            "query": query,
            "results": results,
            "count": len(results)
        }

    except Exception as e:
        logger.error(f"Error in semantic search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Collections Endpoints
# =============================================================================

@router.get("/api/citations/collections", tags=["collections"])
async def get_collections():
    """Get all collections"""
    try:
        cursor = db.conn.cursor()
        cursor.execute("""
        SELECT c.*, COUNT(cc.citation_id) as item_count
        FROM collections c
        LEFT JOIN citation_collections cc ON c.id = cc.collection_id
        GROUP BY c.id
        """)

        collections = [dict(row) for row in cursor.fetchall()]

        return {
            "success": True,
            "collections": collections,
            "count": len(collections)
        }

    except Exception as e:
        logger.error(f"Error getting collections: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Health Check
# =============================================================================

@router.get("/api/health", tags=["system"])
async def health_check():
    """System health check"""
    return {
        "status": "healthy",
        "database": "connected",
        "rag_system": "ready",
        "paper_pipeline": "ready"
    }
