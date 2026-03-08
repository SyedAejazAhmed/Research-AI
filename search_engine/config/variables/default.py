from .base import BaseConfig

DEFAULT_CONFIG: BaseConfig = {
    "RETRIEVER": "local_search",
    "EMBEDDING": "ollama:nomic-embed-text",
    "SIMILARITY_THRESHOLD": 0.42,
    "FAST_LLM": "ollama:gpt-oss:20b",
    "SMART_LLM": "ollama:gpt-oss:20b",
    "STRATEGIC_LLM": "ollama:gpt-oss:20b",
    "FAST_TOKEN_LIMIT": 600,  # ~4 min at 2.58 tok/s (for planning/analysis)
    "SMART_TOKEN_LIMIT": 1200,  # ~8 min at 2.58 tok/s (minimum for complete reports)
    "STRATEGIC_TOKEN_LIMIT": 600,
    "BROWSE_CHUNK_MAX_LENGTH": 4096,
    "CURATE_SOURCES": False,
    "SUMMARY_TOKEN_LIMIT": 500,
    "TEMPERATURE": 0.4,
    "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    "MAX_SEARCH_RESULTS_PER_QUERY": 2,  # Reduced from 3 to save time
    "MEMORY_BACKEND": "local",
    "TOTAL_WORDS": 300,  # Concise but complete (~5 min generation)
    "REPORT_FORMAT": "APA",
    "MAX_ITERATIONS": 1,  # Reduced from 2 to save time
    "AGENT_ROLE": None,
    "SCRAPER": "bs",
    "MAX_SCRAPER_WORKERS": 15,
    "MAX_SUBTOPICS": 3,
    "LANGUAGE": "english",
    "REPORT_SOURCE": "web",
    "DOC_PATH": "./my-docs",
    "PROMPT_FAMILY": "default",
    "LLM_KWARGS": {
        "timeout": 600,  # 10 minute timeout
        "num_ctx": 8192,
        "num_predict": 1200,  # 1200 tokens = ~7-8 min at 2.58 tok/s (safe buffer for complete reports)
        "num_thread": 16,
        "num_gpu": 0,
    },
    "EMBEDDING_KWARGS": {},
    "VERBOSE": False,
    # Deep research specific settings
    "DEEP_RESEARCH_BREADTH": 2,
    "DEEP_RESEARCH_DEPTH": 2,
    "DEEP_RESEARCH_CONCURRENCY": 3,
    
    # MCP retriever specific settings
    "MCP_SERVERS": [],  # List of predefined MCP server configurations
    "MCP_AUTO_TOOL_SELECTION": True,  # Whether to automatically select the best tool for a query
    "MCP_ALLOWED_ROOT_PATHS": [],  # List of allowed root paths for local file access
    "MCP_STRATEGY": "fast",  # MCP execution strategy: "fast", "deep", "disabled"
    "REASONING_EFFORT": "medium",
}
