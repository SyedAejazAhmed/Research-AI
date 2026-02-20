"""
Base Agent Classes
==================

Provides abstract base classes and common interfaces for all research agents.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum
import asyncio
import logging
from datetime import datetime
import uuid


class AgentStatus(Enum):
    """Agent execution status."""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentConfig:
    """Configuration for agents."""
    name: str = "BaseAgent"
    description: str = ""
    verbose: bool = False
    timeout: int = 300
    retry_count: int = 3
    retry_delay: float = 1.0
    websocket_stream: bool = True
    output_dir: str = "./outputs"
    temp_dir: str = "/tmp/research_agent"
    log_level: str = "INFO"
    extra_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResponse:
    """Standard response from agents."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    agent_name: str = ""
    execution_time: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata,
            "agent_name": self.agent_name,
            "execution_time": self.execution_time,
            "timestamp": self.timestamp,
        }


class BaseAgent(ABC):
    """
    Abstract base class for all research agents.
    
    All agents must implement the `execute` method.
    """
    
    def __init__(self, websocket=None, stream_output=None, headers=None, config: Optional[AgentConfig] = None):
        self.websocket = websocket
        self.stream_output = stream_output
        self.headers = headers or {}
        self.config = config or AgentConfig()
        self.agent_id = str(uuid.uuid4())
        self.status = AgentStatus.IDLE
        self.logger = logging.getLogger(f"agent.{self.config.name}")
        self._task_history: List[Dict[str, Any]] = []
    
    async def log_output(self, message: str, log_type: str = "logs", event: str = "info") -> None:
        """Stream output to websocket or print to console."""
        if self.websocket and self.stream_output:
            await self.stream_output(log_type, event, message, self.websocket)
        else:
            from .utils.views import print_agent_output
            print_agent_output(message, agent=self.config.name.upper())
    
    @abstractmethod
    async def execute(self, *args, **kwargs) -> AgentResponse:
        """Execute the agent's main task. Must be implemented by subclasses."""
        pass
    
    async def run(self, *args, **kwargs) -> AgentResponse:
        """Run the agent with lifecycle management."""
        start_time = asyncio.get_event_loop().time()
        self.status = AgentStatus.RUNNING
        
        try:
            response = await asyncio.wait_for(
                self.execute(*args, **kwargs),
                timeout=self.config.timeout
            )
            self.status = AgentStatus.COMPLETED if response.success else AgentStatus.FAILED
            response.execution_time = asyncio.get_event_loop().time() - start_time
            response.agent_name = self.config.name
            return response
            
        except asyncio.TimeoutError:
            self.status = AgentStatus.FAILED
            return AgentResponse(
                success=False,
                error=f"Timeout after {self.config.timeout}s",
                agent_name=self.config.name,
                execution_time=asyncio.get_event_loop().time() - start_time,
            )
        except Exception as e:
            self.status = AgentStatus.FAILED
            self.logger.exception(f"Agent execution failed: {e}")
            return AgentResponse(
                success=False,
                error=str(e),
                agent_name=self.config.name,
                execution_time=asyncio.get_event_loop().time() - start_time,
            )
    
    def get_status(self) -> AgentStatus:
        """Get current agent status."""
        return self.status
