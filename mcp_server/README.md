# 🎓 GPT Researcher MCP Server - Multi-Format Citation Generator

> **Academic Citation Support**: Professional research with 6 citation formats (APA, MLA, Chicago, Harvard, IEEE, Vancouver)

## Overview

This MCP server includes:
1. **GPT Researcher** - Comprehensive web research and report generation via Machine Conversation Protocol (MCP)
2. **Academic Citation Generator** - Multi-format academic citations with 20-30 peer-reviewed references

Repository: [https://github.com/assafelovic/gptr-mcp](https://github.com/assafelovic/gptr-mcp)

---

## 🎓 Academic Citation Generator

### Features
- **6 Citation Formats**: APA 7th, MLA 9th, Chicago, Harvard, IEEE, Vancouver
- **Multi-Source Search**: ArXiv, Semantic Scholar, PubMed, Google Scholar, Universities
- **20-30 References**: Comprehensive research coverage  
- **Frontend Integration**: User-selectable citation format dropdown
- **Real-time Generation**: Citations added automatically to reports

### Quick Start

1. **Enable Academic Mode** in frontend ✓
2. **Select Citation Format**:
   - APA 7th (Psychology, Education)
   - MLA 9th (Humanities, Literature)
   - Chicago (History, Arts)
   - Harvard (Business, Economics)
   - IEEE (Engineering, CS)
   - Vancouver (Medical)
3. **Start Research** - citations are automatically generated

### Standalone Testing

```bash
# Test all formats
python test_citation_formats.py

# Interactive mode
python mcp-server/academic_mcp_server.py
```

### Python Integration

```python
from mcp_server.academic_mcp_server import comprehensive_academic_search

result = comprehensive_academic_search(
    query="machine learning in healthcare",
    max_per_source=8,
    citation_format="APA"  # APA, MLA, Chicago, Harvard, IEEE, Vancouver
)

print(f"Found {result['total_results']} papers")
print(result['formatted_references'])
```

### Citation Format Examples

**APA**: `Smith, J. A., & Jones, M. B. (2023). Title. Journal. https://doi.org/10.1234/567890`

**MLA**: `Smith, John A., and Mary B. Jones. "Title." Journal, 2023. https://doi.org/10.1234/567890`

**Chicago**: `Smith, John A., and Mary B. Jones. 2023. "Title." Journal. https://doi.org/10.1234/567890.`

**Harvard**: `Smith, J.A. and Jones, M.B. (2023) 'Title', Journal. doi: 10.1234/567890`

**IEEE**: `J. A. Smith and M. B. Jones, "Title," Journal, 2023. doi: 10.1234/567890.`

**Vancouver**: `Smith JA, Jones MB. Title. Journal. 2023; doi: 10.1234/567890`

### Files
- `academic_mcp_server.py` - Main citation generator with 6 formats
- `test_citation_formats.py` - Test script
- See [../CITATION_FORMATS_GUIDE.md](../CITATION_FORMATS_GUIDE.md) for full documentation

---

## Why GPT Researcher MCP?

While LLM apps can access web search tools with MCP, **GPT Researcher MCP delivers deep research results.** Standard search tools return raw results requiring manual filtering, often containing irrelevant sources and wasting context window space.

GPT Researcher autonomously explores and validates numerous sources, focusing only on relevant, trusted and up-to-date information. Though slightly slower than standard search (~30 seconds wait), it delivers:

* ✨ Higher quality information
* 📊 Optimized context usage
* 🔎 Comprehensive results
* 🧠 Better reasoning for LLMs

## Features

### Resources
* `research_resource`: Get web resources related to a given task via research.

### Primary Tools
* `deep_research`: Performs deep web research on a topic, finding reliable and relevant information
* `quick_search`: Performs a fast web search optimized for speed over quality 
* `write_report`: Generate a report based on research results
* `get_research_sources`: Get the sources used in the research
* `get_research_context`: Get the full context of the research

## Installation

For detailed installation and usage instructions, please visit the [official repository](https://github.com/assafelovic/gptr-mcp).

Quick start:

1. Clone the new repository:
   ```bash
   git clone https://github.com/assafelovic/gptr-mcp.git
   cd gptr-mcp
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your API keys:
   ```
   OLLAMA_BASE_URL=http://localhost:11434
   TAVILY_API_KEY=your_tavily_api_key
   ```

4. Run the server:
   ```bash
   python server.py
   ```

For Docker deployment, Claude Desktop integration, example usage, and troubleshooting, please refer to the [full documentation](https://github.com/assafelovic/gptr-mcp).

## Support & Contact

* Website: [gptr.dev](https://gptr.dev)
* Email: assaf.elovic@gmail.com
* GitHub: [assafelovic/gptr-mcp](https://github.com/assafelovic/gptr-mcp) :-)