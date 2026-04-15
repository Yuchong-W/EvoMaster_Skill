"""Tools for paper discovery and analysis."""

import re
import urllib.parse
from typing import Optional
import httpx
import arxiv


def search_arxiv(query: str, max_results: int = 50, category: str = "cs.AI") -> list[dict]:
    """Search arXiv for papers matching a query."""
    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance,
    )

    papers = []
    for result in client.results(search):
        papers.append({
            "id": result.entry_id.split("/")[-1],
            "title": result.title,
            "abstract": result.summary,
            "authors": [a.name for a in result.authors],
            "published": result.published.isoformat(),
            "updated": result.updated.isoformat(),
            "categories": result.categories,
            "pdf_url": result.pdf_url,
            "comment": result.comment,
            "doi": result.doi,
        })
    return papers


def get_icml_papers(year: Optional[int] = None, max_results: int = 100) -> list[dict]:
    """Get papers from ICML (stat.ML category)."""
    query_parts = ["cat:stat.ML", "cat:cs.LG"]
    if year:
        query_parts.append(f"abs_date_first:[{year}0101 TO {year}1231]")
    query = " OR ".join(query_parts)

    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )

    papers = []
    for result in client.results(search):
        # Filter for ICML if possible
        if "ICML" in str(result.categories) or "International Conference on Machine Learning" in (result.comment or ""):
            papers.append({
                "id": result.entry_id.split("/")[-1],
                "title": result.title,
                "abstract": result.summary,
                "authors": [a.name for a in result.authors],
                "published": result.published.isoformat(),
                "categories": result.categories,
                "pdf_url": result.pdf_url,
                "venue": "ICML",
            })
    return papers


def download_pdf(paper_id: str, output_dir: str = "./data/papers") -> str:
    """Download a paper's PDF."""
    import os
    os.makedirs(output_dir, exist_ok=True)

    client = arxiv.Client()
    search = arxiv.Search(id_list=[paper_id])
    result = list(client.results(search))[0]

    output_path = os.path.join(output_dir, f"{paper_id}.pdf")
    result.download_pdf(output_dir, filename=f"{paper_id}.pdf")
    return output_path


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text content from PDF."""
    import fitz  # pymupdf
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text
