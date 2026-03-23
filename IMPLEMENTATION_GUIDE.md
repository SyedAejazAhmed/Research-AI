# Research AI Platform - Complete Implementation Guide

## Overview

This is a production-ready, full-stack AI-powered research assistant platform that automates the entire academic research workflow. The system combines capabilities similar to Zotero, autonomous research engines, and LaTeX academic writing into a single integrated platform.

## Key Features Implemented

### 1. Modular Multi-Agent Architecture
- **Planner Agent**: Breaks research questions into subtopics
- **Research Agents**: Web and Academic research with verified sources
- **Synthesizer Agent**: LLM-powered content generation
- **Publisher Agent**: Multi-format export
- **GitHub Analyzer**: Repository analysis with image extraction
- **LaTeX Writing & Compiler Agents**: Journal-ready paper generation
- **Citation Memory Agent**: Zotero-like citation management
- **RAG System**: Vector embeddings for semantic search
- **Ordered Reference Agent**: Section-wise citation activation
- **LLM Checker Agent**: Cross-platform LLM detection and management

### 2. Persistent Citation Management (Zotero-like)
- Stores references using DOI, BibTeX, ArXiv ID, and metadata APIs
- Normalizes and deduplicates citation data
- Supports tagging and collections
- Exports in 7 formats: APA, MLA, IEEE, Harvard, Chicago, Vancouver, BibTeX
- SQLite/DuckDB database for scaling
- RAW and normalized metadata storage

### 3. RAG System with Ordered Embeddings
- PDF processing with text extraction
- Vector embeddings using SentenceTransformers (all-MiniLM-L6-v2)
- Section-wise reference activation:
  - Introduction refs 1-5 → activates embeddings 1-5
  - Literature Review refs 6-15 → activates embeddings 6-15
  - Methodology refs 16-22 → activates embeddings 16-22
  - Discussion refs 23-28 → activates embeddings 23-28
  - Conclusion refs 29-30 → activates embeddings 29-30
- Cosine similarity search within active section

### 4. Research Modes
- **Academic Mode**: ArXiv, PubMed, Semantic Scholar, Google Scholar with DOI validation
- **Normal Mode**: General web sources (articles, blogs, news)
- Source verification and credibility scoring

### 5. LaTeX Paper Generation
- Templates: IEEE (two-column), Springer LNCS, ACM formats
- Docker-based compilation with TeX Live 2024
- Security: No shell escape, no network access, resource limits
- Deterministic builds
- Complete paper structure: Title, Abstract, Intro, Lit Review, Methodology, Discussion, Conclusion, References

### 6. GitHub Repository Analyzer
- Extracts README, structure, methodology, novelty
- Downloads images (PNG, JPG, SVG) → saved to `outputs/images/`
- Analyzes architecture and technical context
- Integration into research papers

### 7. Multi-Format Export
- PDF via LaTeX compilation
- DOCX (Microsoft Word)
- Markdown
- BibTeX citation lists
- Citation export in all supported formats

### 8. Frontend (React 19 + Tailwind CSS v4)
- Research Dashboard with query submission
- Citation Library (Zotero-like interface)
- Paper Editor with LaTeX preview
- GitHub Analyzer interface
- Export panel
- Real-time WebSocket progress updates
- Glassmorphism UI with animations

### 9. Backend (FastAPI + Python)
- Asynchronous endpoints
- Pipeline orchestration
- WebSocket support
- Citation storage and retrieval
- LaTeX compilation triggers
- Parallel agent execution
- Caching and validation
- Security middleware

### 10. Production-Ready Features
- **Security**:
  - Rate limiting (per-minute and per-hour)
  - API key authentication
  - Input validation and sanitization
  - SQL injection prevention
  - XSS protection
  - File upload validation
  - Resource limits

- **Deployment**:
  - Docker containerization
  - Docker Compose orchestration
  - Frontend, backend, LaTeX, Ollama, MCP services
  - Health check endpoints
  - Environment configuration

- **Testing**:
  - Comprehensive integration tests
  - Database operation tests
  - Agent interaction tests
  - Security feature tests
  - End-to-end pipeline tests

### 11. Local LLM Integration (Ollama)
- Direct Ollama integration
- Cross-platform LLM detection
- Automatic model recommendation based on system resources
- Model download management
- Privacy-first processing

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Frontend (React 19)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │  Research   │  │  Citation   │  │   Paper     │     │
│  │  Dashboard  │  │  Library    │  │   Editor    │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└────────────────────┬────────────────────────────────────┘
                     │ REST API / WebSocket
┌────────────────────┴────────────────────────────────────┐
│         Backend (FastAPI + Security Middleware)          │
│  ┌───────────────────────────────────────────────────┐  │
│  │     Comprehensive Pipeline Orchestrator           │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────┐
│                 Enhanced Agent Layer                     │
│  ┌──────────────┐ ┌──────────────┐ ┌─────────────────┐ │
│  │  LLM Checker │ │   Ordered    │ │   RAG System    │ │
│  │    Agent     │ │  Reference   │ │  + Embeddings   │ │
│  │              │ │    Agent     │ │                 │ │
│  └──────────────┘ └──────────────┘ └─────────────────┘ │
│  ┌──────────────┐ ┌──────────────┐ ┌─────────────────┐ │
│  │ LaTeX Agent  │ │   GitHub     │ │   Citation      │ │
│  │ + Compiler   │ │   Analyzer   │ │   Memory        │ │
│  └──────────────┘ └──────────────┘ └─────────────────┘ │
└─────────────────────────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────┐
│              Data & Services Layer                       │
│  ┌──────────────┐ ┌──────────────┐ ┌─────────────────┐ │
│  │   SQLite DB  │ │    Ollama    │ │  Docker LaTeX   │ │
│  │  + Vectors   │ │ (Local LLM)  │ │   Compiler      │ │
│  └──────────────┘ └──────────────┘ └─────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## Installation & Setup

### Prerequisites

```bash
# Required
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Git
- 8GB+ RAM (16GB recommended for Ollama)
- 20GB+ disk space
```

### Quick Start

```bash
# 1. Clone repository
git clone https://github.com/SyedAejazAhmed/Research-AI.git
cd Research-AI

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Install frontend dependencies
cd frontend
npm install
npm run build
cd ..

# 4. Install Ollama (if not already installed)
# Linux
curl -fsSL https://ollama.com/install.sh | sh

# macOS
brew install ollama

# Windows: Download from https://ollama.com/download

# 5. Start Ollama and pull a model
ollama serve &
ollama pull llama3.1:8b

# 6. Start the platform
python server/run.py
```

Access the platform at: http://localhost:8000

### Docker Deployment (Recommended for Production)

```bash
# Build and start all services
docker-compose up -d

# Services will be available:
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:8000
# - Ollama: http://localhost:11434
# - MCP Service: http://localhost:8001
```

## Usage

### 1. Using the Pipeline Orchestrator

```python
from app.pipeline_orchestrator import ResearchPipelineOrchestrator

orchestrator = ResearchPipelineOrchestrator()

results = await orchestrator.run_full_pipeline(
    query="Recent advances in transformer models for NLP",
    research_mode="academic",
    template_type="IEEE",
    citation_style="IEEE",
    github_repo="https://github.com/huggingface/transformers",
    max_citations=30,
    export_formats=["pdf", "markdown", "bibtex"]
)
```

### 2. API Endpoints

#### Pipeline Execution
```bash
POST /api/pipeline/run
{
  "query": "Machine learning research",
  "research_mode": "academic",
  "template_type": "IEEE",
  "max_citations": 30,
  "github_repo": "https://github.com/user/repo"
}
```

#### Citation Management
```bash
# Create citation
POST /api/citations
{
  "title": "Deep Learning Paper",
  "authors": ["John Doe"],
  "year": 2024,
  "doi": "10.1234/example"
}

# Search citations
GET /api/citations?query=deep+learning&limit=50

# Upload PDF for RAG
POST /api/citations/{citation_id}/upload-pdf
```

#### Ordered References
```bash
# Assign references to sections
POST /api/references/assign
{
  "citation_ids": ["cit_001", "cit_002", ...],
  "mode": "auto"
}

# Activate section embeddings
GET /api/references/sections/introduction/activate

# Retrieve RAG context for section
POST /api/references/sections/methodology/retrieve
{
  "query": "neural networks",
  "top_k": 5
}
```

#### LLM Management
```bash
# Check system status
GET /api/system/status

# Get recommended models
GET /api/llm/models/recommended?top_n=5

# Download model
POST /api/llm/models/llama3.1:8b/download
```

## Testing

### Run Integration Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test suite
pytest tests/test_integration.py -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

### Manual Testing

```bash
# Test ordered reference agent
python app/agents/ordered_reference_agent.py

# Test LLM checker
python app/agents/llm_checker.py

# Test security features
python app/security.py

# Test pipeline orchestrator
python app/pipeline_orchestrator.py
```

## Configuration

### Environment Variables

Create `.env` file:

```env
# API Keys
TAVILY_API_KEY=your_tavily_key
GOOGLE_API_KEY=your_google_key
GITHUB_TOKEN=your_github_token

# Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# Database
DATABASE_PATH=research_ai.db

# Paths
OUTPUT_DIR=outputs
WORKSPACE_DIR=multi_agent/Latex_engine/workspace

# Security
MAX_UPLOAD_SIZE=52428800  # 50MB
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000

# Zotero (optional)
ZOTERO_LIBRARY_ID=your_library_id
ZOTERO_API_KEY=your_zotero_key
```

## Security Features

- **Rate Limiting**: 60 requests/minute, 1000 requests/hour
- **API Key Authentication**: Optional API key support
- **Input Validation**: Pydantic models with sanitization
- **SQL Injection Prevention**: Pattern detection and sanitization
- **XSS Protection**: HTML escaping and URL validation
- **File Upload Validation**: Type and size restrictions
- **Resource Limits**: Query length, citation count, file size
- **Docker Isolation**: LaTeX compilation in isolated containers
- **No Shell Escape**: Disabled in LaTeX compilation
- **CORS Protection**: Configurable allowed origins

## Performance & Scalability

- **Async I/O**: All agents use async/await
- **Parallel Execution**: Research agents run in parallel
- **Caching**: Citation metadata and embeddings cached
- **Database Indexing**: Optimized queries
- **Connection Pooling**: Database connections reused
- **Background Tasks**: Long-running tasks in background
- **Docker Scaling**: Can scale services independently

## Troubleshooting

### Ollama Not Running
```bash
# Check status
ollama list

# Restart
killall ollama
ollama serve

# Pull models
ollama pull llama3.1:8b
```

### LaTeX Compilation Fails
```bash
# Rebuild Docker image
cd multi_agent/Latex_engine
docker build --no-cache -t latex-compiler:latest .
```

### Database Issues
```bash
# Reset database
rm research_ai.db
python -c "from app.database.schema import ResearchDatabase; ResearchDatabase()"
```

### Frontend Build Issues
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run build
```

## Development

### Project Structure
```
Research-AI/
├── app/                    # Core application
│   ├── agents/            # All agent implementations
│   ├── database/          # Database layer
│   ├── utils/             # Utilities
│   ├── orchestrator.py    # Research orchestrator
│   ├── pipeline_orchestrator.py  # NEW: Complete pipeline
│   └── security.py        # NEW: Security features
├── server/                # FastAPI server
│   ├── server.py          # Main server
│   ├── api_routes.py      # Original routes
│   ├── enhanced_api_routes.py  # NEW: Enhanced routes
│   ├── run.py             # Startup script (cross-platform)
│   └── main.py            # Alternative startup
├── frontend/              # React 19 frontend
├── multi_agent/           # LangGraph agents
├── search_engine/         # Research retrieval
├── tests/                 # Test suite
│   ├── test_platform.py
│   ├── test_github_agent.py
│   └── test_integration.py  # NEW: Integration tests
├── docker-compose.yml     # Docker orchestration
└── requirements.txt       # Python dependencies
```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Contributing

1. Fork the repository
2. Create feature branch
3. Write tests for new features
4. Ensure all tests pass
5. Submit pull request

## License

This project uses open-source components:
- FastAPI: MIT
- React: MIT
- Ollama: MIT
- TeX Live: Various open-source licenses
- SentenceTransformers: Apache 2.0

## Support

- Issues: https://github.com/SyedAejazAhmed/Research-AI/issues
- Discussions: https://github.com/SyedAejazAhmed/Research-AI/discussions
- Documentation: DEPLOYMENT_GUIDE.md

## Recent Updates (Latest Commit)

### ✨ New Features Added

1. **LLM Checker Agent**
   - Cross-platform LLM detection (Ollama, GPT4All)
   - System resource analysis (RAM, disk, GPU)
   - Automatic model recommendation
   - Model download management

2. **Ordered Reference Agent**
   - Section-wise citation activation
   - Automatic reference distribution
   - RAG retrieval per section
   - LaTeX bibliography generation

3. **Comprehensive Pipeline Orchestrator**
   - End-to-end workflow automation
   - 10-stage pipeline execution
   - Session management
   - Multi-format export

4. **Production Security**
   - Rate limiting middleware
   - API key authentication
   - Input validation (Pydantic)
   - SQL injection prevention
   - XSS protection
   - File upload validation

5. **Enhanced API Routes**
   - `/api/pipeline/*` - Pipeline endpoints
   - `/api/references/*` - Reference management
   - `/api/llm/*` - LLM management
   - `/api/security/*` - Security endpoints

6. **Integration Tests**
   - Database operations
   - Agent interactions
   - Security features
   - Pipeline execution

7. **Cross-Platform Support**
   - Fixed `server/run.py` for Linux/Windows/macOS
   - Platform-specific npm commands
   - System detection

---

**Built for Prince PROTOTHON'26 by Team Dart Vadar**

**Status**: Production-Ready ✅
