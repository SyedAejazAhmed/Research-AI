"""
RAG (Retrieval Augmented Generation) System
=============================================
Handles PDF processing, embedding generation, and vector-based retrieval for citations.
"""

import hashlib
import logging
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import asyncio

import numpy as np

logger = logging.getLogger(__name__)


class RAGSystem:
    """
    RAG system for managing PDF embeddings and semantic search.

    Features:
    - PDF text extraction
    - Chunking with overlap
    - Embedding generation (SentenceTransformers)
    - Vector similarity search
    - Ordered reference activation
    """

    def __init__(
        self,
        db_manager=None,
        model_name: str = "all-MiniLM-L6-v2",
        chunk_size: int = 512,
        chunk_overlap: int = 50
    ):
        """
        Initialize RAG system.

        Args:
            db_manager: Database manager instance
            model_name: SentenceTransformer model name
            chunk_size: Size of text chunks (characters)
            chunk_overlap: Overlap between chunks
        """
        self.db = db_manager
        self.model_name = model_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._model = None

    @property
    def model(self):
        """Lazy load embedding model"""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
                logger.info(f"Loaded embedding model: {self.model_name}")
            except ImportError:
                logger.error("sentence-transformers not installed. Install with: pip install sentence-transformers")
                raise
        return self._model

    async def process_pdf(
        self,
        pdf_path: str,
        citation_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a PDF file: extract text, chunk, and generate embeddings.

        Args:
            pdf_path: Path to PDF file
            citation_id: Citation ID to link embeddings
            metadata: Optional metadata

        Returns:
            Dictionary with processing results
        """
        try:
            # Extract text from PDF
            text = await self._extract_pdf_text(pdf_path)

            if not text or len(text.strip()) < 100:
                return {
                    "success": False,
                    "error": "PDF text extraction failed or too short",
                    "chunks": 0
                }

            # Chunk text
            chunks = self._chunk_text(text)

            # Generate embeddings
            embeddings_data = []
            for idx, chunk in enumerate(chunks):
                embedding = self.model.encode(chunk, convert_to_numpy=True)
                embedding_bytes = pickle.dumps(embedding)

                embedding_id = hashlib.sha256(
                    f"{citation_id}_{idx}".encode()
                ).hexdigest()[:16]

                # Store in database
                if self.db:
                    self.db.add_embedding(
                        embedding_id=embedding_id,
                        citation_id=citation_id,
                        chunk_index=idx,
                        content=chunk,
                        embedding=embedding_bytes,
                        model=self.model_name
                    )

                embeddings_data.append({
                    "id": embedding_id,
                    "chunk_index": idx,
                    "content_preview": chunk[:200] + "..." if len(chunk) > 200 else chunk
                })

            return {
                "success": True,
                "citation_id": citation_id,
                "chunks": len(chunks),
                "embeddings": embeddings_data,
                "model": self.model_name
            }

        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {e}")
            return {
                "success": False,
                "error": str(e),
                "chunks": 0
            }

    async def _extract_pdf_text(self, pdf_path: str) -> str:
        """Extract text from PDF file"""
        try:
            # Try PyPDF2 first
            try:
                import PyPDF2
                with open(pdf_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text() + "\n\n"
                    return text
            except ImportError:
                pass

            # Try pdfplumber as fallback
            try:
                import pdfplumber
                with pdfplumber.open(pdf_path) as pdf:
                    text = ""
                    for page in pdf.pages:
                        text += page.extract_text() + "\n\n"
                    return text
            except ImportError:
                pass

            logger.error("No PDF extraction library available. Install PyPDF2 or pdfplumber")
            return ""

        except Exception as e:
            logger.error(f"PDF extraction error: {e}")
            return ""

    def _chunk_text(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks.

        Args:
            text: Full text to chunk

        Returns:
            List of text chunks
        """
        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = start + self.chunk_size
            chunk = text[start:end]

            # Try to break at sentence boundary
            if end < text_length:
                # Look for sentence end markers
                last_period = chunk.rfind('.')
                last_newline = chunk.rfind('\n')
                break_point = max(last_period, last_newline)

                if break_point > self.chunk_size * 0.5:  # At least 50% of chunk size
                    chunk = chunk[:break_point + 1]
                    end = start + break_point + 1

            chunks.append(chunk.strip())
            start = end - self.chunk_overlap

        return [c for c in chunks if c]  # Filter empty chunks

    async def search_similar(
        self,
        query: str,
        citation_ids: Optional[List[str]] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks using semantic similarity.

        Args:
            query: Search query
            citation_ids: Optional list of citation IDs to search within
            top_k: Number of top results to return

        Returns:
            List of similar chunks with scores
        """
        try:
            # Generate query embedding
            query_embedding = self.model.encode(query, convert_to_numpy=True)

            # Get all embeddings from database
            if self.db:
                if citation_ids:
                    # Search within specific citations
                    all_embeddings = []
                    for cid in citation_ids:
                        embeddings = self.db.get_embeddings(cid)
                        all_embeddings.extend(embeddings)
                else:
                    # This would require a method to get all embeddings
                    # For now, return empty
                    logger.warning("Global search not implemented yet")
                    return []

                # Calculate similarities
                results = []
                for emb_data in all_embeddings:
                    stored_embedding = pickle.loads(emb_data['embedding'])
                    similarity = self._cosine_similarity(query_embedding, stored_embedding)

                    results.append({
                        "citation_id": emb_data['citation_id'],
                        "chunk_index": emb_data['chunk_index'],
                        "content": emb_data['content'],
                        "similarity": float(similarity)
                    })

                # Sort by similarity and return top_k
                results.sort(key=lambda x: x['similarity'], reverse=True)
                return results[:top_k]

            return []

        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

    @staticmethod
    def _cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        return dot_product / (norm1 * norm2) if norm1 and norm2 else 0.0

    async def get_ordered_references(
        self,
        paper_id: str,
        section_name: str,
        context: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get ordered references for a paper section and activate corresponding embeddings.

        Args:
            paper_id: Paper ID
            section_name: Section name (introduction, methodology, etc.)
            context: Optional context for filtering

        Returns:
            List of ordered references with their embeddings
        """
        if not self.db:
            return []

        try:
            # Get ordered references from database
            refs = self.db.get_ordered_references(paper_id, section_name)

            # For each reference, get its embeddings
            enriched_refs = []
            for ref in refs:
                citation_id = ref['citation_id']
                embeddings = self.db.get_embeddings(citation_id)

                # If context is provided, find most relevant chunks
                if context and embeddings:
                    relevant_chunks = await self.search_similar(
                        query=context,
                        citation_ids=[citation_id],
                        top_k=3
                    )
                else:
                    relevant_chunks = []

                enriched_refs.append({
                    **dict(ref),
                    "embedding_count": len(embeddings),
                    "relevant_chunks": relevant_chunks
                })

            return enriched_refs

        except Exception as e:
            logger.error(f"Error getting ordered references: {e}")
            return []

    async def batch_process_pdfs(
        self,
        pdf_citations: List[Tuple[str, str]]
    ) -> Dict[str, Any]:
        """
        Process multiple PDFs in batch.

        Args:
            pdf_citations: List of (pdf_path, citation_id) tuples

        Returns:
            Batch processing results
        """
        results = {
            "total": len(pdf_citations),
            "processed": 0,
            "failed": 0,
            "details": []
        }

        for pdf_path, citation_id in pdf_citations:
            result = await self.process_pdf(pdf_path, citation_id)

            if result["success"]:
                results["processed"] += 1
            else:
                results["failed"] += 1

            results["details"].append({
                "citation_id": citation_id,
                "pdf_path": pdf_path,
                "success": result["success"],
                "chunks": result.get("chunks", 0),
                "error": result.get("error")
            })

        return results


class OrderedReferenceAgent:
    """
    Agent for managing ordered reference tracking.

    This agent ensures that references are used in the correct order
    and that the corresponding embeddings are activated sequentially.
    """

    def __init__(self, db_manager, rag_system: RAGSystem):
        """
        Initialize ordered reference agent.

        Args:
            db_manager: Database manager instance
            rag_system: RAG system instance
        """
        self.db = db_manager
        self.rag = rag_system

    async def add_ordered_reference(
        self,
        paper_id: str,
        section_name: str,
        citation_id: str,
        order_index: int,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add an ordered reference for a paper section.

        Args:
            paper_id: Paper ID
            section_name: Section name
            citation_id: Citation ID
            order_index: Order index (1, 2, 3, ...)
            context: Context where citation is used

        Returns:
            Result dictionary
        """
        ref_id = hashlib.sha256(
            f"{paper_id}_{section_name}_{order_index}".encode()
        ).hexdigest()[:16]

        success = self.db.add_reference_order(
            ref_id=ref_id,
            paper_id=paper_id,
            section_name=section_name,
            citation_id=citation_id,
            order_index=order_index,
            context=context
        )

        if success:
            # Get embeddings for this citation
            embeddings = self.db.get_embeddings(citation_id)

            return {
                "success": True,
                "ref_id": ref_id,
                "embedding_count": len(embeddings),
                "message": f"Added reference {order_index} in {section_name}"
            }
        else:
            return {
                "success": False,
                "error": "Failed to add ordered reference"
            }

    async def get_section_references(
        self,
        paper_id: str,
        section_name: str,
        with_embeddings: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get ordered references for a section with embeddings.

        Args:
            paper_id: Paper ID
            section_name: Section name
            with_embeddings: Include embedding data

        Returns:
            List of ordered references
        """
        refs = self.db.get_ordered_references(paper_id, section_name)

        if not with_embeddings:
            return refs

        # Enrich with embeddings
        enriched = []
        for ref in refs:
            citation_id = ref['citation_id']
            embeddings = self.db.get_embeddings(citation_id)

            enriched.append({
                **dict(ref),
                "embeddings": [
                    {
                        "chunk_index": e['chunk_index'],
                        "content_preview": e['content'][:200]
                    }
                    for e in embeddings
                ]
            })

        return enriched

    async def activate_reference_embeddings(
        self,
        paper_id: str,
        section_name: str,
        order_index: int
    ) -> Dict[str, Any]:
        """
        Activate embeddings for a specific reference in order.

        This simulates the "sequential activation" mentioned in requirements:
        - Reference 1 in introduction → activate embedding 1
        - Reference 2 in introduction → activate embedding 2
        - etc.

        Args:
            paper_id: Paper ID
            section_name: Section name
            order_index: Order index to activate

        Returns:
            Activated embedding data
        """
        refs = self.db.get_ordered_references(paper_id, section_name)

        # Find reference at this order index
        target_ref = next(
            (r for r in refs if r['order_index'] == order_index),
            None
        )

        if not target_ref:
            return {
                "success": False,
                "error": f"No reference at order {order_index}"
            }

        # Get embeddings for this citation
        citation_id = target_ref['citation_id']
        embeddings = self.db.get_embeddings(citation_id)

        return {
            "success": True,
            "order_index": order_index,
            "citation_id": citation_id,
            "citation_title": target_ref['title'],
            "embeddings_activated": len(embeddings),
            "embeddings": [
                {
                    "chunk_index": e['chunk_index'],
                    "content": e['content']
                }
                for e in embeddings
            ]
        }
