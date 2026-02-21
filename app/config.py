"""
Yukti Research AI - Configuration
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
APP_DIR = BASE_DIR / "app"
STATIC_DIR = APP_DIR / "static"
TEMPLATES_DIR = APP_DIR / "templates"
OUTPUT_DIR = BASE_DIR / "outputs"
SESSIONS_DIR = BASE_DIR / "sessions"

# Create directories
OUTPUT_DIR.mkdir(exist_ok=True)
SESSIONS_DIR.mkdir(exist_ok=True)

# LLM Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:latest")
OLLAMA_FALLBACK_MODELS = ["llama3.2:latest", "llama3.1:latest", "llama3:latest", "mistral:latest", "gemma2:latest", "phi3:latest", "qwen2:latest"]

# API Configuration (all free/open)
ARXIV_MAX_RESULTS = int(os.getenv("ARXIV_MAX_RESULTS", "10"))
PUBMED_MAX_RESULTS = int(os.getenv("PUBMED_MAX_RESULTS", "10"))
SEMANTIC_SCHOLAR_MAX = int(os.getenv("SEMANTIC_SCHOLAR_MAX", "10"))

# Server Configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

# Research Configuration
MAX_CONCURRENT_AGENTS = int(os.getenv("MAX_CONCURRENT_AGENTS", "4"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "4000"))
MAX_REPORT_SECTIONS = int(os.getenv("MAX_REPORT_SECTIONS", "8"))
