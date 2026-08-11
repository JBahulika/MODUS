"""Enterprise transformation research workflow graph."""

from __future__ import annotations

import operator
from typing import Annotated, Any, Callable, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.company import research_company
from app.agents.competitor import research_competitors
from app.agents.industry import research_industry
from app.agents.news import research_news
from app.agents.opportunity import research_opportunities
from app.agents.planner import plan_research
from app.agents.risk import research_risks
from app.agents.synthesizer import synthesize_report


ProgressCallback = Callable[[str, str], None]


class ResearchState(TypedDict, total=False):
    query: str
    job_id: str
    plan: dict[str, Any]
    company: dict[str, Any]
    industry: dict[str, Any]
    news: dict[str, Any]
    competitors: dict[str, Any]
    opportunities: dict[str, Any]
    risks: dict[str, Any]
    report: dict[str, Any]
    errors: Annotated[list[str], operator.add]
    events: Annotated[list[dict[str, str]], operator.add]


def build_graph(on_progress: ProgressCallback | None = None):
    def emit(step: str, message: str) -> dict[str, Any]:
        if on_progress:
            on_progress(step, message)
        return {"events": [{"step": step, "message": message}]}

    def subject(state: ResearchState) -> str:
        plan = state.get("plan") or {}
        return str(plan.get("subject") or state["query"])

    def planner_node(state: ResearchState) -> dict[str, Any]:
        query = state["query"]
        base = emit("planning", f"Planning transformation research...")
        plan = plan_research(query)
        return {**base, "plan": plan, "query": plan.get("query") or query}

    def company_node(state: ResearchState) -> dict[str, Any]:
        base = emit("company", "Gathering company and operating context...")
        try:
            data = research_company(state["query"], subject=subject(state))
            return {**base, "company": data}
        except Exception as exc:
            return {**base, "company": {}, "errors": [f"company: {exc}"]}

    def industry_node(state: ResearchState) -> dict[str, Any]:
        base = emit("industry", "Researching industry transformation signals...")
        try:
            plan = state.get("plan") or {}
            data = research_industry(
                state["query"],
                subject=subject(state),
                industry_hint=plan.get("industry_hint"),
            )
            return {**base, "industry": data}
        except Exception as exc:
            return {**base, "industry": {}, "errors": [f"industry: {exc}"]}

    def news_node(state: ResearchState) -> dict[str, Any]:
        base = emit("news", "Fetching recent AI and transformation news...")
        try:
            data = research_news(state["query"], subject=subject(state))
            return {**base, "news": data}
        except Exception as exc:
            return {**base, "news": {}, "errors": [f"news: {exc}"]}

    def competitor_node(state: ResearchState) -> dict[str, Any]:
        base = emit("competitors", "Comparing competitor AI moves...")
        try:
            data = research_competitors(
                state["query"],
                subject=subject(state),
                company_data=state.get("company"),
                industry_data=state.get("industry"),
                news_data=state.get("news"),
            )
            return {**base, "competitors": data}
        except Exception as exc:
            return {**base, "competitors": {}, "errors": [f"competitors: {exc}"]}

    def opportunity_node(state: ResearchState) -> dict[str, Any]:
        base = emit("opportunity", "Identifying AI opportunity areas...")
        try:
            data = research_opportunities(
                state["query"],
                subject=subject(state),
                company_data=state.get("company"),
                industry_data=state.get("industry"),
            )
            return {**base, "opportunities": data}
        except Exception as exc:
            return {**base, "opportunities": {}, "errors": [f"opportunity: {exc}"]}

    def risk_node(state: ResearchState) -> dict[str, Any]:
        base = emit("risk", "Running risk and governance check...")
        try:
            data = research_risks(
                state["query"],
                subject=subject(state),
                company_data=state.get("company"),
                industry_data=state.get("industry"),
                news_data=state.get("news"),
                competitor_data=state.get("competitors"),
                opportunity_data=state.get("opportunities"),
            )
            return {**base, "risks": data}
        except Exception as exc:
            return {**base, "risks": {}, "errors": [f"risk: {exc}"]}

    def synthesizer_node(state: ResearchState) -> dict[str, Any]:
        base = emit("summarizing", "Synthesizing transformation brief...")
        try:
            report = synthesize_report(
                query=state["query"],
                plan=state.get("plan") or {},
                company=state.get("company") or {},
                industry=state.get("industry") or {},
                news=state.get("news") or {},
                competitors=state.get("competitors") or {},
                opportunities=state.get("opportunities") or {},
                risks=state.get("risks") or {},
            )
            done = emit("done", "Brief ready.")
            return {
                "events": base["events"] + done["events"],
                "report": report,
            }
        except Exception as exc:
            fail = emit("error", f"Synthesizer failed: {exc}")
            return {
                "events": base["events"] + fail["events"],
                "errors": [f"synthesizer: {exc}"],
                "report": {"query": state["query"], "error": str(exc)},
            }

    graph = StateGraph(ResearchState)
    graph.add_node("planner", planner_node)
    graph.add_node("company", company_node)
    graph.add_node("industry", industry_node)
    graph.add_node("news", news_node)
    graph.add_node("competitors", competitor_node)
    graph.add_node("opportunity", opportunity_node)
    graph.add_node("risk", risk_node)
    graph.add_node("synthesizer", synthesizer_node)

    graph.add_edge(START, "planner")
    # First wave: company, industry, news in parallel
    graph.add_edge("planner", "company")
    graph.add_edge("planner", "industry")
    graph.add_edge("planner", "news")
    # Second wave: competitors + opportunities after first wave
    graph.add_edge(["company", "industry", "news"], "competitors")
    graph.add_edge(["company", "industry", "news"], "opportunity")
    # Risk after second wave, then synthesize
    graph.add_edge(["competitors", "opportunity"], "risk")
    graph.add_edge("risk", "synthesizer")
    graph.add_edge("synthesizer", END)

    return graph.compile()


def run_research(
    query: str,
    job_id: str = "",
    on_progress: ProgressCallback | None = None,
) -> dict[str, Any]:
    app = build_graph(on_progress=on_progress)
    final = app.invoke(
        {
            "query": query,
            "job_id": job_id,
            "errors": [],
            "events": [],
        }
    )
    return final
