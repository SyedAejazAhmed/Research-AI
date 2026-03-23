# Research AI Platform - Comprehensive Documentation

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Features](#features)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Usage Guide](#usage-guide)
7. [API Documentation](#api-documentation)
8. [Deployment](#deployment)
9. [Development](#development)
10. [Troubleshooting](#troubleshooting)

---

## Overview

The Research AI Platform is a complete AI-powered research assistant that automates the entire academic research workflow. It combines capabilities of Zotero (citation management), autonomous research engines, and LaTeX academic writing systems into a single integrated platform.

### Key Capabilities

- **Automated Research**: Query-based research with multi-source data gathering
- **Citation Management**: Zotero-like functionality with full citation lifecycle management
- **RAG System**: PDF processing with vector embeddings for semantic search
- **Academic Paper Generation**: Journal-ready LaTeX papers with IEEE, Springer, ACM templates
- **GitHub Analysis**: Repository analysis with image extraction and methodology detection
- **Multi-format Export**: PDF, DOCX, Markdown, BibTeX export
- **Local LLM Integration**: Direct Ollama integration for privacy-first processing

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────┐
│                   Frontend (React)                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │  Research   │  │  Citation   │  │   Paper     │ │
│  │  Dashboard  │  │  Library    │  │   Editor    │ │
│  └─────────────┘  └─────────────┘  └─────────────┘ │
└────────────────────┬────────────────────────────────┘
                     │ REST API / WebSocket
┌────────────────────┴────────────────────────────────┐
│              Backend (FastAPI + Python)              │
│  ┌─────────────────────────────────────────────┐   │
│  │         Research Orchestrator                │   │
│  └─────────────────────────────────────────────┘   │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │  Planner │ │ Research │ │    Synthesizer   │   │
│  │  Agent   │ │ Agents   │ │     Agent        │   │
│  └──────────┘ └──────────┘ └──────────────────┘   │
└─────────────────────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────┐
│           Enhanced Agent Layer                       │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │   RAG System │  │  LaTeX Agent │  │  GitHub   │ │
│  │  + Embeddings│  │  + Compiler  │  │  Analyzer │ │
│  └──────────────┘  └──────────────┘  └───────────┘ │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │   Citation   │  │   Ordered    │  │  Zotero   │ │
│  │   Memory     │  │   Reference  │  │   Agent   │ │
│  └──────────────┘  └──────────────┘  └───────────┘ │
└─────────────────────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────┐
│              Data & Services Layer                   │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │   SQLite DB  │  │    Ollama    │  │   Docker  │ │
│  │   + Vectors  │  │  (Local LLM) │  │   LaTeX   │ │
│  └──────────────┘  └──────────────┘  └───────────┘ │
└─────────────────────────────────────────────────────┘
```

### Technology Stack

**Frontend:**
- React 19
- Tailwind CSS v4
- Framer Motion
- Three.js/OGL for visualizations

**Backend:**
- Python 3.11+
- FastAPI
- SQLite/DuckDB
- Ollama (Local LLM)

**Agents & Processing:**
- LangChain/LangGraph
- Sentence Transformers (RAG)
- PyZotero (Citation management)
- Docker (LaTeX compilation)

---

## Features

### 1. Citation Management (Zotero-like)

#### Database Schema
- **Citations Table**: Stores full citation metadata
- **Collections**: Organize citations into collections
- **Embeddings**: Vector embeddings for semantic search
- **Reference Order**: Ordered references by paper section

#### Supported Citation Formats
- APA 7th Edition
- MLA 9th Edition
- IEEE
- Chicago
- Harvard
- Vancouver
- BibTeX

#### Citation Sources
- ArXiv
- PubMed
- Semantic Scholar
- Google Scholar
- DOI resolution
- Manual entry

### 2. RAG System for PDF Embeddings

#### PDF Processing Pipeline
1. **Text Extraction**: PyPDF2/pdfplumber
2. **Chunking**: Overlapping chunks (default: 512 chars)
3. **Embedding Generation**: SentenceTransformers (all-MiniLM-L6-v2)
4. **Storage**: Serialized vectors in SQLite
5. **Retrieval**: Cosine similarity search

#### Ordered Reference Activation
- References assigned to paper sections in order
- Embedding activation by reference sequence
- Context-aware retrieval per section

Example:
```
Introduction:
  - Reference 1 → Activates Embedding Set 1
  - Reference 2 → Activates Embedding Set 2
  - Reference 3 → Activates Embedding Set 3
```

### 3. Academic Paper Generation

#### LaTeX Templates
- **IEEE Conference**: Two-column format
- **Springer LNCS**: Lecture Notes in Computer Science
- **ACM**: ACM article format

#### Paper Structure
```
Title, Authors, Affiliation
Abstract
Keywords
1. Introduction
2. Literature Review
3. Methodology
4. Results and Discussion
5. Conclusion
References (BibTeX)
```

#### Generation Pipeline
1. Citation collection
2. PDF processing & embedding
3. Section-wise reference assignment
4. Content generation (LLM-assisted)
5. LaTeX rendering
6. Docker-based compilation
7. Multi-format export

### 4. GitHub Repository Analyzer

#### Extracted Information
- README content
- Repository structure
- File statistics
- Methodology sections
- Novelty/innovation descriptions
- Images (PNG, JPG, SVG) → saved to `outputs/images/`

#### Use Cases
- Include technical context in papers
- Analyze software methodologies
- Extract architecture diagrams
- Document innovation

### 5. Docker-Based LaTeX Compilation

#### Security Features
- Isolated Docker container
- No shell escape
- No network access
- Resource limits (CPU, memory)
- Deterministic TeX Live 2024

#### Compilation Process
```bash
# Build Docker image
docker build -t latex-compiler:latest -f Dockerfile .

# Compile paper
docker run --rm -v workspace:/work latex-compiler pdflatex paper.tex
```

---

## Installation

### Prerequisites

```bash
# System requirements
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Git
- 8GB+ RAM (16GB recommended for Ollama)
```

### Step 1: Clone Repository

```bash
git clone https://github.com/SyedAejazAhmed/Research-AI.git
cd Research-AI
```

### Step 2: Install Python Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Install Frontend Dependencies

```bash
cd frontend
npm install
npm run build
cd ..
```

### Step 4: Build LaTeX Docker Image

```bash
cd multi_agent/Latex_engine
docker build -t latex-compiler:latest .
cd ../..
```

### Step 5: Install Ollama

```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh

# macOS
brew install ollama

# Windows
# Download from https://ollama.com/download

# Pull models
ollama pull llama3.1:8b
ollama pull phi3
```

---

## Configuration

### Environment Variables

Create `.env` file in project root:

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

# Zotero (optional)
ZOTERO_LIBRARY_ID=your_library_id
ZOTERO_API_KEY=your_zotero_key
```

---

## Usage Guide

### Starting the Platform

#### Option 1: Docker Compose (Recommended)

```bash
docker-compose up -d
```

Access at: http://localhost:8000

#### Option 2: Manual Start

```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Start Backend
python backend/run.py

# Terminal 3: Start Frontend (if needed)
cd frontend && npm run dev
```

### Basic Workflow

#### 1. Add Citations

```python
# Via API
POST /api/citations
{
  "title": "Deep Learning for NLP",
  "authors": ["John Smith", "Jane Doe"],
  "year": 2024,
  "doi": "10.1234/example",
  "url": "https://arxiv.org/abs/2401.12345"
}
```

#### 2. Upload PDF for Embedding

```python
# Via API
POST /api/citations/upload-pdf/{citation_id}
# Upload PDF file

# System will:
# - Extract text
# - Generate chunks
# - Create embeddings
# - Store in database
```

#### 3. Generate Paper

```python
# Via API
POST /api/papers/generate
{
  "query": "Recent advances in deep learning for natural language processing",
  "citation_ids": ["cit1", "cit2", "cit3"],
  "template_type": "IEEE",
  "research_mode": "academic",
  "github_repo": "https://github.com/huggingface/transformers"  # Optional
}

# Returns:
{
  "success": true,
  "paper_id": "abc123",
  "files": {
    "tex": "path/to/paper.tex",
    "pdf": "path/to/paper.pdf",
    "bib": "path/to/references.bib",
    "markdown": "path/to/paper.md"
  }
}
```

---

## API Documentation

### Citation Endpoints

```
POST   /api/citations              Create citation
GET    /api/citations              Search citations
GET    /api/citations/{id}         Get citation by ID
POST   /api/citations/upload-pdf/{id}  Upload PDF
POST   /api/citations/export/bibtex    Export BibTeX
```

### Paper Generation Endpoints

```
POST   /api/papers/generate        Generate paper
GET    /api/papers/{id}            Get paper by ID
```

### RAG & Embeddings

```
GET    /api/citations/{id}/embeddings  Get embeddings
POST   /api/rag/search                 Semantic search
```

### GitHub Analysis

```
POST   /api/github/analyze         Analyze repository
```

---

## Deployment

### Production Deployment with Docker Compose

```bash
# Build and start all services
docker-compose -f docker-compose.yml up -d

# Services:
# - frontend (port 3000)
# - backend (port 8000)
# - ollama (port 11434)
# - latex-compiler
# - mcp-service (port 8001)
```

### Environment-Specific Configurations

#### Development
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

#### Production
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Scaling

```bash
# Scale backend workers
docker-compose up -d --scale backend=3

# Scale MCP service
docker-compose up -d --scale mcp-service=2
```

---

## Development

### Project Structure

```
Research-AI/
├── app/                    # Core application
│   ├── agents/            # Agent implementations
│   │   ├── rag_system.py
│   │   ├── latex_writing_agent.py
│   │   ├── github_analyzer.py
│   │   └── paper_pipeline.py
│   ├── database/          # Database layer
│   │   └── schema.py
│   └── utils/             # Utilities
│       └── security.py
├── frontend/               # React frontend
│   └── src/
│       └── components/
│           └── ZoteroCitationLibrary.jsx
├── multi_agent/           # Multi-agent system
│   ├── agents/            # LangGraph agents
│   └── Latex_engine/      # LaTeX compilation
│       ├── Dockerfile
│       └── templates/
├── server/                # FastAPI server
│   ├── server.py
│   └── api_routes.py
├── tests/                 # Test suite
├── docker-compose.yml     # Docker orchestration
└── requirements.txt       # Python dependencies
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_platform.py -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

### Adding New Features

1. Create agent in `app/agents/`
2. Add database schema if needed in `app/database/schema.py`
3. Add API routes in `server/api_routes.py`
4. Add frontend components in `frontend/src/components/`
5. Write tests in `tests/`
6. Update documentation

---

## Troubleshooting

### Common Issues

#### 1. Ollama Not Responding

```bash
# Check Ollama status
ollama list

# Restart Ollama
killall ollama
ollama serve

# Pull models again
ollama pull llama3.1:8b
```

#### 2. LaTeX Compilation Fails

```bash
# Rebuild Docker image
cd multi_agent/Latex_engine
docker build --no-cache -t latex-compiler:latest .

# Check Docker logs
docker logs <container_id>
```

#### 3. Database Locked

```bash
# If SQLite database is locked
rm research_ai.db
python -c "from app.database.schema import ResearchDatabase; ResearchDatabase()"
```

#### 4. Frontend Build Issues

```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run build
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python backend/run.py
```

---

## License

This project uses open-source components. Check individual licenses:
- FastAPI: MIT
- React: MIT
- Ollama: MIT
- TeX Live: Various open-source licenses
- SentenceTransformers: Apache 2.0

---

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

## Support

- **Documentation**: This file
- **Issues**: https://github.com/SyedAejazAhmed/Research-AI/issues
- **Discussions**: https://github.com/SyedAejazAhmed/Research-AI/discussions

---

**Built for Prince PROTOTHON'26 by Team Dart Vadar**
