"""
Zotero Integration Agent
========================

Integrates with Zotero for reference management using PyZotero.
Provides a Python interface to Zotero's functionality:
- Library access (personal and group)
- Citation management
- Collection handling
- BibTeX import/export
- Full-text search

This agent uses the official PyZotero library to interface with
Zotero's API (both web and local).

Note: Zotero itself is a JavaScript/Firefox-based desktop application.
Instead of embedding Zotero, we use PyZotero for Python integration.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union
from enum import Enum
from datetime import datetime
import json
import logging

from .base import BaseAgent, AgentConfig, AgentResponse, AgentStatus

logger = logging.getLogger(__name__)


class ZoteroLibraryType(str, Enum):
    """Types of Zotero libraries"""
    USER = "user"
    GROUP = "group"


class ZoteroItemType(str, Enum):
    """Common Zotero item types"""
    JOURNAL_ARTICLE = "journalArticle"
    BOOK = "book"
    BOOK_SECTION = "bookSection"
    CONFERENCE_PAPER = "conferencePaper"
    THESIS = "thesis"
    REPORT = "report"
    WEBPAGE = "webpage"
    PREPRINT = "preprint"
    MANUSCRIPT = "manuscript"


@dataclass
class ZoteroConfig:
    """Configuration for Zotero connection"""
    library_id: str
    library_type: ZoteroLibraryType = ZoteroLibraryType.USER
    api_key: Optional[str] = None
    local: bool = False  # True for local Zotero access
    base_url: str = "https://api.zotero.org"


@dataclass
class ZoteroItem:
    """Represents a Zotero library item"""
    key: str
    item_type: str
    title: str
    creators: List[Dict[str, str]] = field(default_factory=list)
    date: Optional[str] = None
    abstract: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    publication: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    collections: List[str] = field(default_factory=list)
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    raw_data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "key": self.key,
            "item_type": self.item_type,
            "title": self.title,
            "creators": self.creators,
            "date": self.date,
            "abstract": self.abstract,
            "doi": self.doi,
            "url": self.url,
            "publication": self.publication,
            "volume": self.volume,
            "issue": self.issue,
            "pages": self.pages,
            "tags": self.tags,
            "collections": self.collections,
            "attachments": self.attachments,
        }
    
    @classmethod
    def from_zotero_data(cls, data: Dict[str, Any]) -> "ZoteroItem":
        """Create ZoteroItem from Zotero API response"""
        item_data = data.get("data", data)
        
        # Extract creators/authors
        creators = []
        for creator in item_data.get("creators", []):
            creators.append({
                "type": creator.get("creatorType", "author"),
                "firstName": creator.get("firstName", ""),
                "lastName": creator.get("lastName", ""),
                "name": creator.get("name", ""),  # For single-name creators
            })
        
        # Extract tags
        tags = [tag.get("tag", "") for tag in item_data.get("tags", [])]
        
        return cls(
            key=item_data.get("key", ""),
            item_type=item_data.get("itemType", ""),
            title=item_data.get("title", ""),
            creators=creators,
            date=item_data.get("date"),
            abstract=item_data.get("abstractNote"),
            doi=item_data.get("DOI"),
            url=item_data.get("url"),
            publication=item_data.get("publicationTitle") or item_data.get("bookTitle"),
            volume=item_data.get("volume"),
            issue=item_data.get("issue"),
            pages=item_data.get("pages"),
            tags=tags,
            collections=item_data.get("collections", []),
            raw_data=data,
        )
    
    def to_citation_dict(self) -> Dict[str, Any]:
        """Convert to citation dictionary compatible with CitationMemoryAgent"""
        # Build authors list
        authors = []
        for creator in self.creators:
            if creator.get("name"):
                authors.append(creator["name"])
            else:
                first = creator.get("firstName", "")
                last = creator.get("lastName", "")
                if first and last:
                    authors.append(f"{first} {last}")
                elif last:
                    authors.append(last)
        
        # Parse year from date
        year = None
        if self.date:
            try:
                if len(self.date) >= 4:
                    year = int(self.date[:4])
            except ValueError:
                pass
        
        return {
            "id": self.key,
            "title": self.title,
            "authors": authors,
            "year": year,
            "source": self.publication or "",
            "doi": self.doi,
            "url": self.url,
            "abstract": self.abstract,
            "keywords": self.tags,
            "bibtex_type": self._infer_bibtex_type(),
        }
    
    def _infer_bibtex_type(self) -> str:
        """Infer BibTeX entry type from Zotero item type"""
        mapping = {
            "journalArticle": "article",
            "book": "book",
            "bookSection": "incollection",
            "conferencePaper": "inproceedings",
            "thesis": "phdthesis",
            "report": "techreport",
            "webpage": "misc",
            "preprint": "unpublished",
        }
        return mapping.get(self.item_type, "misc")


@dataclass
class ZoteroCollection:
    """Represents a Zotero collection"""
    key: str
    name: str
    parent_key: Optional[str] = None
    item_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "key": self.key,
            "name": self.name,
            "parent_key": self.parent_key,
            "item_count": self.item_count,
        }
    
    @classmethod
    def from_zotero_data(cls, data: Dict[str, Any]) -> "ZoteroCollection":
        """Create ZoteroCollection from Zotero API response"""
        coll_data = data.get("data", data)
        meta = data.get("meta", {})
        return cls(
            key=coll_data.get("key", ""),
            name=coll_data.get("name", ""),
            parent_key=coll_data.get("parentCollection") or None,
            item_count=meta.get("numItems", 0),
        )


class ZoteroIntegrationAgent(BaseAgent):
    """
    Agent for integrating with Zotero reference manager.
    
    Provides:
    - Library access and search
    - Citation import/export
    - Collection management
    - Attachment handling
    - Sync with citation memory
    
    Uses PyZotero for both Zotero Web API and local Zotero access.
    """
    
    def __init__(
        self,
        config: Optional[ZoteroConfig] = None,
        agent_config: Optional[AgentConfig] = None,
    ):
        """
        Initialize Zotero integration agent.
        
        Args:
            config: Zotero connection configuration
            agent_config: Base agent configuration
        """
        if agent_config is None:
            agent_config = AgentConfig(
                name="ZoteroIntegrationAgent",
                version="1.0.0",
                description="Integrates with Zotero for reference management",
            )
        super().__init__(agent_config)
        
        self.config = config
        self._zotero = None
        self._connected = False
    
    @property
    def zotero(self):
        """Lazy-load PyZotero connection"""
        if self._zotero is None and self.config:
            self._connect()
        return self._zotero
    
    def _connect(self) -> bool:
        """Establish connection to Zotero"""
        if not self.config:
            logger.warning("No Zotero configuration provided")
            return False
        
        try:
            from pyzotero import zotero
            
            self._zotero = zotero.Zotero(
                library_id=self.config.library_id,
                library_type=self.config.library_type.value,
                api_key=self.config.api_key,
                local=self.config.local,
            )
            self._connected = True
            logger.info(f"Connected to Zotero library: {self.config.library_id}")
            return True
        except ImportError:
            logger.error("PyZotero not installed. Run: pip install pyzotero")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Zotero: {e}")
            return False
    
    def is_connected(self) -> bool:
        """Check if connected to Zotero"""
        return self._connected and self._zotero is not None
    
    def configure(self, config: ZoteroConfig) -> bool:
        """Configure and connect to Zotero"""
        self.config = config
        self._zotero = None
        self._connected = False
        return self._connect()
    
    # =========================================================================
    # Library Operations
    # =========================================================================
    
    def get_items(
        self,
        limit: int = 25,
        start: int = 0,
        item_type: Optional[str] = None,
        collection_key: Optional[str] = None,
        q: Optional[str] = None,
        sort: str = "dateModified",
        direction: str = "desc",
    ) -> List[ZoteroItem]:
        """
        Get items from Zotero library.
        
        Args:
            limit: Maximum items to return (max 100)
            start: Offset for pagination
            item_type: Filter by item type
            collection_key: Filter by collection
            q: Search query
            sort: Sort field
            direction: Sort direction ('asc' or 'desc')
        
        Returns:
            List of ZoteroItem objects
        """
        if not self.is_connected():
            logger.error("Not connected to Zotero")
            return []
        
        try:
            params = {
                "limit": min(limit, 100),
                "start": start,
                "sort": sort,
                "direction": direction,
            }
            
            if item_type:
                params["itemType"] = item_type
            if q:
                params["q"] = q
            
            if collection_key:
                items = self._zotero.collection_items(collection_key, **params)
            else:
                items = self._zotero.top(**params)
            
            return [ZoteroItem.from_zotero_data(item) for item in items]
        except Exception as e:
            logger.error(f"Failed to get Zotero items: {e}")
            return []
    
    def get_item(self, key: str) -> Optional[ZoteroItem]:
        """Get a single item by key"""
        if not self.is_connected():
            return None
        
        try:
            item = self._zotero.item(key)
            return ZoteroItem.from_zotero_data(item)
        except Exception as e:
            logger.error(f"Failed to get item {key}: {e}")
            return None
    
    def search_items(
        self,
        query: str,
        fulltext: bool = False,
        limit: int = 25,
    ) -> List[ZoteroItem]:
        """
        Search for items in the library.
        
        Args:
            query: Search query
            fulltext: Include full-text search (slower)
            limit: Maximum results
        
        Returns:
            List of matching items
        """
        if not self.is_connected():
            return []
        
        try:
            if fulltext:
                # Full-text search includes PDFs and notes
                items = self._zotero.fulltext(query, limit=limit)
            else:
                # Quick search on metadata only
                items = self._zotero.top(q=query, limit=limit)
            
            return [ZoteroItem.from_zotero_data(item) for item in items]
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def get_recent_items(self, limit: int = 10) -> List[ZoteroItem]:
        """Get recently modified items"""
        return self.get_items(
            limit=limit,
            sort="dateModified",
            direction="desc",
        )
    
    # =========================================================================
    # Collection Operations
    # =========================================================================
    
    def get_collections(self) -> List[ZoteroCollection]:
        """Get all collections in the library"""
        if not self.is_connected():
            return []
        
        try:
            collections = self._zotero.collections()
            return [ZoteroCollection.from_zotero_data(c) for c in collections]
        except Exception as e:
            logger.error(f"Failed to get collections: {e}")
            return []
    
    def get_collection(self, key: str) -> Optional[ZoteroCollection]:
        """Get a single collection by key"""
        if not self.is_connected():
            return None
        
        try:
            coll = self._zotero.collection(key)
            return ZoteroCollection.from_zotero_data(coll)
        except Exception as e:
            logger.error(f"Failed to get collection {key}: {e}")
            return None
    
    def create_collection(
        self,
        name: str,
        parent_key: Optional[str] = None,
    ) -> Optional[ZoteroCollection]:
        """Create a new collection"""
        if not self.is_connected():
            return None
        
        try:
            payload = {"name": name}
            if parent_key:
                payload["parentCollection"] = parent_key
            
            result = self._zotero.create_collection(payload)
            if result and "successful" in result:
                # Get the created collection key
                created = result["successful"].get("0", {})
                if created:
                    return ZoteroCollection(
                        key=created.get("key", ""),
                        name=name,
                        parent_key=parent_key,
                    )
            return None
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            return None
    
    # =========================================================================
    # Citation Import/Export
    # =========================================================================
    
    def import_bibtex(
        self,
        bibtex: str,
        collection_key: Optional[str] = None,
    ) -> List[str]:
        """
        Import BibTeX entries into Zotero.
        
        Args:
            bibtex: BibTeX content
            collection_key: Target collection (optional)
        
        Returns:
            List of created item keys
        """
        if not self.is_connected():
            return []
        
        try:
            # Parse BibTeX and create items
            # Note: Zotero API can directly import via /import endpoint
            # For more control, we parse and create individually
            
            import_result = self._zotero.create_items(
                self._parse_bibtex_to_items(bibtex)
            )
            
            created_keys = []
            if import_result and "successful" in import_result:
                for idx, item_data in import_result["successful"].items():
                    key = item_data.get("key")
                    if key:
                        created_keys.append(key)
                        # Add to collection if specified
                        if collection_key:
                            self._add_to_collection(key, collection_key)
            
            return created_keys
        except Exception as e:
            logger.error(f"BibTeX import failed: {e}")
            return []
    
    def export_bibtex(
        self,
        item_keys: Optional[List[str]] = None,
        collection_key: Optional[str] = None,
    ) -> str:
        """
        Export items as BibTeX.
        
        Args:
            item_keys: Specific items to export (None for all)
            collection_key: Export entire collection
        
        Returns:
            BibTeX string
        """
        if not self.is_connected():
            return ""
        
        try:
            if item_keys:
                items = [self._zotero.item(key, format="bibtex") for key in item_keys]
                return "\n\n".join(items)
            elif collection_key:
                return self._zotero.collection_items(
                    collection_key, format="bibtex"
                )
            else:
                return self._zotero.top(format="bibtex")
        except Exception as e:
            logger.error(f"BibTeX export failed: {e}")
            return ""
    
    def _parse_bibtex_to_items(self, bibtex: str) -> List[Dict[str, Any]]:
        """Parse BibTeX to Zotero item format"""
        # This is a simplified parser - for production use bibtexparser
        items = []
        # Basic parsing logic - can be enhanced with bibtexparser
        try:
            import re
            
            # Find all entries
            entry_pattern = r'@(\w+)\s*\{\s*([^,]+),\s*([\s\S]*?)\}\s*(?=@|\Z)'
            for match in re.finditer(entry_pattern, bibtex):
                entry_type, cite_key, fields_str = match.groups()
                
                # Parse fields
                fields = {}
                field_pattern = r'(\w+)\s*=\s*[{"]([^}"]+)[}"]'
                for field_match in re.finditer(field_pattern, fields_str):
                    fields[field_match.group(1).lower()] = field_match.group(2)
                
                # Map to Zotero format
                item = {
                    "itemType": self._bibtex_to_zotero_type(entry_type),
                    "title": fields.get("title", ""),
                    "creators": self._parse_authors(fields.get("author", "")),
                    "date": fields.get("year", ""),
                    "DOI": fields.get("doi", ""),
                    "url": fields.get("url", ""),
                }
                
                if entry_type.lower() == "article":
                    item["publicationTitle"] = fields.get("journal", "")
                    item["volume"] = fields.get("volume", "")
                    item["issue"] = fields.get("number", "")
                    item["pages"] = fields.get("pages", "")
                
                items.append(item)
        except Exception as e:
            logger.error(f"BibTeX parsing error: {e}")
        
        return items
    
    def _bibtex_to_zotero_type(self, bibtex_type: str) -> str:
        """Convert BibTeX type to Zotero item type"""
        mapping = {
            "article": "journalArticle",
            "book": "book",
            "inbook": "bookSection",
            "incollection": "bookSection",
            "inproceedings": "conferencePaper",
            "conference": "conferencePaper",
            "phdthesis": "thesis",
            "mastersthesis": "thesis",
            "techreport": "report",
            "misc": "document",
            "unpublished": "manuscript",
        }
        return mapping.get(bibtex_type.lower(), "document")
    
    def _parse_authors(self, author_str: str) -> List[Dict[str, str]]:
        """Parse BibTeX author string"""
        if not author_str:
            return []
        
        creators = []
        for author in author_str.split(" and "):
            author = author.strip()
            if ", " in author:
                # Last, First format
                parts = author.split(", ", 1)
                creators.append({
                    "creatorType": "author",
                    "lastName": parts[0],
                    "firstName": parts[1] if len(parts) > 1 else "",
                })
            else:
                # First Last format
                parts = author.rsplit(" ", 1)
                if len(parts) == 2:
                    creators.append({
                        "creatorType": "author",
                        "firstName": parts[0],
                        "lastName": parts[1],
                    })
                else:
                    creators.append({
                        "creatorType": "author",
                        "lastName": author,
                    })
        
        return creators
    
    def _add_to_collection(self, item_key: str, collection_key: str) -> bool:
        """Add an item to a collection"""
        try:
            self._zotero.addto_collection(collection_key, [item_key])
            return True
        except Exception as e:
            logger.error(f"Failed to add item to collection: {e}")
            return False
    
    # =========================================================================
    # Sync with Citation Memory
    # =========================================================================
    
    def sync_to_memory(
        self,
        memory_agent,
        collection_key: Optional[str] = None,
        limit: int = 100,
    ) -> int:
        """
        Sync Zotero items to CitationMemoryAgent.
        
        Args:
            memory_agent: CitationMemoryAgent instance
            collection_key: Sync specific collection (None for all)
            limit: Maximum items to sync
        
        Returns:
            Number of items synced
        """
        items = self.get_items(collection_key=collection_key, limit=limit)
        synced = 0
        
        for item in items:
            try:
                citation_data = item.to_citation_dict()
                memory_agent.add_citation(**citation_data)
                synced += 1
            except Exception as e:
                logger.error(f"Failed to sync item {item.key}: {e}")
        
        return synced
    
    def sync_from_memory(
        self,
        memory_agent,
        collection_key: Optional[str] = None,
    ) -> int:
        """
        Sync citations from CitationMemoryAgent to Zotero.
        
        Args:
            memory_agent: CitationMemoryAgent instance
            collection_key: Target collection for synced items
        
        Returns:
            Number of items synced
        """
        if not self.is_connected():
            return 0
        
        # Export all citations from memory as BibTeX
        bibtex = memory_agent.export_bibtex()
        if not bibtex:
            return 0
        
        # Import to Zotero
        keys = self.import_bibtex(bibtex, collection_key)
        return len(keys)
    
    # =========================================================================
    # Agent Interface Implementation
    # =========================================================================
    
    async def execute(self, task: Dict[str, Any]) -> AgentResponse:
        """
        Execute a Zotero task.
        
        Supported actions:
        - search: Search library
        - get_items: Get items with filters
        - get_collections: List collections
        - import_bibtex: Import BibTeX
        - export_bibtex: Export as BibTeX
        - sync_to_memory: Sync to CitationMemoryAgent
        """
        action = task.get("action", "")
        
        try:
            if action == "search":
                items = self.search_items(
                    query=task.get("query", ""),
                    fulltext=task.get("fulltext", False),
                    limit=task.get("limit", 25),
                )
                return AgentResponse(
                    status=AgentStatus.SUCCESS,
                    data={"items": [i.to_dict() for i in items]},
                    message=f"Found {len(items)} items",
                )
            
            elif action == "get_items":
                items = self.get_items(
                    limit=task.get("limit", 25),
                    item_type=task.get("item_type"),
                    collection_key=task.get("collection_key"),
                )
                return AgentResponse(
                    status=AgentStatus.SUCCESS,
                    data={"items": [i.to_dict() for i in items]},
                    message=f"Retrieved {len(items)} items",
                )
            
            elif action == "get_collections":
                collections = self.get_collections()
                return AgentResponse(
                    status=AgentStatus.SUCCESS,
                    data={"collections": [c.to_dict() for c in collections]},
                    message=f"Found {len(collections)} collections",
                )
            
            elif action == "import_bibtex":
                keys = self.import_bibtex(
                    bibtex=task.get("bibtex", ""),
                    collection_key=task.get("collection_key"),
                )
                return AgentResponse(
                    status=AgentStatus.SUCCESS,
                    data={"imported_keys": keys},
                    message=f"Imported {len(keys)} items",
                )
            
            elif action == "export_bibtex":
                bibtex = self.export_bibtex(
                    item_keys=task.get("item_keys"),
                    collection_key=task.get("collection_key"),
                )
                return AgentResponse(
                    status=AgentStatus.SUCCESS,
                    data={"bibtex": bibtex},
                    message="Export complete",
                )
            
            else:
                return AgentResponse(
                    status=AgentStatus.FAILED,
                    error=f"Unknown action: {action}",
                )
        
        except Exception as e:
            logger.error(f"Zotero task failed: {e}")
            return AgentResponse(
                status=AgentStatus.FAILED,
                error=str(e),
            )


# =============================================================================
# Factory Functions
# =============================================================================

def create_zotero_agent(
    library_id: str,
    api_key: Optional[str] = None,
    library_type: str = "user",
    local: bool = False,
) -> ZoteroIntegrationAgent:
    """
    Factory function to create a configured Zotero agent.
    
    Args:
        library_id: Zotero library ID
        api_key: API key (not needed for local access)
        library_type: 'user' or 'group'
        local: True for local Zotero access
    
    Returns:
        Configured ZoteroIntegrationAgent
    """
    config = ZoteroConfig(
        library_id=library_id,
        library_type=ZoteroLibraryType(library_type),
        api_key=api_key,
        local=local,
    )
    
    agent = ZoteroIntegrationAgent(config=config)
    agent._connect()
    return agent
