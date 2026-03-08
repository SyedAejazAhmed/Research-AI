# 🧠 Yukti Research AI
> **"An Autonomous AI System for Logical & Verified Academic Research"**

Built for **Prince PROTOTHON'26** by Team **Dart Vadar**.

---

## 📑 Overview
Yukti Research AI is a state-of-the-art autonomous research agent designed to democratize access to verifiable academic knowledge. It uses a multi-agent orchestrated pipeline to plan, research, aggregate, synthesize, and publish high-quality research reports with real-time progress tracking and DOI-validated citations.

## ✨ Premium Features (V4.5)

### 🎨 Academic-Futuristic Aesthetics
- **Cinematic Visuals**: Immersive global backgrounds powered by vanilla WebGL shaders (**DarkVeil** & **PixelSnow**) using `ogl` and `three.js`.
- **Neural Branding**: Dynamic animated text gradients that pulse with the platform's state.
- **Glassmorphism UI**: High-fidelity interface using depth gradients and frosted glass effects for a professional academic feel.
- **Interactive Onboarding**: A multi-step stepper powered by **Framer Motion** to guide scholars through the platform's core mechanisms.

### 🧭 Advanced Research Capabilities
- **Multi-Format Citations**: Professional support for 6 citation formats: **APA 7th, MLA 9th, Chicago, Harvard, IEEE, and Vancouver**.
- **Deep Research Engine**: Conducts in-depth web and academic searches using **20+ verified sources** (ArXiv, PubMed, Semantic Scholar, etc.).
- **LangGraph Orchestration**: A stateful multi-agent system (Chief Editor, Researcher, Reviewer, Writer) ensuring high-quality, peer-reviewed outputs.
- **MCP Server Integration**: Machine Conversation Protocol support for deep research and real-time citation generation.

### 🛡️ Security & Privacy
- **Auth-First Architecture**: Mandatory secure authentication (Auth Vault) before entering the research cockpit.
- **Privacy-First Processing**: 100% of the report synthesis happens on your local machine via Ollama.

### ⚙️ Hardware-Aware Optimization
- **Neural Diagnostic Engine**: Automatically detects system RAM and CPU cores to recommend the optimal AI model.
- **Zero-Config Setup**: One-click "Ignite Optimization" to automatically pull and install the recommended Ollama models.

## 🏗️ Project Architecture

The system is composed of several specialized modules:

- **`app/`**: The core FastAPI backend orchestrating the primary research pipeline.
- **`frontend/`**: A modern React 19 SPA with Tailwind CSS v4 and Framer Motion.
- **`multi_agent/`**: LangGraph-powered research team (Chief Editor, Editor, Researcher, Reviewer, Revisor, Writer, Publisher).
- **`mcp_service/`**: Specialized MCP server for deep research and citation formatting.
- **`search_engine/`**: Advanced retriever and scraper engine with support for ArXiv, Bing, Google, PubMed, and more.
- **`repo_analyzer/`**: Integrated tools for repository handling, code summarization, and structure generation.

## 🛠️ Tech Stack
-   **Backend**: Python 3.11, FastAPI, WebSockets, LangGraph
-   **LLM Engine**: Ollama (Local - Scalable from Phi-3 to Llama 3.1 8B)
-   **Frontend**: React 19, Tailwind CSS v4, Framer Motion, Three.js, OGL
-   **Citation Engine**: Multi-source DOI validation & Formatting (6 Standards)
-   **Team**: Dart Vadar - St. Joseph's College of Engineering

## 🏃 Getting Started

### Prerequisites
-   **Python 3.11+**
-   **Node.js & npm** (for frontend)
-   **Ollama** installed and running (`ollama serve`)

### Installation & Run
1.  **Clone the repository**.
2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    cd frontend && npm install
    ```
3.  **Setup Environment Variables**:
    Create a `.env` file with necessary keys (Tavily, Google Search, etc. - see `search_engine/config/`).
4.  **Run the startup script**:
    ```bash
    python run.py
    ```
5.  **Access the Dashboard**:
    Open [http://localhost:8000](http://localhost:8000).

## 🏆 Project Highlights
-   **Logical Methodologies**: Inspired by the STORM paper, our multi-agent pipeline avoids "random" LLM answers by enforcing structured planning and peer-review.
-   **High Credibility**: Citations are derived exclusively from verified academic sources and processed through a **Hallucination Shield**.
-   **Modern UX**: Combines deep technical research with a cinematic, high-performance UI.

---
*Created with ❤️ for Prince PROTOTHON'26*
