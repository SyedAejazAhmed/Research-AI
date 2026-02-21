"""
Yukti Research AI - LLM Client
================================
Handles communication with Ollama (local LLM) for privacy-first processing.
Supports chunk-based processing and citation-aware generation.
"""

import asyncio
import logging
import json
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class OllamaClient:
    """
    Client for Ollama local LLM.
    Handles model detection, generation, and chunk-based processing.
    """
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = None):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.available_models = []
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize client and detect available models."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    self.available_models = [m["name"] for m in data.get("models", [])]
                    
                    if not self.model and self.available_models:
                        # Auto-select best model
                        preferred = ["llama3.2:latest", "llama3.1:latest", "llama3:latest", 
                                    "mistral:latest", "gemma2:latest", "phi3:latest", "qwen2:latest"]
                        for p in preferred:
                            if p in self.available_models:
                                self.model = p
                                break
                        if not self.model:
                            self.model = self.available_models[0]
                    
                    self._initialized = True
                    logger.info(f"Ollama initialized with model: {self.model}")
                    logger.info(f"Available models: {self.available_models}")
                    return True
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
        
        self._initialized = False
        return False
    
    async def generate(self, prompt: str, system: str = None, temperature: float = 0.3) -> str:
        """Generate text using Ollama."""
        if not self._initialized:
            await self.initialize()
        
        if not self._initialized:
            return self._fallback_response(prompt)
        
        try:
            import httpx
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": 4096
                }
            }
            
            if system:
                payload["system"] = system
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("response", "")
                else:
                    logger.error(f"Ollama error: {resp.status_code} - {resp.text}")
                    return self._fallback_response(prompt)
                    
        except Exception as e:
            logger.error(f"Ollama generation error: {e}")
            return self._fallback_response(prompt)
    
    async def generate_stream(self, prompt: str, system: str = None, callback=None) -> str:
        """Generate text using Ollama with streaming."""
        if not self._initialized:
            await self.initialize()
        
        if not self._initialized:
            result = self._fallback_response(prompt)
            if callback:
                await callback(result)
            return result
        
        try:
            import httpx
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 4096
                }
            }
            
            if system:
                payload["system"] = system
            
            full_response = ""
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=120.0
                ) as resp:
                    async for line in resp.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                token = data.get("response", "")
                                full_response += token
                                if callback and token:
                                    await callback(token)
                            except json.JSONDecodeError:
                                continue
            
            return full_response
            
        except Exception as e:
            logger.error(f"Ollama stream error: {e}")
            result = self._fallback_response(prompt)
            if callback:
                await callback(result)
            return result
    
    def _fallback_response(self, prompt: str) -> str:
        """Provide a fallback response when LLM is unavailable."""
        return (
            "Note: Local LLM (Ollama) is not currently available. "
            "The system has compiled the research data from academic sources "
            "without LLM synthesis. Please install Ollama and a model to "
            "enable AI-powered report synthesis.\n\n"
            "Install Ollama: https://ollama.com\n"
            "Then run: ollama pull llama3.2"
        )
    
    @property
    def is_available(self) -> bool:
        return self._initialized
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "available": self._initialized,
            "model": self.model,
            "models": self.available_models,
            "base_url": self.base_url
        }
