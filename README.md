# 🧠 Yukti Research AI
> **"An Autonomous AI System for Logical & Verified Academic Research"**

Built for **Prince PROTOTHON'26** by Team **Dart Vadar**.

---

## 📑 Overview
Yukti Research AI is a state-of-the-art autonomous research agent designed to democratize access to verifiable academic knowledge. It uses a multi-agent orchestrated pipeline to plan, research, aggregate, synthesize, and publish high-quality research reports with real-time progress tracking and DOI-validated citations.

## ✨ Premium Features (V4.5)

### 🎨 Academic-Futuristic Aesthetics
- **Cinematic Visuals**: Immersive global backgrounds powered by vanilla WebGL shaders (**DarkVeil** & **PixelSnow**).
- **Neural Branding**: Dynamic animated text gradients that pulse with the platform's state.
- **Glassmorphism UI**: High-fidelity interface using depth gradients and frosted glass effects for a professional academic feel.

### 🧭 High-Fidelity Onboarding
- **Guided Cognitive Initialization**: A multi-step onboarding stepper (powered by Framer Motion) that illuminates the platform's core mechanisms for new scholars.

### 🛡️ Security & Privacy
- **Auth-First Architecture**: Mandatory secure authentication (Auth Vault) before entering the research cockpit.
- **Privacy-First Processing**: 100% of the report synthesis happens on your local machine via Ollama.

### ⚙️ Hardware-Aware Optimization
- **Neural Diagnostic Engine**: Automatically detects system RAM and CPU cores to recommend the optimal AI model.
- **Zero-Config Setup**: One-click "Ignite Optimization" to automatically pull and install the recommended Ollama models.

## 🚀 Core Pipeline
1.  **Planner Agent**: Breaks query into sub-questions and defines research scope.
2.  **Web Context Agent**: Gathers recent developments and general context.
3.  **Academic Research Agent**: Concurrently searches ArXiv, PubMed, and Semantic Scholar.
4.  **Document Processing Agent**: Ranks and filters sources for relevance and quality.
5.  **Metadata & Citation Agent**: Validates DOIs and formats citations (APA/IEEE/MLA).
6.  **Content Aggregator**: Unified dataset construction for LLM processing.
7.  **Synthesizer Agent**: Local LLM synthesis with source grounding.
8.  **Publisher Agent**: Generates academic-grade reports (MD, HTML, PDF, LaTeX).

## 🛠️ Tech Stack
-   **Backend**: Python 3.11, FastAPI, WebSockets
-   **LLM Engine**: Ollama (Local - Scalable from Phi-3 to Llama 3.1 8B)
-   **Frontend**: React 19, Tailwind CSS v4, Framer Motion, Vanilla WebGL
-   **Team**: Dart Vadar - St. Joseph's College of Engineering

## 🏃 Getting Started

### Prerequisites
-   **Python 3.11+**
-   **Ollama** installed and running (`ollama serve`)

### Installation & Run
1.  **Clone/Open** the project directory.
2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    cd frontend && npm install
    ```
3.  **Run the startup script**:
    ```bash
    python run.py
    ```
4.  **Access the Dashboard**:
    Open [http://localhost:8000](http://localhost:8000).

## 🏆 Project Highlights
-   **Uniqueness**: Multi-agent planning avoids "random" LLM answers by enforcing a logical step-by-step methodology.
-   **Impact**: Accelerated innovation by reducing research time from hours to minutes.
-   **Credibility**: Citations are derived exclusively from verified DOI academic sources and processed through a **Hallucination Shield**.

---
*Created with ❤️ for Prince PROTOTHON'26*
