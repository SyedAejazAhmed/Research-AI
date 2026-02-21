---
description: How to run the Yukti Research AI system
---

# Yukti Research AI Workflow

An autonomous AI system for logical & verified academic research.

## Prerequisites
1. **Python 3.11+** installed
2. **Ollama** installed (https://ollama.com)
3. Run `ollama pull llama3.2` to get the default model

## Steps to Run
// turbo
1. Open a terminal in the project directory.
2. Run the startup script:
   ```bash
   python run.py
   ```
3. Open your browser and navigate to:
   [http://localhost:8000](http://localhost:8000)

## Features
- Enter a research topic and watch 9 agents work in parallel.
- View real-time progress of ArXiv, PubMed, and Semantic Scholar searches.
- Download verified academic reports in Markdown or HTML.
- Chat with your research report for follow-up questions.
