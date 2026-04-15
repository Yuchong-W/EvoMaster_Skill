"""Hybrid memory system combining vector search and knowledge graph."""

import os
from pathlib import Path
from typing import Optional
import chromadb
from chromadb.config import Settings
import networkx as nx

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "memory"


class VectorStore:
    """ChromaDB-backed vector store for semantic search."""

    def __init__(self, collection_name: str = "papers", persist_dir: Optional[str] = None):
        persist_dir = persist_dir or str(DATA_DIR / "chromadb")
        os.makedirs(persist_dir, exist_ok=True)
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add(self, doc_id: str, text: str, metadata: dict):
        """Add a document."""
        self.collection.add(
            ids=[doc_id],
            documents=[text],
            metadatas=[metadata],
        )

    def search(self, query: str, n_results: int = 5) -> list[dict]:
        """Semantic search for similar documents."""
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
        )
        return [
            {
                "id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i],
            }
            for i in range(len(results["ids"][0]))
        ]

    def get(self, doc_id: str) -> Optional[dict]:
        """Retrieve a document by ID."""
        results = self.collection.get(ids=[doc_id])
        if results["ids"]:
            return {
                "id": results["ids"][0],
                "text": results["documents"][0],
                "metadata": results["metadatas"][0],
            }
        return None


class KnowledgeGraph:
    """NetworkX-backed knowledge graph for relationships."""

    def __init__(self, graph_name: str = "research_graph", persist_path: Optional[str] = None):
        persist_path = persist_path or str(DATA_DIR / f"{graph_name}.gpickle")
        self.persist_path = persist_path
        self.graph = nx.DiGraph()
        if os.path.exists(persist_path):
            self.graph = nx.read_gpickle(persist_path)

    def add_paper(self, paper_id: str, data: dict):
        """Add a paper node with metadata."""
        self.graph.add_node(paper_id, **data)

    def add_relationship(self, from_id: str, to_id: str, rel_type: str, weight: float = 1.0):
        """Add an edge (relationship) between two nodes."""
        self.graph.add_edge(from_id, to_id, relation=rel_type, weight=weight)

    def add_citation(self, from_paper: str, to_paper: str):
        """Add a citation relationship."""
        self.add_relationship(from_paper, to_paper, "cites")

    def get_paper(self, paper_id: str) -> Optional[dict]:
        """Get paper metadata."""
        if paper_id in self.graph:
            return dict(self.graph.nodes[paper_id])
        return None

    def get_references(self, paper_id: str) -> list[str]:
        """Get papers cited by this paper."""
        if paper_id in self.graph:
            return list(self.graph.successors(paper_id))
        return []

    def get_citations(self, paper_id: str) -> list[str]:
        """Get papers that cite this paper."""
        if paper_id in self.graph:
            return list(self.graph.predecessors(paper_id))
        return []

    def get_neighbors(self, paper_id: str, depth: int = 1) -> list[str]:
        """Get nearby nodes within N hops."""
        if paper_id not in self.graph:
            return []
        return list(nx.descendants(self.graph, paper_id))[:depth * 10]

    def save(self):
        """Persist the graph to disk."""
        nx.write_gpickle(self.graph, self.persist_path)

    def query_subgraph(self, paper_ids: list[str]) -> nx.DiGraph:
        """Extract a subgraph containing specific papers."""
        return self.graph.subgraph(paper_ids).copy()


class HybridMemory:
    """Combined vector + graph memory for research context."""

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        knowledge_graph: Optional[KnowledgeGraph] = None,
    ):
        self.vector = vector_store or VectorStore()
        self.graph = knowledge_graph or KnowledgeGraph()

    def store_paper(
        self,
        paper_id: str,
        title: str,
        abstract: str,
        authors: list[str],
        year: int,
        venue: str,
        citations: list[str] = None,
        references: list[str] = None,
    ):
        """Store a paper in both vector and graph stores."""
        # Vector store
        text = f"{title}\n\nAbstract: {abstract}"
        metadata = {
            "title": title,
            "authors": ",".join(authors),
            "year": year,
            "venue": venue,
        }
        self.vector.add(paper_id, text, metadata)

        # Knowledge graph
        self.graph.add_paper(paper_id, {
            "title": title,
            "authors": authors,
            "year": year,
            "venue": venue,
            "abstract": abstract,
        })

        # Add citation edges
        if citations:
            for cited in citations:
                self.graph.add_citation(paper_id, cited)
        if references:
            for ref in references:
                self.graph.add_citation(ref, paper_id)

    def search_papers(self, query: str, n_results: int = 10) -> list[dict]:
        """Search papers by semantic similarity."""
        return self.vector.search(query, n_results)

    def find_related(self, paper_id: str, depth: int = 2) -> list[dict]:
        """Find related papers via graph traversal."""
        neighbors = self.graph.get_neighbors(paper_id, depth)
        papers = []
        for nid in neighbors:
            paper_data = self.graph.get_paper(nid)
            if paper_data:
                papers.append({"id": nid, **paper_data})
        return papers

    def save(self):
        """Persist all memory to disk."""
        self.graph.save()
