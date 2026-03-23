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

import httpx

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
        self._http_client = None  # persistent client, created on first use

    def _get_http_client(self):
        """Return (or lazily create) a shared httpx.AsyncClient."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=120.0)
        return self._http_client
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system configuration (cross-platform)."""
        import multiprocessing
        import shutil
        info = {
            "ram_gb": 8,
            "available_ram_gb": 4,
            "disk_free_gb": None,
            "cores": multiprocessing.cpu_count(),
            "os": os.name,
            "has_gpu": False,
        }
        try:
            if os.name == 'nt':  # Windows
                cmd = "wmic computersystem get totalphysicalmemory"
                out = subprocess.check_output(cmd, shell=True).decode()
                mem = [line for line in out.splitlines() if line.strip() and "Total" not in line]
                if mem:
                    info["ram_gb"] = int(int(mem[0].strip()) / (1024**3))
                try:
                    avail_out = subprocess.check_output(
                        "wmic OS get FreePhysicalMemory", shell=True
                    ).decode()
                    avail_mem = [ln for ln in avail_out.splitlines() if ln.strip() and "Free" not in ln]
                    if avail_mem:
                        info["available_ram_gb"] = round(int(avail_mem[0].strip()) / (1024**2), 1)
                except Exception:
                    pass
            else:
                # Linux / macOS
                with open("/proc/meminfo") as f:
                    for line in f:
                        if line.startswith("MemTotal"):
                            kb = int(line.split()[1])
                            info["ram_gb"] = round(kb / (1024**2))
                        elif line.startswith("MemAvailable"):
                            kb = int(line.split()[1])
                            info["available_ram_gb"] = round(kb / (1024**2), 1)

            # Free disk space
            disk = shutil.disk_usage("/")
            info["disk_free_gb"] = round(disk.free / (1024**3), 1)

            # GPU detection (NVIDIA via nvidia-smi)
            try:
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                    capture_output=True, text=True, timeout=2,
                )
                if result.returncode == 0 and result.stdout.strip():
                    info["has_gpu"] = True
            except Exception:
                pass

        except Exception as e:
            logger.warning(f"Failed to get detailed system info: {e}")

        self.system_info = info
        return info

    def _recommend_model(self) -> str:
        """Recommend model based on available models and RAM."""
        # Prefer gpt-oss:20b if available
        preferred = "gpt-oss:20b"
        if preferred in self.available_models:
            return preferred
        # Partial match (e.g. "gpt-oss:20b-..." variants)
        for m in self.available_models:
            if "gpt-oss" in m:
                return m

        ram = self.system_info.get("ram_gb", 8)
        if ram < 4:
            return "phi3:3.8b-mini-4k-instruct-q4_K_M"
        elif ram < 8:
            return "llama3.2:1b"
        elif ram < 14:
            return "llama3.2:3b"
        elif ram < 24:
            return "llama3.1:8b"
        else:
            return "gpt-oss:20b"

    async def initialize(self, auto_setup: bool = False) -> bool:
        """Initialize client and detect available models."""
        self._get_system_info()
        self.recommended_model = self._recommend_model()
        
        try:
            client = self._get_http_client()
            resp = await client.get(f"{self.base_url}/api/tags", timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                self.available_models = [m["name"] for m in data.get("models", [])]

                # Re-evaluate recommendation now that we know what's available
                self.recommended_model = self._recommend_model()

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
    
    async def generate(self, prompt: str, system: str = None, temperature: float = 0.3, max_tokens: int = 600) -> str:
        """Generate text using Ollama."""
        if not self._initialized:
            await self.initialize()
        
        if not self._initialized:
            return self._fallback_response(prompt)
        
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }
            
            if system:
                payload["system"] = system
            
            client = self._get_http_client()
            resp = await client.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=300.0
            )
            
            if resp.status_code == 200:
                data = resp.json()
                return data.get("response", "")
            else:
                logger.error(f"Ollama error: {resp.status_code} - {resp.text}")
                return self._fallback_response(prompt)
                
        except httpx.TimeoutException as e:
            logger.error(f"Ollama generation timeout ({type(e).__name__}) — model may be busy")
            return self._fallback_response(prompt)
        except Exception as e:
            logger.error(f"Ollama generation error ({type(e).__name__}): {e or repr(e)}")
            return self._fallback_response(prompt)
    
    async def generate_stream(self, prompt: str, system: str = None, callback=None, max_tokens: int = 600) -> str:
        """Generate text using Ollama with streaming."""
        if not self._initialized:
            await self.initialize()
        
        if not self._initialized:
            result = self._fallback_response(prompt)
            if callback:
                await callback(result)
            return result
        
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": 0.3,
                    "num_predict": max_tokens
                }
            }
            
            if system:
                payload["system"] = system
            
            full_response = ""
            
            client = self._get_http_client()
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
            "Then run: ollama pull gpt-oss:20b"
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
