"""
Multi-Agents Package
====================

Research agents for the GPT Researcher system.

Core Agents:
- ChiefEditorAgent: Master orchestrator
- ResearchAgent: Conducts research
- WriterAgent: Writes content
- EditorAgent: Plans and edits research
- PublisherAgent: Publishes to various formats
- ReviewerAgent: Reviews content
- ReviserAgent: Revises content
- HumanAgent: Human-in-the-loop

Citation Agents:
- CitationMemoryAgent: Citation storage and retrieval
- CitationFormatterAgent: Citation formatting (APA, MLA, etc.)

LaTeX Agents:
- LaTeXTemplateAgent: LaTeX template management
- LaTeXWriterAgent: LaTeX document writing
- LaTeXCompilerAgent: LaTeX to PDF compilation

Interface Agents:
- ResearchOrchestratorAgent: Enhanced research workflow
- MCPInterfaceAgent: Model Context Protocol interface

Base Classes:
- BaseAgent: Abstract base class
- AgentConfig: Agent configuration
- AgentResponse: Standard response
"""

# Base classes
from .base import BaseAgent, AgentConfig, AgentResponse, AgentStatus

# Core research agents
from .researcher import ResearchAgent
from .writer import WriterAgent
from .publisher import PublisherAgent
from .reviser import ReviserAgent
from .reviewer import ReviewerAgent
from .editor import EditorAgent
from .human import HumanAgent

# Citation agents
from .citation_memory import CitationMemoryAgent, Citation
from .citation_formatter import CitationFormatterAgent, CitationStyle

# LaTeX agents
from .latex_template import LaTeXTemplateAgent, LaTeXTemplate, TemplateType
from .latex_writer import LaTeXWriterAgent, LaTeXDocument, LaTeXSection
from .latex_compiler import LaTeXCompilerAgent, CompilerEngine, CompilationResult

# Interface agents
from .mcp_interface import MCPInterfaceAgent, MCPTool, MCPRequest, MCPResponse

# Orchestrators (import last as they depend on other agents)
from .orchestrator import ChiefEditorAgent
from .research_orchestrator import ResearchOrchestratorAgent

# Zotero integration
from .zotero_integration import (
    ZoteroIntegrationAgent,
    ZoteroConfig,
    ZoteroLibraryType,
    ZoteroItem,
    ZoteroCollection,
    ZoteroItemType,
    create_zotero_agent,
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
    
    # Zotero integration
    "ZoteroIntegrationAgent",
    "ZoteroConfig",
    "ZoteroLibraryType",
    "ZoteroItem",
    "ZoteroCollection",
    "ZoteroItemType",
    "create_zotero_agent",
]
