"""Command-line entrypoint for the multi-agent research lab."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer
import yaml
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.errors import LabError
from multi_agent_research_lab.core.schemas import AgentName, AgentResult, ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import run_benchmark
from multi_agent_research_lab.evaluation.report import render_markdown_report
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.observability.logging import configure_logging
from multi_agent_research_lab.observability.tracing import configure_tracing, trace_span
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.search_client import SearchClient
from multi_agent_research_lab.services.storage import LocalArtifactStore

app = typer.Typer(help="Multi-Agent Research Lab CLI")
console = Console()


def _init() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    configure_tracing(settings)


def _parse_query(query: str) -> ResearchQuery:
    try:
        return ResearchQuery(query=query)
    except ValidationError as exc:
        console.print(
            Panel.fit(
                f"Invalid query: {exc.errors()[0]['msg']}",
                title="Input Error",
                style="red",
            )
        )
        raise typer.Exit(code=1) from exc


def _run_baseline(query: str) -> ResearchState:
    """Single agent: search once, then perform research+analysis+writing in one LLM call."""

    request = _parse_query(query)
    state = ResearchState(request=request)
    search_client = SearchClient()
    llm_client = LLMClient()

    with trace_span("baseline", {"query": query}) as span:
        state.sources = search_client.search(query, max_results=request.max_sources)
        source_context = "\n\n".join(
            f"[{index}] {source.title}\nURL: {source.url or 'N/A'}\nEvidence: {source.snippet}"
            for index, source in enumerate(state.sources, start=1)
        )
        response = llm_client.complete(
            system_prompt=(
                "You are a single-agent research assistant. In one pass, inspect the supplied "
                "sources, analyze them, and answer the user. Cite factual claims with [1], [2], "
                "etc. Do not invent sources."
            ),
            user_prompt=f"Question: {query}\n\nSources:\n{source_context}",
        )
        answer = response.content
        if state.sources:
            answer += "\n\nSources:\n" + "\n".join(
                f"[{index}] {source.title} — {source.url or 'URL unavailable'}"
                for index, source in enumerate(state.sources, start=1)
            )
        state.final_answer = answer
        metadata = {
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "cost_usd": response.cost_usd,
            "source_count": len(state.sources),
        }
        state.agent_results.append(
            AgentResult(agent=AgentName.BASELINE, content=answer, metadata=metadata)
        )
        span.update(metadata)
    state.add_trace_event("baseline", span)
    return state


def _run_multi(query: str) -> ResearchState:
    request = _parse_query(query)
    return MultiAgentWorkflow().run(ResearchState(request=request))


def _load_benchmark_queries(path: Path) -> list[str]:
    payload: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    queries = payload.get("benchmark", {}).get("queries", [])
    return [str(query) for query in queries if str(query).strip()]


@app.command()
def baseline(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run the single-agent baseline with a real LLM call."""

    _init()
    try:
        state = _run_baseline(query)
    except LabError as exc:
        console.print(Panel.fit(str(exc), title="Baseline Error", style="red"))
        raise typer.Exit(code=2) from exc
    console.print(Panel.fit(state.final_answer or "", title="Single-Agent Baseline"))


@app.command("multi-agent")
def multi_agent(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run Supervisor -> Researcher -> Analyst -> Writer."""

    _init()
    try:
        result = _run_multi(query)
    except LabError as exc:
        console.print(Panel.fit(str(exc), title="Multi-Agent Error", style="red"))
        raise typer.Exit(code=2) from exc
    console.print(result.model_dump_json(indent=2))


@app.command()
def benchmark(
    config: Annotated[
        Path | None,
        typer.Option("--config", help="YAML file containing benchmark.queries"),
    ] = None,
) -> None:
    """Run the same query set through baseline and multi-agent and write the report."""

    _init()
    if not get_settings().openai_api_key:
        console.print(
            Panel.fit(
                "OPENAI_API_KEY is required for a submission-grade live benchmark.",
                title="Benchmark Error",
                style="red",
            )
        )
        raise typer.Exit(code=2)
    config_path = config or Path("configs/lab_default.yaml")
    queries = _load_benchmark_queries(config_path)
    if not queries:
        console.print(
            Panel.fit("No benchmark queries found.", title="Benchmark Error", style="red")
        )
        raise typer.Exit(code=1)

    all_metrics = []
    for index, query in enumerate(queries, start=1):
        _, baseline_metrics = run_benchmark(f"baseline-q{index}", query, _run_baseline)
        _, multi_metrics = run_benchmark(f"multi-agent-q{index}", query, _run_multi)
        all_metrics.extend([baseline_metrics, multi_metrics])

    report = render_markdown_report(all_metrics)
    path = LocalArtifactStore().write_text("benchmark_report.md", report)
    console.print(Panel.fit(f"Wrote {path}", title="Benchmark Complete"))


if __name__ == "__main__":
    app()
