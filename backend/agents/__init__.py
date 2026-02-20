"""
Backend Agents Package
======================

This package provides a clean import interface for all research agents.
All agent implementations reside in multi_agents.agents.

Usage in backend code:
    from backend.agents import (
        ChiefEditorAgent,
        ResearchAgent,
        CitationMemoryAgent,
        LaTeXCompilerAgent,
        # ... etc
    )

This structure keeps:
- Agent implementations in: multi_agents/agents/
- Backend server integration in: backend/
- Clean imports for both internal and external use
"""

# Import all agents from multi_agents.agents
from multi_agents.agents import (
    # Base classes
    BaseAgent,
    AgentConfig,
    AgentResponse,
    AgentStatus,
    
    # Core research agents
    ChiefEditorAgent,
    ResearchAgent,
    WriterAgent,
    EditorAgent,
    PublisherAgent,
    ReviserAgent,
    ReviewerAgent,
    HumanAgent,
    
    # Citation agents
    CitationMemoryAgent,
    Citation,
    CitationFormatterAgent,
    CitationStyle,
    
    # LaTeX agents
    LaTeXTemplateAgent,
    LaTeXTemplate,
    TemplateType,
    LaTeXWriterAgent,
    LaTeXDocument,
    LaTeXSection,
    LaTeXCompilerAgent,
    CompilerEngine,
    CompilationResult,
    
    # Interface agents
    MCPInterfaceAgent,
    MCPTool,
    MCPRequest,
    MCPResponse,
    
    # Orchestrators
    ResearchOrchestratorAgent,
)

__all__ = [
    # Base
    "BaseAgent",
    "AgentConfig",
    "AgentResponse",
    "AgentStatus",
    
    # Core agents
    "ChiefEditorAgent",
    "ResearchAgent",
    "WriterAgent",
    "EditorAgent",
    "PublisherAgent",
    "ReviserAgent",
    "ReviewerAgent",
    "HumanAgent",
    
    # Citation agents
    "CitationMemoryAgent",
    "Citation",
    "CitationFormatterAgent",
    "CitationStyle",
    
    # LaTeX agents
    "LaTeXTemplateAgent",
    "LaTeXTemplate",
    "TemplateType",
    "LaTeXWriterAgent",
    "LaTeXDocument",
    "LaTeXSection",
    "LaTeXCompilerAgent",
    "CompilerEngine",
    "CompilationResult",
    
    # Interface agents
    "MCPInterfaceAgent",
    "MCPTool",
    "MCPRequest",
    "MCPResponse",
    
    # Orchestrators
    "ResearchOrchestratorAgent",
]
