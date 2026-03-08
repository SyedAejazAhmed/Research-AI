"""
Yukti Research AI - Startup Script (Linux)
===========================================
Installs dependencies, starts the Vite dev server (frontend on :5173)
and the FastAPI backend (on :8000) together.

Usage:
  python3 backend/main.py            # start both servers
  python3 backend/main.py --rebuild  # force npm install + rebuild
  python3 backend/main.py --backend  # backend only (no frontend dev server)
"""

import subprocess
import sys
import os
import signal
import time
from pathlib import Path

# ── Resolve project root (one level above this script) ────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(PROJECT_ROOT)                      # ensure all relative paths resolve correctly
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))   # make project packages importable


_procs = []  # track child processes for clean shutdown


def _cleanup(sig=None, frame=None):
    print("\n👋 Shutting down Yukti Research AI...")
    for p in _procs:
        try:
            p.terminate()
        except Exception:
            pass
    sys.exit(0)


signal.signal(signal.SIGINT, _cleanup)
signal.signal(signal.SIGTERM, _cleanup)


def run_command(command, cwd=None):
    print(f"  ▸ {' '.join(command)}")
    try:
        subprocess.check_call(command, cwd=cwd)
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Error: {e}")
        return False
    except FileNotFoundError as e:
        print(f"  ✗ Command not found: {e}")
        return False


def main():
    print("🚀 Initializing Yukti Research AI...\n")

    backend_only = "--backend" in sys.argv
    rebuild = "--rebuild" in sys.argv

    # ── Virtual env check ─────────────────────────────────────────────
    if not os.environ.get('VIRTUAL_ENV'):
        print("💡 Hint: Run inside a virtualenv for isolation.\n")

    # ── Python dependencies ───────────────────────────────────────────
    print("📦 Installing / verifying Python dependencies...")
    if not run_command([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"]):
        print("❌ Failed to install Python dependencies.")
        return
    print("  ✓ Python packages OK\n")

    # ── Ollama check ──────────────────────────────────────────────────
    print("🧠 Checking Ollama (gpt-oss:20b)...")
    try:
        import httpx, asyncio

        async def check_ollama():
            async with httpx.AsyncClient(timeout=5) as client:
                try:
                    resp = await client.get("http://localhost:11434/api/tags")
                    if resp.status_code == 200:
                        models = [m["name"] for m in resp.json().get("models", [])]
                        print(f"  ✓ Ollama running — available models: {models}")
                        if any("gpt-oss" in m for m in models):
                            print("  ✓ gpt-oss:20b detected ✅")
                        else:
                            print("  ⚠ gpt-oss:20b not found — will fall back to first available model")
                        return True
                except Exception:
                    pass
            print("  ⚠ Ollama not reachable at http://localhost:11434 — start Ollama for AI synthesis")
            return False

        asyncio.run(check_ollama())
    except ImportError:
        pass
    print()

    # ── Frontend ──────────────────────────────────────────────────────
    frontend_dir = Path("frontend")
    frontend_proc = None

    if not backend_only and frontend_dir.exists():
        # Install npm packages if needed
        if not (frontend_dir / "node_modules").exists() or rebuild:
            print("📦 Installing frontend npm packages...")
            run_command(["npm", "install"], cwd="frontend")

        print("🎨 Starting Vite dev server  →  http://localhost:5173")
        frontend_proc = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd="frontend",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _procs.append(frontend_proc)
        time.sleep(1.5)  # give Vite a moment to start
        print("  ✓ Frontend dev server started (PID", frontend_proc.pid, ")\n")

    # ── Backend ───────────────────────────────────────────────────────
    print("🌐 Starting FastAPI backend      →  http://localhost:8000")
    print("   (Vite proxies /api and /ws automatically)\n")
    print("─" * 60)

    try:
        import uvicorn
        uvicorn.run("server.server:app", host="0.0.0.0", port=8000, reload=True)
    except KeyboardInterrupt:
        pass
    finally:
        _cleanup()


if __name__ == "__main__":
    main()