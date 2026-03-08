"""
Yukti Research AI - Startup Script
===================================
Installs dependencies and starts the FastAPI server.
"""

import subprocess
import sys
import os
from pathlib import Path

# ── Resolve project root (one level above this script) ────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(PROJECT_ROOT)                      # ensure all relative paths resolve correctly
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))   # make project packages importable

def run_command(command, cwd=None):
    print(f"Executing: {' '.join(command)}")
    try:
        subprocess.check_call(command, cwd=cwd)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
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

    # Check for Ollama
    print("🧪 Checking for Ollama...")
    try:
        import httpx
        import asyncio
        
        async def check_ollama():
            async with httpx.AsyncClient() as client:
                try:
                    resp = await client.get("http://localhost:11434/api/tags")
                    if resp.status_code == 200:
                        print("✅ Ollama is running.")
                        return True
                except:
                    pass
            print("⚠️ Ollama is NOT running or unreachable at http://localhost:11434")
            print("💡 Please start Ollama for AI synthesis capabilities.")
            return False
            
        import asyncio
        asyncio.run(check_ollama())
    except ImportError:
        pass

    # Build Frontend if needed
    frontend_dir = Path("frontend")
    if frontend_dir.exists():
        print("🎨 Building advanced React frontend...")
        frontend_dist = frontend_dir / "dist"
        if not frontend_dist.exists() or "--rebuild" in sys.argv:
            print("📦 Installing frontend dependencies...")
            run_command(["cmd", "/c", "npm", "install"], cwd="frontend")
            print("🏗️ Running build...")
            run_command(["cmd", "/c", "npm", "run", "build"], cwd="frontend")
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
