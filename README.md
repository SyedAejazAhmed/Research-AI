# 🧠 Yukti Research AI
> **"An Autonomous AI System for Logical & Verified Academic Research"**

Built for **Prince PROTOTHON'26** by Team **Dart Vadar**.

## 📑 Overview
Yukti Research AI is a state-of-the-art autonomous research agent designed to democratize access to verifiable academic knowledge. It uses a multi-agent orchestrated pipeline to plan, research, aggregate, synthesize, and publish high-quality research reports with real-time progress tracking and DOI-validated citations.

## 🚀 Core Pipeline
1.  **Planner Agent**: Breaks query into sub-questions and defines research scope.
2.  **Web Context Agent**: Gathers recent developments and general context.
3.  **Academic Research Agent**: Concurrently searches ArXiv, PubMed, and Semantic Scholar.
4.  **Document Processing Agent**: Ranks and filters sources for relevance and quality.
5.  **Metadata & Citation Agent**: Validates DOIs and formats citations (APA/IEEE/MLA).
6.  **Content Aggregator**: Unified dataset construction for LLM processing.
7.  **Synthesizer Agent**: Local LLM synthesis with source grounding (Privacy-first).
8.  **Publisher Agent**: Generates academic-grade reports in Markdown and HTML.

## 🛠️ Tech Stack
-   **Backend**: Python 3.11, FastAPI, WebSockets
-   **LLM Engine**: Ollama (Local LLM - Llama 3.2)
-   **Frontend**: Vanilla HTML5, CSS3 (Glassmorphism), JavaScript (ES6+)
-   **Data Sources**: ArXiv API, NCBI PubMed (eutils), Semantic Scholar API, DuckDuckGo
-   **Export Tools**: Markdown, Styled HTML, Native PDF, and IEEE LaTeX (IEEEtran)
-   **Team**: Dart Vadar - St. Joseph's College of Engineering

## 🏃 Getting Started

### Prerequisites
-   **Python 3.11+**
-   **Ollama** installed and running (`ollama serve`)
-   Download model: `ollama pull llama3.2`

### Installation & Run
1.  **Clone/Open** the project directory.
2.  **Run the startup script** (Windows):
    ```bash
    python run.py
    ```
3.  **Access the Dashboard**:
    Open [http://localhost:8000](http://localhost:8000) in your browser.

## ✨ Advanced Features
-   **Real-time Progress Tracker**: Watch each agent work in the sidebar with live updates over WebSockets.
-   **Privacy-First**: No data leaves your machine; all synthesis happens via your local Ollama instance.
-   **DOI Validation**: Automated verification of academic papers to reduce hallucinations.
-   **Interactive Chat**: Ask follow-up questions about the generated report using the built-in research assistant.
-   **Smart Caching**: Local disk caching for academic results to speed up repeated queries.

## 🏆 Project Highlights
-   **Uniqueness**: Multi-agent planning avoids "random" LLM answers by enforcing a logical step-by-step methodology.
-   **Impact**: Accelerates innovation by reducing research time from hours to minutes.
-   **Credibility**: Citations are derived exclusively from verified academic sources.

---
*Created with ❤️ for Prince PROTOTHON'26*
