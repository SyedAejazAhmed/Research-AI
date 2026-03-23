"""
Database Schema for Research AI Platform
==========================================
SQLite/DuckDB schema for persistent citation management, embeddings, and research metadata.
"""

import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any, List
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ResearchDatabase:
    """Database manager for Research AI platform"""

    def __init__(self, db_path: str = "research_ai.db"):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
        self._initialize_db()

    def _initialize_db(self):
        """Create database schema if it doesn't exist"""
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Enable column access by name

        cursor = self.conn.cursor()

        # Create citations table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS citations (
            id TEXT PRIMARY KEY,
            citation_key TEXT UNIQUE,
            title TEXT NOT NULL,
            authors TEXT NOT NULL,  -- JSON array
            year INTEGER,
            source TEXT,
            doi TEXT UNIQUE,
            arxiv_id TEXT,
            pmid TEXT,
            url TEXT,
            abstract TEXT,
            keywords TEXT,  -- JSON array
            bibtex_type TEXT DEFAULT 'article',
            raw_bibtex TEXT,
            raw_metadata TEXT,  -- JSON
            normalized_metadata TEXT,  -- JSON
            pdf_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Create collections table (like Zotero collections)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS collections (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            parent_id TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (parent_id) REFERENCES collections(id) ON DELETE CASCADE
        )
        """)

        # Create citation_collections mapping table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS citation_collections (
            citation_id TEXT,
            collection_id TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (citation_id, collection_id),
            FOREIGN KEY (citation_id) REFERENCES citations(id) ON DELETE CASCADE,
            FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE
        )
        """)

        # Create embeddings table for RAG
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS embeddings (
            id TEXT PRIMARY KEY,
            citation_id TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            embedding BLOB NOT NULL,  -- Serialized numpy array or list
            embedding_model TEXT DEFAULT 'all-MiniLM-L6-v2',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (citation_id) REFERENCES citations(id) ON DELETE CASCADE,
            UNIQUE (citation_id, chunk_index)
        )
        """)

        # Create reference_order table for ordered reference tracking
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reference_order (
            id TEXT PRIMARY KEY,
            paper_id TEXT NOT NULL,
            section_name TEXT NOT NULL,
            citation_id TEXT NOT NULL,
            order_index INTEGER NOT NULL,
            context TEXT,  -- Context where citation is used
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (citation_id) REFERENCES citations(id) ON DELETE CASCADE,
            UNIQUE (paper_id, section_name, order_index)
        )
        """)

        # Create papers table for generated papers
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS papers (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            abstract TEXT,
            query TEXT,
            content TEXT,
            latex_source TEXT,
            pdf_path TEXT,
            docx_path TEXT,
            markdown_path TEXT,
            template_type TEXT,  -- IEEE, Springer, ACM
            research_mode TEXT,  -- normal, academic
            metadata TEXT,  -- JSON
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Create paper_citations mapping table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS paper_citations (
            paper_id TEXT,
            citation_id TEXT,
            section_name TEXT,
            order_index INTEGER,
            PRIMARY KEY (paper_id, citation_id),
            FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE,
            FOREIGN KEY (citation_id) REFERENCES citations(id) ON DELETE CASCADE
        )
        """)

        # Create research_sessions table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS research_sessions (
            id TEXT PRIMARY KEY,
            query TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            research_mode TEXT DEFAULT 'academic',
            citation_style TEXT DEFAULT 'APA',
            paper_id TEXT,
            metadata TEXT,  -- JSON
            error TEXT,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE SET NULL
        )
        """)

        # Create github_repos table for repo analysis
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS github_repos (
            id TEXT PRIMARY KEY,
            repo_url TEXT NOT NULL UNIQUE,
            repo_name TEXT,
            description TEXT,
            readme_content TEXT,
            structure TEXT,  -- JSON
            methodology TEXT,
            novelty TEXT,
            images_path TEXT,  -- Path to extracted images folder
            metadata TEXT,  -- JSON
            analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Create indices for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_citations_doi ON citations(doi)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_citations_year ON citations(year)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_citations_arxiv ON citations(arxiv_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_embeddings_citation ON embeddings(citation_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reference_order_paper ON reference_order(paper_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_paper_citations_paper ON paper_citations(paper_id)")

        self.conn.commit()
        logger.info(f"Database initialized at {self.db_path}")

    def add_citation(
        self,
        citation_id: str,
        title: str,
        authors: List[str],
        year: Optional[int] = None,
        **kwargs
    ) -> bool:
        """Add a new citation to database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
            INSERT INTO citations (
                id, citation_key, title, authors, year, source, doi, arxiv_id, pmid,
                url, abstract, keywords, bibtex_type, raw_bibtex,
                raw_metadata, normalized_metadata, pdf_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                citation_id,
                kwargs.get('citation_key'),
                title,
                json.dumps(authors),
                year,
                kwargs.get('source'),
                kwargs.get('doi'),
                kwargs.get('arxiv_id'),
                kwargs.get('pmid'),
                kwargs.get('url'),
                kwargs.get('abstract'),
                json.dumps(kwargs.get('keywords', [])),
                kwargs.get('bibtex_type', 'article'),
                kwargs.get('raw_bibtex'),
                json.dumps(kwargs.get('raw_metadata', {})),
                json.dumps(kwargs.get('normalized_metadata', {})),
                kwargs.get('pdf_path')
            ))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError as e:
            logger.warning(f"Citation already exists: {citation_id}")
            return False
        except Exception as e:
            logger.error(f"Error adding citation: {e}")
            return False

    def get_citation(self, citation_id: str) -> Optional[Dict[str, Any]]:
        """Get citation by ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM citations WHERE id = ?", (citation_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def search_citations(
        self,
        query: Optional[str] = None,
        author: Optional[str] = None,
        year: Optional[int] = None,
        doi: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search citations"""
        cursor = self.conn.cursor()

        conditions = []
        params = []

        if query:
            conditions.append("(title LIKE ? OR abstract LIKE ?)")
            params.extend([f"%{query}%", f"%{query}%"])

        if author:
            conditions.append("authors LIKE ?")
            params.append(f"%{author}%")

        if year:
            conditions.append("year = ?")
            params.append(year)

        if doi:
            conditions.append("doi = ?")
            params.append(doi)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        cursor.execute(f"""
        SELECT * FROM citations
        WHERE {where_clause}
        ORDER BY year DESC, title
        LIMIT ?
        """, params + [limit])

        return [dict(row) for row in cursor.fetchall()]

    def add_embedding(
        self,
        embedding_id: str,
        citation_id: str,
        chunk_index: int,
        content: str,
        embedding: bytes,
        model: str = "all-MiniLM-L6-v2"
    ) -> bool:
        """Add embedding for a citation chunk"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
            INSERT INTO embeddings (id, citation_id, chunk_index, content, embedding, embedding_model)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (embedding_id, citation_id, chunk_index, content, embedding, model))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding embedding: {e}")
            return False

    def get_embeddings(self, citation_id: str) -> List[Dict[str, Any]]:
        """Get all embeddings for a citation"""
        cursor = self.conn.cursor()
        cursor.execute("""
        SELECT * FROM embeddings
        WHERE citation_id = ?
        ORDER BY chunk_index
        """, (citation_id,))
        return [dict(row) for row in cursor.fetchall()]

    def add_reference_order(
        self,
        ref_id: str,
        paper_id: str,
        section_name: str,
        citation_id: str,
        order_index: int,
        context: Optional[str] = None
    ) -> bool:
        """Add ordered reference for a paper section"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
            INSERT INTO reference_order (id, paper_id, section_name, citation_id, order_index, context)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (ref_id, paper_id, section_name, citation_id, order_index, context))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding reference order: {e}")
            return False

    def get_ordered_references(self, paper_id: str, section_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get ordered references for a paper section"""
        cursor = self.conn.cursor()
        if section_name:
            cursor.execute("""
            SELECT ro.*, c.title, c.authors, c.year, c.doi
            FROM reference_order ro
            JOIN citations c ON ro.citation_id = c.id
            WHERE ro.paper_id = ? AND ro.section_name = ?
            ORDER BY ro.order_index
            """, (paper_id, section_name))
        else:
            cursor.execute("""
            SELECT ro.*, c.title, c.authors, c.year, c.doi
            FROM reference_order ro
            JOIN citations c ON ro.citation_id = c.id
            WHERE ro.paper_id = ?
            ORDER BY ro.section_name, ro.order_index
            """, (paper_id,))
        return [dict(row) for row in cursor.fetchall()]

    def add_paper(
        self,
        paper_id: str,
        title: str,
        query: str,
        **kwargs
    ) -> bool:
        """Add a generated paper"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
            INSERT INTO papers (
                id, title, abstract, query, content, latex_source,
                pdf_path, docx_path, markdown_path, template_type,
                research_mode, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                paper_id,
                title,
                kwargs.get('abstract'),
                query,
                kwargs.get('content'),
                kwargs.get('latex_source'),
                kwargs.get('pdf_path'),
                kwargs.get('docx_path'),
                kwargs.get('markdown_path'),
                kwargs.get('template_type'),
                kwargs.get('research_mode', 'academic'),
                json.dumps(kwargs.get('metadata', {}))
            ))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding paper: {e}")
            return False

    def add_github_repo(
        self,
        repo_id: str,
        repo_url: str,
        **kwargs
    ) -> bool:
        """Add GitHub repository analysis"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
            INSERT INTO github_repos (
                id, repo_url, repo_name, description, readme_content,
                structure, methodology, novelty, images_path, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                repo_id,
                repo_url,
                kwargs.get('repo_name'),
                kwargs.get('description'),
                kwargs.get('readme_content'),
                json.dumps(kwargs.get('structure', {})),
                kwargs.get('methodology'),
                kwargs.get('novelty'),
                kwargs.get('images_path'),
                json.dumps(kwargs.get('metadata', {}))
            ))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding GitHub repo: {e}")
            return False

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
