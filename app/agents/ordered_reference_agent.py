"""
Ordered Reference Activation Agent
===================================
Manages ordered references per paper section and activates corresponding embeddings.

For a paper with 30 references:
- Introduction uses refs 1-5 → activates embeddings 1-5
- Literature Review uses refs 6-15 → activates embeddings 6-15
- Methodology uses refs 16-22 → activates embeddings 16-22
- Discussion uses refs 23-28 → activates embeddings 23-28
- Conclusion uses refs 29-30 → activates embeddings 29-30
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class PaperSection(Enum):
    """Standard academic paper sections"""
    ABSTRACT = "abstract"
    INTRODUCTION = "introduction"
    LITERATURE_REVIEW = "literature_review"
    METHODOLOGY = "methodology"
    RESULTS = "results"
    DISCUSSION = "discussion"
    CONCLUSION = "conclusion"
    REFERENCES = "references"


@dataclass
class ReferenceAssignment:
    """Assignment of references to a paper section"""
    section: PaperSection
    citation_ids: List[str]
    start_index: int  # 1-indexed position in full reference list
    end_index: int    # 1-indexed position in full reference list


@dataclass
class ActivatedEmbedding:
    """Activated embedding with metadata"""
    citation_id: str
    embedding_vector: List[float]
    reference_number: int
    section: PaperSection
    metadata: Dict


class OrderedReferenceAgent:
    """
    Manages ordered references across paper sections.

    Key features:
    1. Assigns references to sections in sequential order
    2. Activates embeddings only for references in current section
    3. Maintains citation order consistency
    4. Supports RAG retrieval with section context
    """

    def __init__(self, database_manager=None):
        """
        Initialize the ordered reference agent

        Args:
            database_manager: Database manager instance for accessing citations/embeddings
        """
        self.database = database_manager
        self.section_assignments: Dict[PaperSection, ReferenceAssignment] = {}
        self.total_references = 0
        self.citation_order: List[str] = []  # Global ordered list

    def set_citation_order(self, citation_ids: List[str]):
        """
        Set the global citation order for the paper

        Args:
            citation_ids: Ordered list of citation IDs
        """
        self.citation_order = citation_ids
        self.total_references = len(citation_ids)
        logger.info(f"Set citation order with {self.total_references} references")

    def auto_assign_sections(
        self,
        citation_ids: List[str],
        section_weights: Optional[Dict[PaperSection, float]] = None
    ) -> Dict[PaperSection, ReferenceAssignment]:
        """
        Automatically assign references to sections based on distribution weights

        Args:
            citation_ids: Ordered list of all citation IDs
            section_weights: Optional custom weights for section distribution

        Returns:
            Dictionary mapping sections to reference assignments
        """
        self.set_citation_order(citation_ids)

        # Default distribution (percentages)
        if section_weights is None:
            section_weights = {
                PaperSection.INTRODUCTION: 0.15,      # 15%
                PaperSection.LITERATURE_REVIEW: 0.35, # 35%
                PaperSection.METHODOLOGY: 0.25,       # 25%
                PaperSection.RESULTS: 0.10,           # 10%
                PaperSection.DISCUSSION: 0.10,        # 10%
                PaperSection.CONCLUSION: 0.05,        # 5%
            }

        total_refs = len(citation_ids)
        assignments = {}
        current_idx = 0

        for section, weight in section_weights.items():
            # Calculate how many references for this section
            count = max(1, int(total_refs * weight))

            # Adjust last section to include remaining references
            if section == list(section_weights.keys())[-1]:
                count = total_refs - current_idx

            # Extract citations for this section
            section_citations = citation_ids[current_idx:current_idx + count]

            assignment = ReferenceAssignment(
                section=section,
                citation_ids=section_citations,
                start_index=current_idx + 1,  # 1-indexed
                end_index=current_idx + count
            )

            assignments[section] = assignment
            self.section_assignments[section] = assignment

            logger.info(
                f"Assigned {len(section_citations)} references to {section.value} "
                f"(refs {assignment.start_index}-{assignment.end_index})"
            )

            current_idx += count

        return assignments

    def manual_assign_section(
        self,
        section: PaperSection,
        citation_ids: List[str]
    ):
        """
        Manually assign specific references to a section

        Args:
            section: Paper section
            citation_ids: List of citation IDs to assign
        """
        # Find indices in global order
        start_idx = None
        end_idx = None

        for i, cid in enumerate(self.citation_order):
            if cid in citation_ids:
                if start_idx is None:
                    start_idx = i
                end_idx = i

        assignment = ReferenceAssignment(
            section=section,
            citation_ids=citation_ids,
            start_index=start_idx + 1 if start_idx is not None else 0,
            end_index=end_idx + 1 if end_idx is not None else 0
        )

        self.section_assignments[section] = assignment
        logger.info(f"Manually assigned {len(citation_ids)} references to {section.value}")

    async def activate_embeddings_for_section(
        self,
        section: PaperSection,
        query: Optional[str] = None
    ) -> List[ActivatedEmbedding]:
        """
        Activate embeddings only for references assigned to this section

        Args:
            section: Paper section to activate embeddings for
            query: Optional search query for RAG retrieval

        Returns:
            List of activated embeddings with metadata
        """
        if section not in self.section_assignments:
            logger.warning(f"No references assigned to section: {section.value}")
            return []

        assignment = self.section_assignments[section]
        activated = []

        logger.info(
            f"Activating embeddings for {section.value}: "
            f"refs {assignment.start_index}-{assignment.end_index}"
        )

        # Fetch embeddings for each citation in this section
        for i, citation_id in enumerate(assignment.citation_ids, start=assignment.start_index):
            if self.database:
                embedding_data = await self.database.get_embedding(citation_id)

                if embedding_data:
                    activated.append(ActivatedEmbedding(
                        citation_id=citation_id,
                        embedding_vector=embedding_data.get("vector", []),
                        reference_number=i,
                        section=section,
                        metadata=embedding_data.get("metadata", {})
                    ))

        logger.info(f"Activated {len(activated)} embeddings for {section.value}")
        return activated

    async def retrieve_context_for_section(
        self,
        section: PaperSection,
        query: str,
        top_k: int = 5
    ) -> List[Dict]:
        """
        Perform RAG retrieval limited to references in this section

        Args:
            section: Paper section
            query: Search query
            top_k: Number of top results to return

        Returns:
            List of relevant context chunks with citation info
        """
        activated = await self.activate_embeddings_for_section(section, query)

        if not activated:
            return []

        # Get query embedding
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('all-MiniLM-L6-v2')
        query_embedding = model.encode(query, convert_to_tensor=False).tolist()

        # Compute similarity scores
        results = []
        for emb in activated:
            if emb.embedding_vector:
                # Cosine similarity
                score = self._cosine_similarity(query_embedding, emb.embedding_vector)
                results.append({
                    "citation_id": emb.citation_id,
                    "reference_number": emb.reference_number,
                    "section": section.value,
                    "score": score,
                    "metadata": emb.metadata
                })

        # Sort by score and return top_k
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors"""
        import numpy as np
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))

    def get_section_reference_list(
        self,
        section: PaperSection,
        format: str = "numbered"
    ) -> List[str]:
        """
        Get formatted reference list for a section

        Args:
            section: Paper section
            format: Citation format ("numbered", "apa", "ieee", etc.)

        Returns:
            List of formatted citations
        """
        if section not in self.section_assignments:
            return []

        assignment = self.section_assignments[section]
        references = []

        for i, citation_id in enumerate(assignment.citation_ids, start=assignment.start_index):
            if format == "numbered":
                references.append(f"[{i}]")
            else:
                # Fetch full citation from database
                if self.database:
                    citation = self.database.get_citation(citation_id)
                    if citation:
                        references.append(citation.format(format))

        return references

    def get_full_reference_list(self, format: str = "numbered") -> List[str]:
        """
        Get complete reference list in order

        Args:
            format: Citation format

        Returns:
            Full ordered reference list
        """
        references = []
        for i, citation_id in enumerate(self.citation_order, start=1):
            if format == "numbered":
                references.append(f"[{i}]")
            elif self.database:
                citation = self.database.get_citation(citation_id)
                if citation:
                    references.append(citation.format(format))
        return references

    def generate_latex_references(self) -> str:
        """
        Generate LaTeX bibliography in citation order

        Returns:
            LaTeX bibliography string
        """
        bibliography = []
        bibliography.append("\\begin{thebibliography}{99}\n")

        for i, citation_id in enumerate(self.citation_order, start=1):
            if self.database:
                citation = self.database.get_citation(citation_id)
                if citation:
                    # Format as LaTeX bibitem
                    authors = citation.get("authors", ["Unknown"])
                    title = citation.get("title", "Untitled")
                    year = citation.get("year", "n.d.")
                    venue = citation.get("venue", "")

                    bibitem = f"\\bibitem{{ref{i}}} {', '.join(authors)}. ``{title}.'' {venue}, {year}.\n"
                    bibliography.append(bibitem)

        bibliography.append("\\end{thebibliography}\n")
        return "".join(bibliography)

    def get_citation_map(self) -> Dict[str, int]:
        """
        Get mapping of citation_id to reference number

        Returns:
            Dictionary mapping citation_id to 1-indexed reference number
        """
        return {cid: i for i, cid in enumerate(self.citation_order, start=1)}

    def get_section_summary(self) -> Dict:
        """
        Get summary of reference distribution across sections

        Returns:
            Summary dictionary
        """
        summary = {
            "total_references": self.total_references,
            "sections": {}
        }

        for section, assignment in self.section_assignments.items():
            summary["sections"][section.value] = {
                "count": len(assignment.citation_ids),
                "range": f"{assignment.start_index}-{assignment.end_index}",
                "percentage": f"{len(assignment.citation_ids) / self.total_references * 100:.1f}%"
            }

        return summary


# Example usage
if __name__ == "__main__":
    # Simulate 30 citations
    citation_ids = [f"cit_{i:03d}" for i in range(1, 31)]

    agent = OrderedReferenceAgent()

    # Auto-assign references to sections
    assignments = agent.auto_assign_sections(citation_ids)

    print("=" * 60)
    print("ORDERED REFERENCE ASSIGNMENT")
    print("=" * 60)

    for section, assignment in assignments.items():
        print(f"\n{section.value.upper()}")
        print(f"  References: {assignment.start_index}-{assignment.end_index}")
        print(f"  Count: {len(assignment.citation_ids)}")
        print(f"  Citations: {', '.join(assignment.citation_ids[:3])}...")

    # Print summary
    print("\n" + "=" * 60)
    print("DISTRIBUTION SUMMARY")
    print("=" * 60)
    summary = agent.get_section_summary()
    for section, info in summary["sections"].items():
        print(f"{section}: {info['count']} refs ({info['percentage']}) - {info['range']}")
