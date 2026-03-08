def get_retriever(retriever: str):
    """
    Gets the retriever
    Args:
        retriever (str): retriever name

    Returns:
        retriever: Retriever class

    """
    match retriever:
        case "google":
            from search_engine.retrievers import GoogleSearch

            return GoogleSearch
        case "searx":
            from search_engine.retrievers import SearxSearch

            return SearxSearch
        case "searchapi":
            from search_engine.retrievers import SearchApiSearch

            return SearchApiSearch
        case "serpapi":
            from search_engine.retrievers import SerpApiSearch

            return SerpApiSearch
        case "serper":
            from search_engine.retrievers import SerperSearch

            return SerperSearch
        case "duckduckgo":
            from search_engine.retrievers import Duckduckgo

            return Duckduckgo
        case "bing":
            from search_engine.retrievers import BingSearch

            return BingSearch
        case "arxiv":
            from search_engine.retrievers import ArxivSearch

            return ArxivSearch
        case "tavily":
            from search_engine.retrievers import TavilySearch

            return TavilySearch
        case "exa":
            from search_engine.retrievers import ExaSearch

            return ExaSearch
        case "semantic_scholar":
            from search_engine.retrievers import SemanticScholarSearch

            return SemanticScholarSearch
        case "pubmed_central":
            from search_engine.retrievers import PubMedCentralSearch

            return PubMedCentralSearch
        case "custom":
            from search_engine.retrievers import CustomRetriever

            return CustomRetriever
        case "mcp":
            from search_engine.retrievers import MCPRetriever

            return MCPRetriever
        case "local_search":
            from search_engine.retrievers import LocalSearch

            return LocalSearch

        case _:
            return None


def get_retrievers(headers: dict[str, str], cfg):
    """
    Determine which retriever(s) to use based on headers, config, or default.

    Args:
        headers (dict): The headers dictionary
        cfg: The configuration object

    Returns:
        list: A list of retriever classes to be used for searching.
    """
    # Check headers first for multiple retrievers
    if headers.get("retrievers"):
        retrievers = headers.get("retrievers").split(",")
    # If not found, check headers for a single retriever
    elif headers.get("retriever"):
        retrievers = [headers.get("retriever")]
    # If not in headers, check config for multiple retrievers
    elif cfg.retrievers:
        # Handle both list and string formats for config retrievers
        if isinstance(cfg.retrievers, str):
            retrievers = cfg.retrievers.split(",")
        else:
            retrievers = cfg.retrievers
        # Strip whitespace from each retriever name
        retrievers = [r.strip() for r in retrievers]
    # If not found, check config for a single retriever
    elif cfg.retriever:
        retrievers = [cfg.retriever]
    # If still not set, use default retriever
    else:
        retrievers = [get_default_retriever().__name__]

    # Convert retriever names to actual retriever classes
    # Use get_default_retriever() as a fallback for any invalid retriever names
    retriever_classes = [get_retriever(r) or get_default_retriever() for r in retrievers]
    
    return retriever_classes


def get_default_retriever():
    from search_engine.retrievers import LocalSearch

    return LocalSearch