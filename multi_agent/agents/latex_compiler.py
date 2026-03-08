"""
LaTeX Compiler Agent
====================

Compiles LaTeX documents to PDF using native Linux LaTeX installation.
Handles compilation, error parsing, and output management.

Requirements (Linux):
- texlive-full or texlive-latex-extra
- latexmk (recommended)
- pdflatex, xelatex, or lualatex
"""

import os
import shutil
import subprocess
import tempfile
import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from enum import Enum

from .base import BaseAgent, AgentConfig, AgentResponse
from .utils.views import print_agent_output


class CompilerEngine(Enum):
    """LaTeX compiler engines."""
    PDFLATEX = "pdflatex"
    XELATEX = "xelatex"
    LUALATEX = "lualatex"
    LATEXMK = "latexmk"


@dataclass
class CompilationResult:
    """Result of a LaTeX compilation."""
    success: bool
    pdf_path: Optional[str] = None
    log_content: str = ""
    errors: List[str] = None
    warnings: List[str] = None
    compilation_time: float = 0.0
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class LaTeXCompilerAgent(BaseAgent):
    """
    Agent for compiling LaTeX documents to PDF.
    
    Features:
    - Multiple compiler engine support (pdflatex, xelatex, lualatex, latexmk)
    - Automatic dependency detection
    - BibTeX/Biber bibliography processing
    - Error and warning parsing
    - Temporary file cleanup
    - Multi-pass compilation
    """
    
    def __init__(self, output_dir: str = "./outputs", websocket=None, stream_output=None, headers=None):
        config = AgentConfig(name="LaTeXCompiler", description="LaTeX to PDF compilation", timeout=300)
        super().__init__(websocket, stream_output, headers, config)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._check_installation()
    
    def _check_installation(self) -> Dict[str, bool]:
        """Check available LaTeX compilers."""
        compilers = {}
        for engine in CompilerEngine:
            compilers[engine.value] = shutil.which(engine.value) is not None
        
        self.available_compilers = compilers
        return compilers
    
    def get_available_compilers(self) -> List[str]:
        """Get list of available compilers."""
        return [name for name, available in self.available_compilers.items() if available]
    
    def _get_default_compiler(self) -> str:
        """Get the default available compiler."""
        preference = ["latexmk", "pdflatex", "xelatex", "lualatex"]
        for compiler in preference:
            if self.available_compilers.get(compiler):
                return compiler
        raise RuntimeError("No LaTeX compiler found. Install texlive-full or texlive-latex-extra.")
    
    def _parse_log(self, log_content: str) -> Tuple[List[str], List[str]]:
        """Parse LaTeX log file for errors and warnings."""
        errors = []
        warnings = []
        
        lines = log_content.split('\n')
        current_error = []
        in_error = False
        
        for line in lines:
            # Errors
            if line.startswith('!') or 'Error:' in line or 'Fatal error' in line:
                in_error = True
                current_error = [line]
            elif in_error:
                if line.strip() and not line.startswith('l.'):
                    current_error.append(line)
                else:
                    if line.startswith('l.'):
                        current_error.append(line)
                    errors.append('\n'.join(current_error))
                    current_error = []
                    in_error = False
            
            # Warnings
            if 'Warning:' in line or 'warning:' in line.lower():
                warnings.append(line.strip())
            elif 'Underfull' in line or 'Overfull' in line:
                warnings.append(line.strip())
        
        return errors, warnings
    
    def _parse_errors(self, log_content: str) -> List[str]:
        """Parse only errors from LaTeX log file."""
        errors, _ = self._parse_log(log_content)
        return errors
    
    def _parse_warnings(self, log_content: str) -> List[str]:
        """Parse only warnings from LaTeX log file."""
        _, warnings = self._parse_log(log_content)
        return warnings
    
    async def compile(
        self,
        source: str,
        output_name: str = "document",
        engine: str = None,
        bibliography: Optional[str] = None,
        extra_args: List[str] = None,
        clean_aux: bool = True,
    ) -> CompilationResult:
        """
        Compile LaTeX source to PDF.
        
        Args:
            source: LaTeX source code or path to .tex file
            output_name: Name for the output PDF (without extension)
            engine: Compiler engine to use (pdflatex, xelatex, lualatex, latexmk)
            bibliography: BibTeX content or path to .bib file
            extra_args: Additional compiler arguments
            clean_aux: Remove auxiliary files after compilation
            
        Returns:
            CompilationResult with PDF path and any errors/warnings
        """
        import time
        start_time = time.time()
        
        engine = engine or self._get_default_compiler()
        if not self.available_compilers.get(engine, False):
            return CompilationResult(
                success=False,
                errors=[f"Compiler not available: {engine}"],
            )
        
        # Create temporary directory for compilation
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            tex_file = temp_path / "document.tex"
            
            # Write source file
            if os.path.isfile(source):
                shutil.copy(source, tex_file)
            else:
                tex_file.write_text(source, encoding='utf-8')
            
            # Write bibliography if provided
            if bibliography:
                bib_file = temp_path / "references.bib"
                if os.path.isfile(bibliography):
                    shutil.copy(bibliography, bib_file)
                else:
                    bib_file.write_text(bibliography, encoding='utf-8')
            
            # Build compiler command
            if engine == "latexmk":
                cmd = [
                    "latexmk",
                    "-pdf",
                    "-interaction=nonstopmode",
                    "-output-directory=" + str(temp_path),
                    str(tex_file)
                ]
            else:
                cmd = [
                    engine,
                    "-interaction=nonstopmode",
                    "-output-directory=" + str(temp_path),
                    str(tex_file)
                ]
            
            if extra_args:
                cmd.extend(extra_args)
            
            await self.log_output(f"Compiling with {engine}...")
            
            # First pass
            try:
                result = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(temp_path)
                )
                stdout, stderr = await result.communicate()
            except Exception as e:
                return CompilationResult(
                    success=False,
                    errors=[f"Compilation failed: {str(e)}"],
                    compilation_time=time.time() - start_time,
                )
            
            # Run BibTeX if bibliography exists and not using latexmk
            if bibliography and engine != "latexmk":
                bibtex_cmd = ["bibtex", str(temp_path / "document")]
                try:
                    bib_result = await asyncio.create_subprocess_exec(
                        *bibtex_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        cwd=str(temp_path)
                    )
                    await bib_result.communicate()
                    
                    # Two more passes for references
                    for _ in range(2):
                        result = await asyncio.create_subprocess_exec(
                            *cmd,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                            cwd=str(temp_path)
                        )
                        await result.communicate()
                except Exception:
                    pass  # BibTeX errors are non-fatal
            
            # Check for PDF
            pdf_file = temp_path / "document.pdf"
            if not pdf_file.exists():
                # Try reading log for errors
                log_file = temp_path / "document.log"
                log_content = log_file.read_text(encoding='utf-8', errors='ignore') if log_file.exists() else ""
                errors, warnings = self._parse_log(log_content)
                
                return CompilationResult(
                    success=False,
                    log_content=log_content,
                    errors=errors or ["PDF not generated. Check LaTeX source."],
                    warnings=warnings,
                    compilation_time=time.time() - start_time,
                )
            
            # Copy PDF to output directory
            output_pdf = self.output_dir / f"{output_name}.pdf"
            shutil.copy(pdf_file, output_pdf)
            
            # Parse log
            log_file = temp_path / "document.log"
            log_content = log_file.read_text(encoding='utf-8', errors='ignore') if log_file.exists() else ""
            errors, warnings = self._parse_log(log_content)
            
            await self.log_output(f"Compilation successful: {output_pdf}")
            
            return CompilationResult(
                success=True,
                pdf_path=str(output_pdf),
                log_content=log_content,
                errors=errors,
                warnings=warnings,
                compilation_time=time.time() - start_time,
            )
    
    async def compile_with_template(
        self,
        template_content: str,
        variables: Dict[str, str],
        output_name: str = "document",
        engine: str = None,
    ) -> CompilationResult:
        """Compile a template with variable substitution."""
        # Fill template variables
        source = template_content
        for key, value in variables.items():
            source = source.replace(f"${{{key}}}", value)
        
        return await self.compile(source, output_name, engine)
    
    async def batch_compile(
        self,
        sources: List[Dict[str, Any]],
        engine: str = None,
    ) -> List[CompilationResult]:
        """Compile multiple documents."""
        results = []
        for i, item in enumerate(sources):
            source = item.get("source", "")
            name = item.get("name", f"document_{i}")
            result = await self.compile(source, name, engine)
            results.append(result)
        return results
    
    def install_packages(self, packages: List[str]) -> bool:
        """
        Attempt to install LaTeX packages using tlmgr.
        
        Note: Requires tlmgr and appropriate permissions.
        """
        if not shutil.which("tlmgr"):
            return False
        
        try:
            for package in packages:
                subprocess.run(
                    ["tlmgr", "install", package],
                    check=True,
                    capture_output=True
                )
            return True
        except subprocess.CalledProcessError:
            return False
    
    async def execute(self, operation: str, **kwargs) -> AgentResponse:
        """Execute LaTeX compilation operations."""
        try:
            if operation == "compile":
                result = await self.compile(
                    source=kwargs.get("source", ""),
                    output_name=kwargs.get("output_name", "document"),
                    engine=kwargs.get("engine"),
                    bibliography=kwargs.get("bibliography"),
                    extra_args=kwargs.get("extra_args"),
                    clean_aux=kwargs.get("clean_aux", True),
                )
                return AgentResponse(
                    success=result.success,
                    data={
                        "pdf_path": result.pdf_path,
                        "compilation_time": result.compilation_time,
                        "errors": result.errors,
                        "warnings": result.warnings,
                    },
                    error=result.errors[0] if result.errors and not result.success else None,
                )
            
            elif operation == "compile_template":
                result = await self.compile_with_template(
                    template_content=kwargs.get("template_content", ""),
                    variables=kwargs.get("variables", {}),
                    output_name=kwargs.get("output_name", "document"),
                    engine=kwargs.get("engine"),
                )
                return AgentResponse(
                    success=result.success,
                    data={
                        "pdf_path": result.pdf_path,
                        "compilation_time": result.compilation_time,
                    },
                    error=result.errors[0] if result.errors and not result.success else None,
                )
            
            elif operation == "batch_compile":
                results = await self.batch_compile(
                    sources=kwargs.get("sources", []),
                    engine=kwargs.get("engine"),
                )
                return AgentResponse(
                    success=all(r.success for r in results),
                    data=[{
                        "pdf_path": r.pdf_path,
                        "success": r.success,
                        "errors": r.errors,
                    } for r in results],
                )
            
            elif operation == "check_installation":
                return AgentResponse(
                    success=True,
                    data={
                        "available_compilers": self.get_available_compilers(),
                        "default_compiler": self._get_default_compiler() if self.get_available_compilers() else None,
                    },
                )
            
            elif operation == "install_packages":
                success = self.install_packages(kwargs.get("packages", []))
                return AgentResponse(
                    success=success,
                    error="Failed to install packages" if not success else None,
                )
            
            else:
                return AgentResponse(success=False, error=f"Unknown operation: {operation}")
                
        except Exception as e:
            return AgentResponse(success=False, error=str(e))
