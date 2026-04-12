"""
Yukti Research AI - Startup Script
===================================
Installs dependencies and starts the FastAPI server.
"""

import subprocess
import sys
import os
import shutil
import time
import asyncio
from pathlib import Path

# ── Resolve project root (one level above this script) ────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(PROJECT_ROOT)                      # ensure all relative paths resolve correctly
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))   # make project packages importable

OLLAMA_URL = "http://localhost:11434/api/tags"

def run_command(command, cwd=None):
    print(f"Executing: {' '.join(command)}")
    try:
        subprocess.check_call(command, cwd=cwd)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
        return False


def run_quiet(command, cwd=None):
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def npm_command(*args):
    if os.name == "nt":
        return ["cmd", "/c", "npm", *args]
    return ["npm", *args]


async def _check_ollama_health() -> bool:
    try:
        import httpx
    except ImportError:
        return False

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(OLLAMA_URL)
            return resp.status_code == 200
    except Exception:
        return False


def is_ollama_running() -> bool:
    return asyncio.run(_check_ollama_health())


def _try_start_ollama_service() -> None:
    if not shutil.which("systemctl"):
        return

    # Try user service first, then system service.
    run_quiet(["systemctl", "--user", "start", "ollama"])
    run_quiet(["systemctl", "start", "ollama"])


def _start_ollama_serve_background():
    ollama_bin = shutil.which("ollama")
    if not ollama_bin:
        return None

    kwargs = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        kwargs["start_new_session"] = True

    try:
        return subprocess.Popen([ollama_bin, "serve"], **kwargs)
    except Exception:
        return None


def ensure_ollama_running(auto_start=True, timeout_seconds=20):
    print("🧪 Checking for Ollama...")

    if is_ollama_running():
        print("✅ Ollama is running.")
        return True

    print(f"⚠️ Ollama is NOT running or unreachable at {OLLAMA_URL}")
    if not auto_start:
        print("💡 Auto-start disabled. Start Ollama manually to enable AI synthesis.")
        return False

    if not shutil.which("ollama"):
        print("❌ Ollama executable not found in PATH. Please install Ollama.")
        return False

    print("🔄 Attempting to start Ollama automatically...")
    _try_start_ollama_service()

    process = None
    if not is_ollama_running():
        process = _start_ollama_serve_background()

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if is_ollama_running():
            print("✅ Ollama started successfully.")
            return True
        time.sleep(1)

    if process and process.poll() is not None:
        print(f"⚠️ 'ollama serve' exited with code {process.returncode}.")

    print("⚠️ Could not auto-start Ollama within timeout. Continuing without it.")
    return False

def main():
    print("🚀 Initializing Yukti Research AI...")
    
    # Check for virtual environment
    if not os.environ.get('VIRTUAL_ENV'):
        print("💡 Hint: You are not running in a virtual environment. It's recommended to use one.")
    
    # Install requirements
    print("📦 Checking dependencies...")
    if not run_command([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]):
        print("❌ Failed to install dependencies.")
        return

    # Check and optionally auto-start Ollama.
    ollama_auto_start = "--no-ollama-autostart" not in sys.argv
    ensure_ollama_running(auto_start=ollama_auto_start)

    # Build Frontend if needed
    frontend_dir = Path("frontend")
    if frontend_dir.exists():
        print("🎨 Building advanced React frontend...")
        frontend_dist = frontend_dir / "dist"
        if not frontend_dist.exists() or "--rebuild" in sys.argv:
            print("📦 Installing frontend dependencies...")
            run_command(npm_command("install"), cwd="frontend")
            print("🏗️ Running build...")
            run_command(npm_command("run", "build"), cwd="frontend")
            print("✅ Frontend built successfully.")
        else:
            print("✨ Using existing frontend build.")

    # Start server
    print("🌐 Starting server at http://localhost:8000")
    try:
        import uvicorn
        uvicorn.run("server.server:app", host="0.0.0.0", port=8000, reload=True)
    except KeyboardInterrupt:
        print("\n👋 Yukti Research AI stopped.")
    except Exception as e:
        print(f"❌ Server failed to start: {e}")

if __name__ == "__main__":
    main()
