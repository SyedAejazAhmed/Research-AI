"""
Academic References Integration for GPT-Researcher

Add this to your research workflow to automatically include
20-30 properly formatted academic citations in reports.
"""

import os
import sys
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def generate_academic_references(query: str, max_references: int = 25) -> Dict[str, Any]:
    """
    Generate 20-30 academic references for a research query.
    
    Args:
        query: Research query string
        max_references: Target number of references (default 25)
        
    Returns:
        Dictionary with:
        - formatted_references: String with [1], [2]... citations
        - papers: List of paper dictionaries
        - total_results: Number of unique papers found
    """
    try:
        # Import academic search module
        from mcp_server.academic_mcp_server import comprehensive_academic_search
        
        # Calculate optimal per-source limit
        per_source = max(6, max_references // 4)
        
        logger.info(f"🔍 Searching academic sources for: {query}")
        logger.info(f"📚 Target: {max_references} references")
        
        # Run comprehensive search
        result = comprehensive_academic_search(query, per_source)
        
        logger.info(f"✓ Found {result['total_results']} unique papers")
        
        return result
        
    except ImportError as e:
        logger.error(f"Academic MCP server not available: {e}")
        logger.info("Install with: pip install arxiv requests beautifulsoup4")
        return {
            "formatted_references": "",
            "papers": [],
            "total_results": 0
        }
    except Exception as e:
        logger.error(f"Academic search error: {e}")
        return {
            "formatted_references": "",
            "papers": [],
            "total_results": 0
        }


def append_references_to_report(report: str, references: str) -> str:
    """
    Append academic references section to a research report.
    
    Args:
        report: Existing report in Markdown
        references: Formatted references string with [1], [2]...
        
    Returns:
        Complete report with references section
    """
    if not references or references == "No references found.":
        return report
    
    # Add references section
    report += "\n\n" + "="*70 + "\n"
    report += "## 📚 Academic References\n\n"
    report += references + "\n"
    
    return report


# Example usage in GPTResearcher workflow
async def research_with_citations(query: str, report_type: str = "research_report") -> str:
    """
    Example: Conduct research and automatically append academic citations.
    
    This is how you would integrate academic references into your
    existing GPTResearcher workflow.
    """
    from gpt_researcher import GPTResearcher
    
    # Standard research process
    researcher = GPTResearcher(query=query, report_type=report_type)
    await researcher.conduct_research()
    report = await researcher.write_report()
    
    # Add academic references for academic/detailed reports
    if report_type in ["research_report", "detailed_report", "academic"]:
        logger.info("📚 Generating academic citations...")
        
        result = generate_academic_references(query, max_references=25)
        
        if result['total_results'] > 0:
            report = append_references_to_report(report, result['formatted_references'])
            logger.info(f"✓ Added {result['total_results']} citations to report")
    
    return report


# Integration with server_utils.py
def enhance_report_with_academics(report: str, query: str, academic_mode: bool = False) -> str:
    """
    Add to handle_start_command in server_utils.py
    
    Usage:
        report = await manager.start_streaming(...)
        
        # Enhance with academic references if enabled
        if academic_mode:
            report = enhance_report_with_academics(report, query, academic_mode=True)
    """
    if not academic_mode:
        return report
    
    logger.info("📚 Academic mode: Fetching research paper citations...")
    
    result = generate_academic_references(query, max_references=25)
    
    if result['total_results'] >= 10:  # Only add if we got enough papers
        report = append_references_to_report(report, result['formatted_references'])
        logger.info(f"✓ Added {result['total_results']} academic citations")
    else:
        logger.warning(f"⚠️ Only found {result['total_results']} papers (minimum 10 required)")
    
    return report


if __name__ == "__main__":
    # Test the integration
    import asyncio
    
    async def test():
        query = "machine learning applications in climate change prediction"
        
        print("\n" + "="*70)
        print("Testing Academic References Integration")
        print("="*70 + "\n")
        
        print(f"Query: {query}\n")
        
        # Generate references
        result = generate_academic_references(query, max_references=25)
        
        print("\n" + "="*70)
        print("Generated References:")
        print("="*70 + "\n")
        print(result['formatted_references'])
        
        print("\n" + "="*70)
        print(f"Total: {result['total_results']} unique papers")
        print("="*70)
        
        # Test report integration
        mock_report = f"""# Research Report: {query}

## Executive Summary
This is a sample research report...

## Key Findings
1. Finding one
2. Finding two
3. Finding three

## Conclusion
Based on the research...
"""
        
        enhanced_report = append_references_to_report(mock_report, result['formatted_references'])
        
        print("\n" + "="*70)
        print("Enhanced Report Preview (with references):")
        print("="*70)
        print(enhanced_report[-500:])  # Show last 500 chars
    
    asyncio.run(test())
