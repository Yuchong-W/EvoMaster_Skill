"""LangGraph-based research team orchestration."""

import operator
from typing import Annotated, Sequence
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from ..agents.definitions import ResearchState, Paper, SCOUT_PROMPT, READER_PROMPT, REVIEWER_PROMPT, SYNTHESIZER_PROMPT
from ..llm import ChatGLM5
from ..tools.arxiv import search_arxiv, get_icml_papers


# === LLM Instances ===
llm_scout = ChatGLM5()
llm_reader = ChatGLM5()
llm_reviewer = ChatGLM5()
llm_synthesizer = ChatGLM5()


# === Agent Functions ===

def scout_papers(state: ResearchState) -> ResearchState:
    """Discover papers from arXiv based on query."""
    query = state.get("query", "")
    year = state.get("year_filter", None)

    if query:
        # Search by query
        raw_papers = search_arxiv(query, max_results=50)
    else:
        # Get ICML papers directly
        raw_papers = get_icml_papers(year=year, max_results=100)

    # Convert to Paper objects
    papers = []
    for p in raw_papers:
        papers.append(Paper(
            paper_id=p["id"],
            title=p["title"],
            abstract=p["abstract"],
            authors=p["authors"],
            year=p.get("year", 2024),
            venue=p.get("venue", "arxiv"),
            pdf_url=p.get("pdf_url", ""),
            full_text="",
        ))

    return {
        "discovered_papers": papers,
        "messages": state["messages"] + [
            {"role": "assistant", "content": f"Discovered {len(papers)} papers"}
        ]
    }


def filter_relevant_papers(state: ResearchState) -> ResearchState:
    """Filter papers to keep only the most relevant ones using LLM."""
    papers = state.get("discovered_papers", [])
    if not papers:
        return state

    # Quick LLM-based filtering using title+abstract
    keep_papers = []
    for paper in papers[:30]:  # Limit to 30 for cost
        prompt = f"""Based on this paper's title and abstract, rate its relevance to the research query: {state.get('query', 'machine learning optimization')}

Title: {paper['title']}
Abstract: {paper['abstract'][:500]}

Respond with only YES or NO."""

        response = llm_scout.invoke([{"role": "user", "content": prompt}])
        if "YES" in response.content.upper()[:10]:
            keep_papers.append(paper)

    return {
        "discovered_papers": keep_papers,
        "messages": state["messages"] + [
            {"role": "assistant", "content": f"Filtered to {len(keep_papers)} relevant papers"}
        ]
    }


def analyze_paper(state: ResearchState) -> ResearchState:
    """Deep analyze a single paper."""
    papers = state.get("discovered_papers", [])
    if not papers:
        return state

    # Pick the first unanalyzed paper
    current = state.get("current_paper")
    if current:
        # Find next
        analyzed_ids = {p["paper_id"] for p in papers if p.get("full_text")}
        for p in papers:
            if p["paper_id"] not in analyzed_ids:
                current = p
                break
    else:
        current = papers[0]

    # Deep read with LLM
    prompt = f"""{READER_PROMPT}

Paper Title: {current['title']}
Paper Abstract: {current['abstract']}
Authors: {', '.join(current['authors'])}

Provide a thorough analysis:"""

    response = llm_reader.invoke([{"role": "user", "content": prompt}])

    analysis_text = response.content

    # Update paper with full analysis
    updated_paper = {**current, "full_text": analysis_text}

    # Update discovered papers list
    updated_papers = []
    for p in papers:
        if p["paper_id"] == current["paper_id"]:
            updated_papers.append(updated_paper)
        else:
            updated_papers.append(p)

    return {
        "current_paper": updated_paper,
        "discovered_papers": updated_papers,
        "messages": state["messages"] + [
            {"role": "assistant", "content": f"Analyzed paper: {current['title']}"}
        ]
    }


def evaluate_paper(state: ResearchState) -> ResearchState:
    """Evaluate a paper across multiple dimensions."""
    current = state.get("current_paper")
    if not current or not current.get("full_text"):
        return state

    prompt = f"""{REVIEWER_PROMPT}

Paper: {current['title']}

Analysis: {current['full_text'][:3000]}

Provide your evaluation:"""

    response = llm_reviewer.invoke([{"role": "user", "content": prompt}])

    return {
        "paper_evaluation": {
            "paper_id": current["paper_id"],
            "review": response.content,
        },
        "messages": state["messages"] + [
            {"role": "assistant", "content": f"Evaluated: {current['title']}"}
        ]
    }


def synthesize_insights(state: ResearchState) -> ResearchState:
    """Synthesize insights from all analyzed papers."""
    papers = [p for p in state.get("discovered_papers", []) if p.get("full_text")]
    if len(papers) < 2:
        return state

    papers_text = "\n\n---\n\n".join([
        f"## {p['title']}\n{p['full_text'][:1500]}"
        for p in papers
    ])

    prompt = f"""{SYNTHESIZER_PROMPT}

Analyzed Papers:
{papers_text}

Generate cross-paper insights and research directions:"""

    response = llm_synthesizer.invoke([{"role": "user", "content": prompt}])

    insights = [l.strip() for l in response.content.split("\n") if l.strip()]

    return {
        "synthesis_insights": insights,
        "messages": state["messages"] + [
            {"role": "assistant", "content": f"Generated {len(insights)} synthesis insights"}
        ]
    }


def should_continue_analysis(state: ResearchState) -> str:
    """Decide whether to continue analyzing more papers."""
    analyzed = len([p for p in state.get("discovered_papers", []) if p.get("full_text")])
    target = state.get("target_papers", 5)

    if analyzed >= target:
        return "synthesize"
    return "analyze"


def build_research_graph():
    """Build the LangGraph research workflow."""

    workflow = StateGraph(ResearchState)

    # Add nodes
    workflow.add_node("scout", scout_papers)
    workflow.add_node("filter", filter_relevant_papers)
    workflow.add_node("analyze", analyze_paper)
    workflow.add_node("evaluate", evaluate_paper)
    workflow.add_node("synthesize", synthesize_insights)

    # Set entry point
    workflow.set_entry_point("scout")

    # Add edges
    workflow.add_edge("scout", "filter")
    workflow.add_edge("filter", "analyze")
    workflow.add_edge("analyze", "evaluate")
    workflow.add_edge("evaluate", "analyze")

    # Conditional edge: continue analyzing or synthesize
    workflow.add_conditional_edges(
        "evaluate",
        should_continue_analysis,
        {
            "analyze": "analyze",
            "synthesize": "synthesize",
        }
    )

    workflow.add_edge("synthesize", END)

    return workflow.compile()
