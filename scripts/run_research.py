#!/usr/bin/env python3
"""Run the ICML Research Team."""

import argparse
import json
from pathlib import Path

from icml_research.graph import build_research_graph
from icml_research.memory import HybridMemory


def run_research(
    query: str = None,
    year: int = None,
    target_papers: int = 5,
    use_memory: bool = True,
    output_dir: str = "./output",
):
    """Run the research team workflow."""

    # Initialize memory
    memory = HybridMemory() if use_memory else None

    # Build and run the graph
    graph = build_research_graph()

    initial_state = {
        "messages": [],
        "query": query or "",
        "year_filter": year,
        "discovered_papers": [],
        "current_paper": None,
        "paper_evaluation": None,
        "synthesis_insights": [],
        "research_roadmap": [],
        "memory_summary": "",
        "target_papers": target_papers,
    }

    print(f"Starting research team...")
    print(f"Query: {query or 'ICML papers'}")
    print(f"Target papers: {target_papers}")
    print("-" * 50)

    # Run the graph
    result = graph.invoke(initial_state)

    # Print results
    print("\n" + "=" * 60)
    print("RESEARCH TEAM RESULTS")
    print("=" * 60)

    # Discovered papers
    papers = result.get("discovered_papers", [])
    analyzed = [p for p in papers if p.get("full_text")]
    print(f"\n📚 Discovered: {len(papers)} papers")
    print(f"📖 Analyzed: {len(analyzed)} papers")

    if analyzed:
        print("\n--- Analyzed Papers ---")
        for p in analyzed:
            print(f"\n### {p['title']}")
            print(f"Authors: {', '.join(p['authors'])}")
            # Print first 500 chars of analysis
            analysis = p.get("full_text", "")[:500]
            print(f"Analysis: {analysis}...")

    # Evaluations
    eval_result = result.get("paper_evaluation")
    if eval_result:
        print("\n--- Latest Evaluation ---")
        print(eval_result.get("review", ""))

    # Synthesis insights
    insights = result.get("synthesis_insights", [])
    if insights:
        print("\n--- Synthesis Insights ---")
        for i, insight in enumerate(insights, 1):
            print(f"{i}. {insight}")

    # Save to memory
    if memory and analyzed:
        for p in analyzed:
            memory.store_paper(
                paper_id=p["paper_id"],
                title=p["title"],
                abstract=p["abstract"],
                authors=p["authors"],
                year=p.get("year", 2024),
                venue=p.get("venue", "arxiv"),
            )
        memory.save()
        print(f"\n💾 Saved {len(analyzed)} papers to memory")

    # Save output
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    output_data = {
        "query": query,
        "papers_analyzed": len(analyzed),
        "papers": [
            {
                "id": p["paper_id"],
                "title": p["title"],
                "authors": p["authors"],
                "analysis": p.get("full_text", ""),
            }
            for p in analyzed
        ],
        "synthesis_insights": insights,
    }

    output_file = output_path / "research_results.json"
    with open(output_file, "w") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\n📁 Results saved to: {output_file}")

    return result


def main():
    parser = argparse.ArgumentParser(description="ICML Research Team")
    parser.add_argument("--query", "-q", type=str, help="Search query for arXiv")
    parser.add_argument("--year", "-y", type=int, help="Filter by year")
    parser.add_argument("--target", "-t", type=int, default=5, help="Number of papers to analyze")
    parser.add_argument("--no-memory", action="store_true", help="Disable persistent memory")
    parser.add_argument("--output", "-o", type=str, default="./output", help="Output directory")

    args = parser.parse_args()

    run_research(
        query=args.query,
        year=args.year,
        target_papers=args.target,
        use_memory=not args.no_memory,
        output_dir=args.output,
    )


if __name__ == "__main__":
    main()
