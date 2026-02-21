"""
Yukti Research AI - LLM Client
================================
Handles communication with Ollama (local LLM) for privacy-first processing.
Supports chunk-based processing and citation-aware generation.
"""

import asyncio
import logging
import json
import os
import subprocess
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
        self.system_info = {}
        self.recommended_model = None
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system configuration (Windows specific falling back to generic)."""
        info = {"ram_gb": 8, "cores": 4, "os": os.name}
        try:
            if os.name == 'nt': # Windows
                # RAM
                cmd = "wmic computersystem get totalphysicalmemory"
                out = subprocess.check_output(cmd, shell=True).decode()
                mem = [line for line in out.splitlines() if line.strip() and "Total" not in line]
                if mem:
                    info["ram_gb"] = int(int(mem[0].strip()) / (1024**3))
                
                # CPU Cores
                cmd = "wmic cpu get NumberOfCores"
                out = subprocess.check_output(cmd, shell=True).decode()
                cores = [line for line in out.splitlines() if line.strip() and "Number" not in line]
                if cores:
                    info["cores"] = int(cores[0].strip())
            else: # Unix/Mac basic fallback
                import multiprocessing
                info["cores"] = multiprocessing.cpu_count()
                # Basic RAM fallback if needed
        except Exception as e:
            logger.warning(f"Failed to get detailed system info: {e}")
        
        self.system_info = info
        return info

    def _recommend_model(self) -> str:
        """Recommend model based on RAM."""
        ram = self.system_info.get("ram_gb", 8)
        
        if ram < 4:
            return "phi3:3.8b-mini-4k-instruct-q4_K_M" # Extremely light
        elif ram < 8:
            return "llama3.2:1b"
        elif ram < 14:
            return "llama3.2:3b"
        elif ram < 24:
            return "llama3.1:8b"
        else:
            return "gemma2:9b"

    async def initialize(self, auto_setup: bool = False) -> bool:
        """Initialize client and detect available models."""
        self._get_system_info()
        self.recommended_model = self._recommend_model()
        
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    self.available_models = [m["name"] for m in data.get("models", [])]
                    
                    # If model not set, use recommended or first available
                    if not self.model:
                        if self.recommended_model in self.available_models:
                            self.model = self.recommended_model
                        elif any(self.recommended_model in m for m in self.available_models):
                           # Match partial names
                           for m in self.available_models:
                               if self.recommended_model in m:
                                   self.model = m
                                   break
                        
                        if not self.model and self.available_models:
                            self.model = self.available_models[0]
                    
                    # Auto-setup if requested and model missing
                    if auto_setup and not self.model:
                        logger.info(f"Auto-pulling recommended model: {self.recommended_model}")
                        await self.pull_model(self.recommended_model)
                        self.model = self.recommended_model
                        # Re-initialize to get updated tags
                        return await self.initialize(auto_setup=False)

                    self._initialized = True
                    return True
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
        
        self._initialized = False
        return False

    async def pull_model(self, model_name: str, callback=None):
        """Pull a model from Ollama library."""
        try:
            import httpx
            logger.info(f"Pulling model: {model_name}")
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/pull",
                    json={"name": model_name, "stream": True}
                ) as resp:
                    async for line in resp.aiter_lines():
                        if line:
                            data = json.loads(line)
                            status = data.get("status", "")
                            digest = data.get("digest", "")
                            total = data.get("total", 0)
                            completed = data.get("completed", 0)
                            
                            if callback:
                                await callback(status, completed, total)
                            
                            if status == "success":
                                logger.info(f"Successfully pulled {model_name}")
                                break
        except Exception as e:
            logger.error(f"Failed to pull model {model_name}: {e}")
            raise
    
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
            "recommended": self.recommended_model,
            "system_info": self.system_info,
            "base_url": self.base_url
        }
