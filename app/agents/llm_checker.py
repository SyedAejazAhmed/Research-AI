"""
LLM Checker Agent
==================
Cross-platform LLM availability detection and management.
Detects available LLMs (Ollama, GPT4All, etc.) and recommends models based on system capabilities.
"""

import asyncio
import httpx
import platform
import psutil
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SystemRequirements:
    """System requirements for LLMs"""
    ram_gb: int
    disk_gb: int
    gpu_required: bool = False


@dataclass
class LLMModel:
    """LLM Model information"""
    name: str
    provider: str
    size_gb: float
    requirements: SystemRequirements
    quality_score: int  # 1-10
    description: str


class LLMChecker:
    """
    Cross-platform LLM availability checker and recommender.

    Features:
    - Detects available LLM providers (Ollama, GPT4All, LlamaCPP)
    - Analyzes system resources (RAM, disk, GPU)
    - Recommends optimal models based on hardware
    - Auto-downloads recommended models
    - Validates model availability
    """

    OLLAMA_MODELS = [
        LLMModel("phi3:mini", "ollama", 2.3, SystemRequirements(4, 5), 7, "Fast, efficient, good for basic tasks"),
        LLMModel("llama3.2:3b", "ollama", 2.0, SystemRequirements(4, 5), 7, "Latest Llama 3.2, 3B parameters"),
        LLMModel("llama3.1:8b", "ollama", 4.7, SystemRequirements(8, 10), 9, "Excellent balance of quality and speed"),
        LLMModel("mistral:7b", "ollama", 4.1, SystemRequirements(8, 10), 8, "High-quality reasoning model"),
        LLMModel("mixtral:8x7b", "ollama", 26.0, SystemRequirements(32, 40), 10, "Best quality, requires high-end hardware"),
        LLMModel("gemma:7b", "ollama", 5.0, SystemRequirements(8, 10), 8, "Google's Gemma, high quality"),
        LLMModel("qwen2:7b", "ollama", 4.4, SystemRequirements(8, 10), 8, "Alibaba's Qwen2, multilingual"),
    ]

    def __init__(self, ollama_host: str = "http://localhost:11434"):
        self.ollama_host = ollama_host
        self.system_info = self._get_system_info()

    def _get_system_info(self) -> Dict:
        """Get system hardware information"""
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            # Try to detect GPU
            has_gpu = False
            gpu_info = []
            try:
                import GPUtil
                gpus = GPUtil.getGPUs()
                if gpus:
                    has_gpu = True
                    gpu_info = [{"name": gpu.name, "memory_mb": gpu.memoryTotal} for gpu in gpus]
            except ImportError:
                # GPUtil not available, check for NVIDIA
                try:
                    import subprocess
                    result = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                                          capture_output=True, text=True, timeout=2)
                    if result.returncode == 0 and result.stdout.strip():
                        has_gpu = True
                        gpu_info = [{"name": result.stdout.strip(), "memory_mb": "unknown"}]
                except:
                    pass

            return {
                "platform": platform.system(),
                "ram_gb": memory.total / (1024**3),
                "available_ram_gb": memory.available / (1024**3),
                "disk_gb": disk.free / (1024**3),
                "has_gpu": has_gpu,
                "gpu_info": gpu_info,
                "cpu_count": psutil.cpu_count(),
            }
        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            return {
                "platform": platform.system(),
                "ram_gb": 8,  # default assumption
                "available_ram_gb": 4,
                "disk_gb": 50,
                "has_gpu": False,
                "gpu_info": [],
                "cpu_count": 4,
            }

    async def check_ollama_available(self) -> bool:
        """Check if Ollama is running and accessible"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.ollama_host}/api/tags")
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            return False

    async def get_installed_models(self) -> List[str]:
        """Get list of installed Ollama models"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.ollama_host}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    return [model["name"] for model in data.get("models", [])]
        except Exception as e:
            logger.error(f"Error fetching installed models: {e}")
        return []

    def recommend_models(self, top_n: int = 3) -> List[LLMModel]:
        """
        Recommend optimal models based on system capabilities

        Args:
            top_n: Number of recommendations to return

        Returns:
            List of recommended LLMModel objects
        """
        ram_gb = self.system_info["ram_gb"]
        disk_gb = self.system_info["disk_gb"]
        has_gpu = self.system_info["has_gpu"]

        suitable_models = []

        for model in self.OLLAMA_MODELS:
            # Check if system meets requirements
            if (model.requirements.ram_gb <= ram_gb and
                model.requirements.disk_gb <= disk_gb):

                # Bonus for GPU if model benefits from it
                if has_gpu and model.requirements.gpu_required:
                    suitable_models.append((model, model.quality_score + 1))
                else:
                    suitable_models.append((model, model.quality_score))

        # Sort by quality score (descending)
        suitable_models.sort(key=lambda x: x[1], reverse=True)

        return [model for model, _ in suitable_models[:top_n]]

    async def download_model(self, model_name: str) -> bool:
        """
        Download a model using Ollama

        Args:
            model_name: Name of the model to download

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Downloading model: {model_name}")
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.ollama_host}/api/pull",
                    json={"name": model_name}
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Error downloading model {model_name}: {e}")
            return False

    async def ensure_model_available(self, preferred_model: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Ensure a suitable model is available, downloading if necessary

        Args:
            preferred_model: Preferred model name (optional)

        Returns:
            Tuple of (success, model_name)
        """
        # Check if Ollama is running
        if not await self.check_ollama_available():
            logger.error("Ollama is not running. Please start Ollama first.")
            return False, None

        # Get installed models
        installed = await self.get_installed_models()

        # If preferred model is installed, use it
        if preferred_model and any(preferred_model in m for m in installed):
            logger.info(f"Using preferred model: {preferred_model}")
            return True, preferred_model

        # If any model is installed, use the first one
        if installed:
            logger.info(f"Using installed model: {installed[0]}")
            return True, installed[0]

        # No models installed, recommend and download
        logger.info("No models installed. Recommending models...")
        recommended = self.recommend_models(top_n=1)

        if not recommended:
            logger.error("No suitable models found for your system")
            return False, None

        best_model = recommended[0]
        logger.info(f"Recommended model: {best_model.name} ({best_model.description})")
        logger.info(f"Downloading {best_model.name}...")

        success = await self.download_model(best_model.name)
        if success:
            logger.info(f"Successfully downloaded {best_model.name}")
            return True, best_model.name
        else:
            logger.error(f"Failed to download {best_model.name}")
            return False, None

    def print_system_report(self) -> str:
        """Generate a human-readable system capabilities report"""
        info = self.system_info
        report = [
            "=" * 60,
            "LLM SYSTEM CAPABILITIES REPORT",
            "=" * 60,
            f"Platform: {info['platform']}",
            f"CPU Cores: {info['cpu_count']}",
            f"Total RAM: {info['ram_gb']:.1f} GB",
            f"Available RAM: {info['available_ram_gb']:.1f} GB",
            f"Free Disk Space: {info['disk_gb']:.1f} GB",
            f"GPU Available: {'Yes' if info['has_gpu'] else 'No'}",
        ]

        if info['gpu_info']:
            report.append("\nGPU Details:")
            for gpu in info['gpu_info']:
                report.append(f"  - {gpu['name']}")

        report.extend([
            "\n" + "=" * 60,
            "RECOMMENDED MODELS",
            "=" * 60,
        ])

        recommended = self.recommend_models(top_n=3)
        for i, model in enumerate(recommended, 1):
            report.extend([
                f"\n{i}. {model.name}",
                f"   Size: {model.size_gb} GB",
                f"   Quality: {model.quality_score}/10",
                f"   Description: {model.description}",
                f"   Requirements: {model.requirements.ram_gb} GB RAM, {model.requirements.disk_gb} GB disk"
            ])

        report.append("=" * 60)
        return "\n".join(report)


async def main():
    """CLI interface for LLM checker"""
    print("🔍 LLM Checker - Cross-Platform LLM Availability Detection\n")

    checker = LLMChecker()

    # Print system report
    print(checker.print_system_report())

    # Check Ollama availability
    print("\n📡 Checking Ollama availability...")
    ollama_available = await checker.check_ollama_available()

    if ollama_available:
        print("✅ Ollama is running!")

        # Get installed models
        installed = await checker.get_installed_models()
        if installed:
            print(f"\n✅ Installed models ({len(installed)}):")
            for model in installed:
                print(f"  - {model}")
        else:
            print("\n⚠️ No models installed")

            # Offer to download recommended model
            recommended = checker.recommend_models(top_n=1)
            if recommended:
                print(f"\n💡 Recommended: {recommended[0].name}")
                response = input(f"Download {recommended[0].name}? (y/n): ")
                if response.lower() == 'y':
                    success = await checker.download_model(recommended[0].name)
                    if success:
                        print(f"✅ Successfully downloaded {recommended[0].name}")
                    else:
                        print(f"❌ Failed to download {recommended[0].name}")
    else:
        print("❌ Ollama is not running")
        print("\n💡 Installation instructions:")
        print("  - Linux: curl -fsSL https://ollama.com/install.sh | sh")
        print("  - macOS: brew install ollama")
        print("  - Windows: https://ollama.com/download")
        print("\nAfter installation, run: ollama serve")


if __name__ == "__main__":
    asyncio.run(main())
