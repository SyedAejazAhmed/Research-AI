"""
MCP Interface Agent
===================

Provides Model Context Protocol (MCP) interface for research agents.
Enables external tools and systems to interact with the research system.
"""

import json
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
import asyncio

from .base import BaseAgent, AgentConfig, AgentResponse


class MCPToolType(Enum):
    """Types of MCP tools."""
    CITATION = "citation"
    RESEARCH = "research"
    LATEX = "latex"
    FORMATTING = "formatting"
    EXPORT = "export"


@dataclass
class MCPTool:
    """Definition of an MCP tool."""
    name: str
    description: str
    input_schema: Dict[str, Any] = None
    output_schema: Dict[str, Any] = None
    tool_type: MCPToolType = MCPToolType.RESEARCH
    parameters: Dict[str, Any] = None  # Legacy support
    required_params: List[str] = None  # Legacy support
    
    def __post_init__(self):
        # Support both old and new API
        if self.input_schema is None and self.parameters is not None:
            self.input_schema = self.parameters
        if self.input_schema is None:
            self.input_schema = {}
        if self.output_schema is None:
            self.output_schema = {}
        if self.required_params is None:
            self.required_params = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "type": self.tool_type.value if isinstance(self.tool_type, MCPToolType) else self.tool_type,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
        }


@dataclass
class MCPRequest:
    """An MCP request."""
    tool_name: str
    arguments: Dict[str, Any] = None
    request_id: Optional[str] = None
    parameters: Dict[str, Any] = None  # Legacy support
    
    def __post_init__(self):
        import uuid
        if self.request_id is None:
            self.request_id = f"req_{uuid.uuid4().hex[:8]}"
        # Support both arguments and parameters
        if self.arguments is None and self.parameters is not None:
            self.arguments = self.parameters
        if self.arguments is None:
            self.arguments = {}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPRequest":
        return cls(
            tool_name=data.get("tool_name", ""),
            arguments=data.get("arguments") or data.get("parameters", {}),
            request_id=data.get("request_id"),
        )


@dataclass
class MCPResponse:
    """An MCP response."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    request_id: Optional[str] = None
    result: Any = None  # Legacy support
    
    def __post_init__(self):
        # Support both data and result
        if self.data is None and self.result is not None:
            self.data = self.result
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "request_id": self.request_id,
        }


class MCPInterfaceAgent(BaseAgent):
    """
    Agent providing MCP (Model Context Protocol) interface.
    
    Exposes research capabilities as MCP tools:
    - Citation management (add, search, format)
    - Research operations (query, summarize)
    - LaTeX generation (template, compile)
    - Export (PDF, DOCX, Markdown)
    
    This agent acts as a bridge between external MCP clients
    and the internal research agent system.
    """
    
    def __init__(self, websocket=None, stream_output=None, headers=None):
        config = AgentConfig(name="MCPInterface", description="MCP protocol interface")
        super().__init__(websocket, stream_output, headers, config)
        
        self._tools: Dict[str, MCPTool] = {}
        self._handlers: Dict[str, Callable] = {}
        self._agents: Dict[str, BaseAgent] = {}
        self._register_builtin_tools()
    
    def _register_builtin_tools(self) -> None:
        """Register built-in MCP tools."""
        # Citation tools
        self.register_tool(MCPTool(
            name="citation_add",
            description="Add a new citation to the memory",
            tool_type=MCPToolType.CITATION,
            parameters={
                "title": {"type": "string", "description": "Citation title"},
                "authors": {"type": "array", "description": "List of authors"},
                "year": {"type": "integer", "description": "Publication year"},
                "source": {"type": "string", "description": "Journal/Conference name"},
                "doi": {"type": "string", "description": "DOI (optional)"},
                "url": {"type": "string", "description": "URL (optional)"},
            },
            required_params=["title", "authors", "year"],
        ))
        
        self.register_tool(MCPTool(
            name="citation_search",
            description="Search citations in memory",
            tool_type=MCPToolType.CITATION,
            parameters={
                "query": {"type": "string", "description": "Search query"},
                "author": {"type": "string", "description": "Filter by author"},
                "year": {"type": "integer", "description": "Filter by year"},
                "limit": {"type": "integer", "description": "Max results"},
            },
            required_params=[],
        ))
        
        self.register_tool(MCPTool(
            name="citation_format",
            description="Format a citation in a specific style",
            tool_type=MCPToolType.FORMATTING,
            parameters={
                "citation_id": {"type": "string", "description": "Citation ID"},
                "style": {"type": "string", "description": "Style: apa, mla, chicago, ieee, harvard, vancouver"},
            },
            required_params=["citation_id", "style"],
        ))
        
        self.register_tool(MCPTool(
            name="citation_import_bibtex",
            description="Import citations from BibTeX",
            tool_type=MCPToolType.CITATION,
            parameters={
                "bibtex": {"type": "string", "description": "BibTeX content"},
            },
            required_params=["bibtex"],
        ))
        
        self.register_tool(MCPTool(
            name="citation_export_bibtex",
            description="Export citations to BibTeX",
            tool_type=MCPToolType.EXPORT,
            parameters={
                "citation_ids": {"type": "array", "description": "IDs to export (optional, exports all if empty)"},
            },
            required_params=[],
        ))
        
        # LaTeX tools
        self.register_tool(MCPTool(
            name="latex_templates",
            description="List available LaTeX templates",
            tool_type=MCPToolType.LATEX,
            parameters={},
            required_params=[],
        ))
        
        self.register_tool(MCPTool(
            name="latex_fill_template",
            description="Fill a LaTeX template with variables",
            tool_type=MCPToolType.LATEX,
            parameters={
                "template": {"type": "string", "description": "Template name"},
                "variables": {"type": "object", "description": "Template variables"},
            },
            required_params=["template", "variables"],
        ))
        
        self.register_tool(MCPTool(
            name="latex_compile",
            description="Compile LaTeX to PDF",
            tool_type=MCPToolType.LATEX,
            parameters={
                "source": {"type": "string", "description": "LaTeX source code"},
                "output_name": {"type": "string", "description": "Output filename"},
                "engine": {"type": "string", "description": "Compiler: pdflatex, xelatex, lualatex"},
            },
            required_params=["source"],
        ))
        
        self.register_tool(MCPTool(
            name="markdown_to_latex",
            description="Convert Markdown to LaTeX",
            tool_type=MCPToolType.LATEX,
            parameters={
                "markdown": {"type": "string", "description": "Markdown content"},
            },
            required_params=["markdown"],
        ))
        
        # Research tools
        self.register_tool(MCPTool(
            name="research_query",
            description="Execute a research query",
            tool_type=MCPToolType.RESEARCH,
            parameters={
                "query": {"type": "string", "description": "Research query"},
                "report_type": {"type": "string", "description": "Report type"},
                "sources": {"type": "array", "description": "Source types to use"},
            },
            required_params=["query"],
        ))
        
        self.register_tool(MCPTool(
            name="generate_bibliography",
            description="Generate formatted bibliography",
            tool_type=MCPToolType.FORMATTING,
            parameters={
                "citation_ids": {"type": "array", "description": "Citation IDs"},
                "style": {"type": "string", "description": "Citation style"},
            },
            required_params=["style"],
        ))
    
    def register_tool(self, tool: MCPTool, handler: Callable = None) -> None:
        """Register an MCP tool with optional handler."""
        self._tools[tool.name] = tool
        if handler is not None:
            self._handlers[tool.name] = handler
    
    def register_handler(self, tool_name: str, handler: Callable) -> None:
        """Register a handler for a tool."""
        self._handlers[tool_name] = handler
    
    def register_agent(self, name: str, agent: BaseAgent) -> None:
        """Register an agent for tool execution."""
        self._agents[name] = agent
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools as dictionaries."""
        return [tool.to_dict() for tool in self._tools.values()]
    
    def list_tools(self) -> List[MCPTool]:
        """Get list of available tools as MCPTool objects."""
        return list(self._tools.values())
    
    def get_tool(self, name: str) -> Optional[MCPTool]:
        """Get a specific tool by name."""
        return self._tools.get(name)
    
    def validate_request(self, request: MCPRequest) -> tuple:
        """
        Validate an MCP request.
        
        Args:
            request: The request to validate
            
        Returns:
            Tuple of (is_valid: bool, errors: list)
        """
        errors = []
        
        if not request.tool_name:
            errors.append("Tool name is required")
            return False, errors
        
        tool = self._tools.get(request.tool_name)
        if tool is None:
            errors.append(f"Unknown tool: {request.tool_name}")
            return False, errors
        
        # Check required parameters from input_schema
        if tool.input_schema and "required" in tool.input_schema:
            for required in tool.input_schema["required"]:
                if required not in (request.arguments or {}):
                    errors.append(f"Missing required parameter: {required}")
        
        return len(errors) == 0, errors
    
    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        """Handle an MCP request."""
        tool = self._tools.get(request.tool_name)
        if not tool:
            return MCPResponse(
                success=False,
                error=f"Unknown tool: {request.tool_name}",
                request_id=request.request_id,
            )
        
        # Get arguments (supporting both arguments and parameters)
        args = request.arguments or request.parameters or {}
        
        # Check required parameters from input_schema
        if tool.input_schema and "required" in tool.input_schema:
            for required in tool.input_schema["required"]:
                if required not in args:
                    return MCPResponse(
                        success=False,
                        error=f"Missing required parameter: {required}",
                        request_id=request.request_id,
                    )
        
        # Also check legacy required_params
        if tool.required_params:
            for param in tool.required_params:
                if param not in args:
                    return MCPResponse(
                        success=False,
                        error=f"Missing required parameter: {param}",
                        request_id=request.request_id,
                    )
        
        # Execute handler or default agent-based execution
        try:
            if request.tool_name in self._handlers:
                result = await self._handlers[request.tool_name](args)
            else:
                result = await self._execute_tool(request.tool_name, args)
            
            return MCPResponse(
                success=True,
                data=result,
                request_id=request.request_id,
            )
        except Exception as e:
            return MCPResponse(
                success=False,
                error=str(e),
                request_id=request.request_id,
            )
    
    async def execute(self, request_or_operation = None, **kwargs) -> MCPResponse:
        """
        Execute an MCP request.
        
        Args:
            request_or_operation: MCPRequest object or operation string (for base class compatibility)
            **kwargs: Alternative way to pass tool_name and arguments
            
        Returns:
            MCPResponse with results or error
        """
        # Handle MCPRequest object
        if isinstance(request_or_operation, MCPRequest):
            return await self.handle_request(request_or_operation)
        
        # Handle string operations (base class compatibility)
        if isinstance(request_or_operation, str):
            # Create request from operation and kwargs
            request = MCPRequest(
                tool_name=request_or_operation,
                arguments=kwargs
            )
            return await self.handle_request(request)
        
        # Handle kwargs-only call
        if request_or_operation is None:
            request = MCPRequest(
                tool_name=kwargs.get("tool_name", ""),
                arguments=kwargs.get("arguments", {})
            )
            return await self.handle_request(request)
        
        # Unknown type
        return MCPResponse(
            success=False,
            error=f"Invalid request type: {type(request_or_operation)}",
        )
    
    async def _execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """Execute a tool using registered agents."""
        # Citation operations
        if tool_name == "citation_add":
            agent = self._agents.get("citation_memory")
            if agent:
                response = await agent.execute("add", **params)
                return response.data if response.success else {"error": response.error}
        
        elif tool_name == "citation_search":
            agent = self._agents.get("citation_memory")
            if agent:
                response = await agent.execute("search", **params)
                return response.data if response.success else {"error": response.error}
        
        elif tool_name == "citation_format":
            # Get citation from memory, then format
            memory_agent = self._agents.get("citation_memory")
            formatter_agent = self._agents.get("citation_formatter")
            if memory_agent and formatter_agent:
                cit_response = await memory_agent.execute("get", citation_id=params.get("citation_id"))
                if cit_response.success:
                    format_response = await formatter_agent.execute(
                        "format",
                        citation=cit_response.data,
                        style=params.get("style", "apa"),
                    )
                    return format_response.data if format_response.success else {"error": format_response.error}
                return {"error": cit_response.error}
        
        elif tool_name == "citation_import_bibtex":
            agent = self._agents.get("citation_memory")
            if agent:
                response = await agent.execute("import_bibtex", bibtex_content=params.get("bibtex"))
                return response.data if response.success else {"error": response.error}
        
        elif tool_name == "citation_export_bibtex":
            agent = self._agents.get("citation_memory")
            if agent:
                response = await agent.execute("export_bibtex", citation_ids=params.get("citation_ids"))
                return response.data if response.success else {"error": response.error}
        
        # LaTeX operations
        elif tool_name == "latex_templates":
            agent = self._agents.get("latex_template")
            if agent:
                response = await agent.execute("list")
                return response.data if response.success else {"error": response.error}
        
        elif tool_name == "latex_fill_template":
            agent = self._agents.get("latex_template")
            if agent:
                response = await agent.execute(
                    "fill",
                    name=params.get("template"),
                    variables=params.get("variables", {}),
                )
                return response.data if response.success else {"error": response.error}
        
        elif tool_name == "latex_compile":
            agent = self._agents.get("latex_compiler")
            if agent:
                response = await agent.execute("compile", **params)
                return response.data if response.success else {"error": response.error}
        
        elif tool_name == "markdown_to_latex":
            agent = self._agents.get("latex_writer")
            if agent:
                response = await agent.execute("markdown_to_latex", markdown=params.get("markdown"))
                return response.data if response.success else {"error": response.error}
        
        elif tool_name == "generate_bibliography":
            memory_agent = self._agents.get("citation_memory")
            formatter_agent = self._agents.get("citation_formatter")
            if memory_agent and formatter_agent:
                # Get all citations or specified ones
                citation_ids = params.get("citation_ids")
                if citation_ids:
                    citations = []
                    for cid in citation_ids:
                        resp = await memory_agent.execute("get", citation_id=cid)
                        if resp.success:
                            citations.append(resp.data)
                else:
                    resp = await memory_agent.execute("get_all")
                    citations = resp.data if resp.success else []
                
                # Format bibliography
                format_resp = await formatter_agent.execute(
                    "bibliography",
                    citations=citations,
                    style=params.get("style", "apa"),
                )
                return format_resp.data if format_resp.success else {"error": format_resp.error}
        
        return {"error": f"No handler for tool: {tool_name}"}
