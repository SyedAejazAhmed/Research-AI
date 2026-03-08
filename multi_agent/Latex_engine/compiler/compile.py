#!/usr/bin/env python3
"""
LaTeX Compiler Wrapper
Manages Docker-based LaTeX compilation with timeout and resource limits.
"""
import subprocess
import os
import json
from pathlib import Path
from typing import Dict, Tuple, Optional

# Import from same directory
from .error_parser import parse_latex_log


class LaTeXCompiler:
    def __init__(
        self,
        image_name: str = "texlive-compiler:latest",
        timeout: int = 300,  # 5 minutes default
        memory_limit: str = "2g"
    ):
        self.image_name = image_name
        self.timeout = timeout
        self.memory_limit = memory_limit
    
    def compile(
        self,
        tex_file: str,
        workspace_path: str,
        engine: str = "pdflatex",
        bibtex: bool = False
    ) -> Dict:
        """
        Compile a LaTeX document inside Docker container.
        
        Args:
            tex_file: Name of the .tex file (e.g., "paper.tex")
            workspace_path: Absolute path to workspace directory
            engine: LaTeX engine (pdflatex, xelatex, lualatex)
            bibtex: Whether to run bibtex for references
        
        Returns:
            Dict with compilation results:
            {
                "success": bool,
                "pdf_path": str or None,
                "errors": list,
                "warnings": list,
                "log": str
            }
        """
        workspace_path = os.path.abspath(workspace_path)
        
        if not os.path.exists(workspace_path):
            return {
                "success": False,
                "pdf_path": None,
                "errors": [f"Workspace path does not exist: {workspace_path}"],
                "warnings": [],
                "log": ""
            }
        
        tex_path = os.path.join(workspace_path, tex_file)
        if not os.path.exists(tex_path):
            return {
                "success": False,
                "pdf_path": None,
                "errors": [f"TeX file not found: {tex_file}"],
                "warnings": [],
                "log": ""
            }
        
        base_name = os.path.splitext(tex_file)[0]
        log_file = f"{base_name}.log"
        pdf_file = f"{base_name}.pdf"
        
        try:
            # First pass: compile LaTeX
            result = self._run_docker_command(
                workspace_path,
                [engine, "-interaction=nonstopmode", tex_file]
            )
            
            # Run bibtex if requested and .bib file exists
            if bibtex:
                bib_files = list(Path(workspace_path).glob("*.bib"))
                if bib_files:
                    self._run_docker_command(workspace_path, ["bibtex", base_name])
                    # Second pass after bibtex
                    self._run_docker_command(
                        workspace_path,
                        [engine, "-interaction=nonstopmode", tex_file]
                    )
                    # Third pass to resolve references
                    result = self._run_docker_command(
                        workspace_path,
                        [engine, "-interaction=nonstopmode", tex_file]
                    )
            
            # Parse the log file
            log_path = os.path.join(workspace_path, log_file)
            log_content = ""
            errors = []
            warnings = []
            
            if os.path.exists(log_path):
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    log_content = f.read()
                
                parsed = parse_latex_log(log_content)
                errors = parsed["errors"]
                warnings = parsed["warnings"]
            
            # Check if PDF was generated
            pdf_path = os.path.join(workspace_path, pdf_file)
            success = os.path.exists(pdf_path) and len(errors) == 0
            
            return {
                "success": success,
                "pdf_path": pdf_path if os.path.exists(pdf_path) else None,
                "errors": errors,
                "warnings": warnings,
                "log": log_content,
                "raw_output": result["stdout"] + result["stderr"]
            }
        
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "pdf_path": None,
                "errors": [f"Compilation timed out after {self.timeout} seconds"],
                "warnings": [],
                "log": ""
            }
        except Exception as e:
            return {
                "success": False,
                "pdf_path": None,
                "errors": [f"Compilation failed: {str(e)}"],
                "warnings": [],
                "log": ""
            }
    
    def _run_docker_command(
        self,
        workspace_path: str,
        command: list
    ) -> Dict[str, str]:
        """
        Run a command inside the Docker container.
        
        Args:
            workspace_path: Host path to mount
            command: Command to run inside container
        
        Returns:
            Dict with stdout and stderr
        """
        docker_cmd = [
            "docker", "run",
            "--rm",
            "-v", f"{workspace_path}:/work",
            "--memory", self.memory_limit,
            "--cpus", "2",
            self.image_name,
            "-c", " ".join(command)
        ]
        
        result = subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True,
            timeout=self.timeout,
            cwd=workspace_path
        )
        
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    
    def clean_auxiliary_files(self, workspace_path: str, base_name: str):
        """Remove auxiliary LaTeX files (.aux, .log, .bbl, etc.)"""
        extensions = ['.aux', '.log', '.bbl', '.blg', '.out', '.toc', '.lof', '.lot']
        for ext in extensions:
            file_path = os.path.join(workspace_path, f"{base_name}{ext}")
            if os.path.exists(file_path):
                os.remove(file_path)


def main():
    """Example usage"""
    compiler = LaTeXCompiler()
    
    # Example: compile test.tex
    result = compiler.compile(
        tex_file="test.tex",
        workspace_path="/media/aejaz/New Volume/Projects/Research Agent/multi_agents/Latex_engine/workspace"
    )
    
    print(json.dumps(result, indent=2))
    
    if result["success"]:
        print(f"\n✅ PDF generated: {result['pdf_path']}")
    else:
        print("\n❌ Compilation failed")
        for error in result["errors"]:
            print(f"  ERROR: {error}")


if __name__ == "__main__":
    main()
