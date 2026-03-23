"""
Enhanced LaTeX Compiler with Docker
====================================
Deterministic LaTeX compilation using Docker with TeX Live 2024.
"""

import subprocess
import os
import json
import logging
from pathlib import Path
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


class DockerLaTeXCompiler:
    """
    Docker-based LaTeX compiler for secure and deterministic builds.

    Features:
    - Runs in isolated Docker container
    - Uses TeX Live 2024 for reproducibility
    - Security: No shell escape, resource limits
    - Error parsing and reporting
    """

    def __init__(
        self,
        image_name: str = "latex-compiler:latest",
        timeout: int = 300,
        memory_limit: str = "2g",
        cpu_limit: str = "2"
    ):
        """
        Initialize Docker LaTeX compiler.

        Args:
            image_name: Docker image name
            timeout: Compilation timeout (seconds)
            memory_limit: Memory limit (e.g., "2g")
            cpu_limit: CPU limit (e.g., "2")
        """
        self.image_name = image_name
        self.timeout = timeout
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit

    def build_image(self, dockerfile_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Build the Docker image for LaTeX compilation.

        Args:
            dockerfile_path: Path to Dockerfile (defaults to engine directory)

        Returns:
            Build result dictionary
        """
        if dockerfile_path is None:
            dockerfile_path = Path(__file__).parent / "Dockerfile"

        try:
            logger.info(f"Building Docker image: {self.image_name}")

            cmd = [
                "docker", "build",
                "-t", self.image_name,
                "-f", str(dockerfile_path),
                str(Path(dockerfile_path).parent)
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes for build
            )

            if result.returncode == 0:
                logger.info("Docker image built successfully")
                return {
                    "success": True,
                    "image": self.image_name,
                    "message": "Image built successfully"
                }
            else:
                logger.error(f"Docker build failed: {result.stderr}")
                return {
                    "success": False,
                    "error": result.stderr
                }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Docker build timed out"
            }
        except Exception as e:
            logger.error(f"Error building Docker image: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def compile(
        self,
        tex_file: str,
        workspace_path: str,
        engine: str = "pdflatex",
        use_bibtex: bool = False,
        passes: int = 2
    ) -> Dict[str, Any]:
        """
        Compile LaTeX document in Docker container.

        Args:
            tex_file: Name of .tex file (e.g., "paper.tex")
            workspace_path: Absolute path to workspace directory
            engine: LaTeX engine (pdflatex, xelatex, lualatex)
            use_bibtex: Run bibtex/biber for references
            passes: Number of compilation passes

        Returns:
            Compilation results dictionary
        """
        workspace_path = os.path.abspath(workspace_path)

        # Validate inputs
        if not os.path.exists(workspace_path):
            return {
                "success": False,
                "error": f"Workspace does not exist: {workspace_path}"
            }

        tex_path = os.path.join(workspace_path, tex_file)
        if not os.path.exists(tex_path):
            return {
                "success": False,
                "error": f"TeX file not found: {tex_file}"
            }

        base_name = os.path.splitext(tex_file)[0]
        pdf_file = f"{base_name}.pdf"

        try:
            # First compilation pass
            logger.info(f"Compiling {tex_file} (pass 1/{passes})")
            result = self._run_docker_command(
                workspace_path,
                [engine, "-interaction=nonstopmode", "-shell-escape=false", tex_file]
            )

            # Run bibtex if requested
            if use_bibtex:
                logger.info("Running bibtex")
                self._run_docker_command(
                    workspace_path,
                    ["bibtex", base_name]
                )

            # Additional passes for references
            for i in range(2, passes + 1):
                logger.info(f"Compiling {tex_file} (pass {i}/{passes})")
                result = self._run_docker_command(
                    workspace_path,
                    [engine, "-interaction=nonstopmode", "-shell-escape=false", tex_file]
                )

            # Parse log file
            log_file = os.path.join(workspace_path, f"{base_name}.log")
            log_content = ""
            errors = []
            warnings = []

            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    log_content = f.read()

                # Simple error/warning parsing
                for line in log_content.split('\n'):
                    if line.startswith('!'):
                        errors.append(line)
                    elif 'Warning:' in line:
                        warnings.append(line)

            # Check if PDF was generated
            pdf_path = os.path.join(workspace_path, pdf_file)
            success = os.path.exists(pdf_path) and len(errors) == 0

            return {
                "success": success,
                "pdf_path": pdf_path if os.path.exists(pdf_path) else None,
                "errors": errors,
                "warnings": warnings[:10],  # Limit warnings
                "log": log_content,
                "message": "Compilation successful" if success else "Compilation failed"
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Compilation timed out after {self.timeout} seconds"
            }
        except Exception as e:
            logger.error(f"Compilation error: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _run_docker_command(
        self,
        workspace_path: str,
        command: List[str]
    ) -> Dict[str, str]:
        """
        Run command in Docker container.

        Args:
            workspace_path: Host path to mount
            command: Command to run

        Returns:
            Command output
        """
        docker_cmd = [
            "docker", "run",
            "--rm",
            "-v", f"{workspace_path}:/work",
            "--memory", self.memory_limit,
            "--cpus", self.cpu_limit,
            "--network", "none",  # No network access for security
            "--security-opt=no-new-privileges",
            self.image_name
        ] + command

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
        """Remove auxiliary LaTeX files"""
        extensions = ['.aux', '.log', '.bbl', '.blg', '.out', '.toc', '.lof', '.lot', '.fls', '.fdb_latexmk']

        for ext in extensions:
            file_path = os.path.join(workspace_path, f"{base_name}{ext}")
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    logger.warning(f"Could not remove {file_path}: {e}")
