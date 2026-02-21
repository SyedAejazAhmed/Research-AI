"""
Yukti Research AI - Simple Cache Utility
========================================
Handles simple JSON-based caching for academic search results
to prevent redundant API calls and improve performance.
"""

import json
import hashlib
import os
import time
from pathlib import Path
from typing import Any, Optional

class SearchCache:
    """Simple disk-based cache for search results."""
    
    def __init__(self, cache_dir: str = ".cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.expiry = 86400 * 7  # 7 days
        
    def _get_key(self, query: str, context: str = "") -> str:
        """Generate a unique key for the query and context."""
        combined = f"{query}:{context}"
        return hashlib.mdsafe_hex(combined.encode()).hexdigest() if hasattr(hashlib, "mdsafe_hex") else hashlib.md5(combined.encode()).hexdigest()

    def get(self, query: str, context: str = "") -> Optional[Any]:
        """Retrieve result from cache if it exists and hasn't expired."""
        key = self._get_key(query, context)
        cache_file = self.cache_dir / f"{key}.json"
        
        if cache_file.exists():
            # Check expiry
            if time.time() - cache_file.stat().st_mtime < self.expiry:
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except Exception:
                    return None
        return None

    def set(self, query: str, data: Any, context: str = ""):
        """Save result to cache."""
        key = self._get_key(query, context)
        cache_file = self.cache_dir / f"{key}.json"
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f)
        except Exception:
            pass

# Create global instance
cache = SearchCache()
