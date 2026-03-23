"""
Enhanced GitHub Repository Analyzer
====================================
Analyzes GitHub repositories and extracts:
- README content
- Repository structure
- Methodology
- Novelty/innovation
- Images (PNG, JPG, etc.) → stored in images folder
"""

import asyncio
import base64
import hashlib
import logging
import os
import re
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

import aiohttp
import aiofiles

logger = logging.getLogger(__name__)


class GitHubRepoAnalyzer:
    """
    Advanced GitHub repository analyzer for research papers.

    Features:
    - Clone or fetch repo via GitHub API
    - Extract README, docs, architecture
    - Identify methodology and innovation
    - Extract and store images
    - Generate structured analysis
    """

    def __init__(
        self,
        output_dir: str = "outputs/github_analysis",
        images_dir: str = "outputs/images",
        github_token: Optional[str] = None
    ):
        """
        Initialize GitHub analyzer.

        Args:
            output_dir: Output directory for analysis results
            images_dir: Directory for extracted images
            github_token: Optional GitHub API token
        """
        self.output_dir = Path(output_dir)
        self.images_dir = Path(images_dir)
        self.github_token = github_token

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)

    async def analyze_repository(
        self,
        repo_url: str,
        extract_images: bool = True,
        analyze_code: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze a GitHub repository.

        Args:
            repo_url: GitHub repository URL
            extract_images: Extract images from repo
            analyze_code: Analyze code structure

        Returns:
            Analysis results dictionary
        """
        try:
            # Parse repo URL
            owner, repo_name = self._parse_repo_url(repo_url)

            if not owner or not repo_name:
                return {
                    "success": False,
                    "error": "Invalid GitHub URL"
                }

            logger.info(f"Analyzing repository: {owner}/{repo_name}")

            # Fetch repository data via GitHub API
            repo_data = await self._fetch_repo_data(owner, repo_name)

            if not repo_data:
                return {
                    "success": False,
                    "error": "Failed to fetch repository data"
                }

            # Extract README
            readme_content = await self._fetch_readme(owner, repo_name)

            # Get repository tree
            tree = await self._fetch_repo_tree(owner, repo_name)

            # Analyze structure
            structure = self._analyze_structure(tree)

            # Extract methodology and novelty from README
            methodology = self._extract_methodology(readme_content)
            novelty = self._extract_novelty(readme_content)

            # Extract images if requested
            images_path = None
            extracted_images = []
            if extract_images:
                images_result = await self._extract_images(
                    owner, repo_name, tree
                )
                images_path = images_result["path"]
                extracted_images = images_result["images"]

            # Generate analysis report
            analysis = {
                "success": True,
                "repo_url": repo_url,
                "owner": owner,
                "repo_name": repo_name,
                "description": repo_data.get("description", ""),
                "language": repo_data.get("language", ""),
                "stars": repo_data.get("stargazers_count", 0),
                "forks": repo_data.get("forks_count", 0),
                "readme_content": readme_content,
                "structure": structure,
                "methodology": methodology,
                "novelty": novelty,
                "images_path": str(images_path) if images_path else None,
                "extracted_images": extracted_images,
                "topics": repo_data.get("topics", []),
                "created_at": repo_data.get("created_at"),
                "updated_at": repo_data.get("updated_at")
            }

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing repository: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _parse_repo_url(self, repo_url: str) -> tuple:
        """Parse GitHub URL to extract owner and repo name"""
        try:
            # Handle different URL formats
            # https://github.com/owner/repo
            # git@github.com:owner/repo.git
            # owner/repo

            if "github.com" in repo_url:
                parsed = urlparse(repo_url)
                path_parts = parsed.path.strip("/").split("/")

                if len(path_parts) >= 2:
                    owner = path_parts[0]
                    repo_name = path_parts[1].replace(".git", "")
                    return owner, repo_name

            # Handle owner/repo format
            elif "/" in repo_url and ":" not in repo_url:
                parts = repo_url.split("/")
                if len(parts) == 2:
                    return parts[0], parts[1]

            return None, None

        except Exception as e:
            logger.error(f"Error parsing repo URL: {e}")
            return None, None

    async def _fetch_repo_data(self, owner: str, repo_name: str) -> Optional[Dict]:
        """Fetch repository metadata from GitHub API"""
        url = f"https://api.github.com/repos/{owner}/{repo_name}"
        headers = {}

        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"GitHub API error: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error fetching repo data: {e}")
            return None

    async def _fetch_readme(self, owner: str, repo_name: str) -> str:
        """Fetch README content"""
        url = f"https://api.github.com/repos/{owner}/{repo_name}/readme"
        headers = {"Accept": "application/vnd.github.v3.raw"}

        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        logger.warning("README not found")
                        return ""
        except Exception as e:
            logger.error(f"Error fetching README: {e}")
            return ""

    async def _fetch_repo_tree(self, owner: str, repo_name: str) -> List[Dict]:
        """Fetch repository file tree"""
        url = f"https://api.github.com/repos/{owner}/{repo_name}/git/trees/main?recursive=1"
        headers = {}

        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("tree", [])
                    else:
                        # Try master branch
                        url = url.replace("main", "master")
                        async with session.get(url, headers=headers) as response2:
                            if response2.status == 200:
                                data = await response2.json()
                                return data.get("tree", [])
                        return []
        except Exception as e:
            logger.error(f"Error fetching tree: {e}")
            return []

    def _analyze_structure(self, tree: List[Dict]) -> Dict[str, Any]:
        """Analyze repository structure"""
        structure = {
            "total_files": 0,
            "directories": [],
            "file_types": {},
            "main_directories": [],
            "has_tests": False,
            "has_docs": False,
            "has_ci": False
        }

        directories = set()

        for item in tree:
            if item.get("type") == "blob":
                structure["total_files"] += 1

                # Count file types
                path = item.get("path", "")
                ext = Path(path).suffix.lower()
                if ext:
                    structure["file_types"][ext] = structure["file_types"].get(ext, 0) + 1

                # Check for key directories
                if "test" in path.lower():
                    structure["has_tests"] = True
                if "doc" in path.lower() or "readme" in path.lower():
                    structure["has_docs"] = True
                if ".github" in path or ".gitlab" in path or "ci" in path.lower():
                    structure["has_ci"] = True

            elif item.get("type") == "tree":
                path = item.get("path", "")
                directories.add(path)

                # Main directories (top-level)
                if "/" not in path:
                    structure["main_directories"].append(path)

        structure["directories"] = sorted(list(directories))

        return structure

    def _extract_methodology(self, readme_content: str) -> str:
        """Extract methodology from README"""
        methodology_sections = []

        # Look for methodology-related sections
        patterns = [
            r"#+\s*Methodology\s*\n(.*?)(?=\n#|$)",
            r"#+\s*Approach\s*\n(.*?)(?=\n#|$)",
            r"#+\s*Architecture\s*\n(.*?)(?=\n#|$)",
            r"#+\s*Implementation\s*\n(.*?)(?=\n#|$)",
            r"#+\s*How it works\s*\n(.*?)(?=\n#|$)",
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, readme_content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                methodology_sections.append(match.group(1).strip())

        if methodology_sections:
            return "\n\n".join(methodology_sections)
        else:
            # Return first few paragraphs as fallback
            paragraphs = readme_content.split("\n\n")
            return "\n\n".join(paragraphs[:3])

    def _extract_novelty(self, readme_content: str) -> str:
        """Extract novelty/innovation from README"""
        novelty_sections = []

        # Look for innovation-related sections
        patterns = [
            r"#+\s*Features\s*\n(.*?)(?=\n#|$)",
            r"#+\s*Innovation\s*\n(.*?)(?=\n#|$)",
            r"#+\s*Novelty\s*\n(.*?)(?=\n#|$)",
            r"#+\s*Key Features\s*\n(.*?)(?=\n#|$)",
            r"#+\s*Highlights\s*\n(.*?)(?=\n#|$)",
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, readme_content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                novelty_sections.append(match.group(1).strip())

        return "\n\n".join(novelty_sections) if novelty_sections else ""

    async def _extract_images(
        self,
        owner: str,
        repo_name: str,
        tree: List[Dict]
    ) -> Dict[str, Any]:
        """Extract images from repository"""
        image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}
        extracted_images = []

        # Create subdirectory for this repo
        repo_images_dir = self.images_dir / f"{owner}_{repo_name}"
        repo_images_dir.mkdir(parents=True, exist_ok=True)

        # Find all image files
        image_files = [
            item for item in tree
            if item.get("type") == "blob" and
            Path(item.get("path", "")).suffix.lower() in image_extensions
        ]

        # Download images
        headers = {}
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"

        async with aiohttp.ClientSession() as session:
            for image_file in image_files[:20]:  # Limit to 20 images
                try:
                    path = image_file.get("path", "")
                    url = f"https://api.github.com/repos/{owner}/{repo_name}/contents/{path}"

                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            content = data.get("content", "")

                            # Decode base64 content
                            image_data = base64.b64decode(content)

                            # Save image
                            filename = Path(path).name
                            save_path = repo_images_dir / filename

                            async with aiofiles.open(save_path, 'wb') as f:
                                await f.write(image_data)

                            extracted_images.append({
                                "original_path": path,
                                "saved_path": str(save_path),
                                "filename": filename
                            })

                            logger.info(f"Extracted image: {filename}")

                except Exception as e:
                    logger.error(f"Error extracting image {path}: {e}")

        return {
            "path": str(repo_images_dir),
            "images": extracted_images,
            "count": len(extracted_images)
        }

    async def generate_research_context(
        self,
        analysis: Dict[str, Any]
    ) -> str:
        """
        Generate research context from repository analysis.

        This creates a structured text that can be used in academic papers.
        """
        if not analysis.get("success"):
            return ""

        context_parts = []

        # Repository overview
        context_parts.append(f"## Repository: {analysis['repo_name']}")
        context_parts.append(f"\n{analysis['description']}\n")

        # Methodology
        if analysis.get("methodology"):
            context_parts.append("### Methodology")
            context_parts.append(analysis["methodology"])

        # Technical details
        structure = analysis.get("structure", {})
        context_parts.append("\n### Technical Structure")
        context_parts.append(f"- Primary Language: {analysis.get('language', 'N/A')}")
        context_parts.append(f"- Total Files: {structure.get('total_files', 0)}")
        context_parts.append(f"- Has Tests: {'Yes' if structure.get('has_tests') else 'No'}")
        context_parts.append(f"- Has Documentation: {'Yes' if structure.get('has_docs') else 'No'}")

        # Novelty
        if analysis.get("novelty"):
            context_parts.append("\n### Innovation & Features")
            context_parts.append(analysis["novelty"])

        return "\n".join(context_parts)
