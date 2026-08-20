"""Command-line entrypoint for the multi-agent research lab."""

from __future__ import annotations

import json
from functools import partial
from pathlib import Path
from typing import Annotated, Any

import typer
import yaml
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel

from multi_agent_research_lab.agents.researcher import ResearcherAgent
from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.errors import LabError
from multi_agent_research_lab.core.schemas import (
    AgentName,
    AgentResult,
    BenchmarkMetrics,
    ResearchQuery,
)
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import run_benchmark
from multi_agent_research_lab.evaluation.report import render_markdown_report
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.observability.logging import configure_logging
from multi_agent_research_lab.observability.tracing import configure_tracing, trace_span
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.offline_corpus import (
    OfflineCorpus,
    OfflineCorpusSearchClient,
    OfflineTopic,
)
from multi_agent_research_lab.services.search_client import SearchClient
from multi_agent_research_lab.services.storage import LocalArtifactStore

app = typer.Typer(help="Multi-Agent Research Lab CLI")
console = Console()


def _init() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    configure_tracing(settings)


def _parse_query(
    query: str,
    max_sources: int = 5,
    audience: str = "technical learners",
) -> ResearchQuery:
    try:
        return ResearchQuery(query=query, max_sources=max_sources, audience=audience)
    except ValidationError as exc:
        console.print(
            Panel.fit(
                f"Invalid query: {exc.errors()[0]['msg']}",
                title="Input Error",
                style="red",
            )
        )
        raise typer.Exit(code=1) from exc


def _citation_id(source: Any, index: int) -> str:
    value = source.metadata.get("citation_id")
    return str(value) if value else str(index)


def _run_baseline(
    query: str,
    *,
    search_client: SearchClient | None = None,
    max_sources: int = 5,
    audience: str = "technical learners",
) -> ResearchState:
    """Single agent: search once, then perform research+analysis+writing in one LLM call."""

    request = _parse_query(query, max_sources=max_sources, audience=audience)
    state = ResearchState(request=request)
    active_search_client = search_client or SearchClient()
    llm_client = LLMClient()

    with trace_span("baseline", {"query": query}) as span:
        state.sources = active_search_client.search(query, max_results=request.max_sources)
        source_context = "\n\n".join(
            (
                f"[{_citation_id(source, index)}] {source.title}\n"
                f"URL: {source.url or 'N/A'}\n"
                f"Synthetic: {bool(source.metadata.get('is_synthetic', False))}\n"
                f"Evidence: {source.snippet}"
            )
            for index, source in enumerate(state.sources, start=1)
        )
        response = llm_client.complete(
            system_prompt=(
                "You are a single-agent research assistant. In one pass, inspect the supplied "
                "sources, analyze them, and answer the user. Cite factual claims with the exact "
                "source ids shown in square brackets. Do not renumber or invent sources. Preserve "
                "synthetic-evidence labels and uncertainty."
            ),
            user_prompt=f"Question: {query}\nAudience: {audience}\n\nSources:\n{source_context}",
        )
        answer = response.content
        if state.sources:
            answer += "\n\nSources:\n" + "\n".join(
                (
                    f"[{_citation_id(source, index)}] {source.title} — "
                    f"{source.url or 'embedded offline evidence'}"
                )
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


def _run_multi(
    query: str,
    *,
    search_client: SearchClient | None = None,
    max_sources: int = 5,
    audience: str = "technical learners",
) -> ResearchState:
    request = _parse_query(query, max_sources=max_sources, audience=audience)
    if search_client is None:
        workflow = MultiAgentWorkflow()
    else:
        workflow = MultiAgentWorkflow(researcher=ResearcherAgent(search_client=search_client))
    return workflow.run(ResearchState(request=request))


def _load_benchmark_queries(path: Path) -> list[str]:
    payload: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    queries = payload.get("benchmark", {}).get("queries", [])
    return [str(query) for query in queries if str(query).strip()]


def _offline_report(
    topics: list[OfflineTopic],
    metrics: list[BenchmarkMetrics],
    max_sources: int,
) -> str:
    topic_lines = [
        "# Offline Corpus Benchmark Report",
        "",
        "This benchmark disables web search and retrieves evidence only from the mentor-provided "
        "offline corpus. Embedded `document_id`/`article_id` values are preserved as citation ids.",
        "",
        f"- Topics evaluated: {len(topics)}",
        f"- Max retrieved sources per run: {max_sources}",
        "- Corpus rubric: bundled 100-point rubric retained for human/LLM-judge review.",
        "",
        "## Topics",
        "",
    ]
    for topic in topics:
        topic_lines.extend(
            [
                f"### {topic.topic_id} — {topic.title}",
                "",
                f"**Research question:** {topic.research_question}",
                "",
                (
                    "**Rubric weight total:** "
                    f"{sum(int(item.get('weight', 0)) for item in topic.rubric)}"
                ),
                "",
            ]
        )
    quantitative = render_markdown_report(metrics).replace(
        "# Benchmark Report", "## Quantitative comparison", 1
    )
    return "\n".join(topic_lines) + quantitative


def _offline_result_record(
    topic: OfflineTopic,
    baseline_state: ResearchState,
    baseline_metrics: BenchmarkMetrics,
    multi_state: ResearchState,
    multi_metrics: BenchmarkMetrics,
) -> dict[str, Any]:
    return {
        "topic_id": topic.topic_id,
        "topic_number": topic.topic_number,
        "title": topic.title,
        "research_question": topic.research_question,
        "rubric": topic.rubric,
        "failure_conditions": topic.failure_conditions,
        "baseline": {
            "metrics": baseline_metrics.model_dump(),
            "final_answer": baseline_state.final_answer,
            "errors": baseline_state.errors,
        },
        "multi_agent": {
            "metrics": multi_metrics.model_dump(),
            "route_history": multi_state.route_history,
            "final_answer": multi_state.final_answer,
            "errors": multi_state.errors,
        },
    }


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


@app.command("offline-benchmark")
def offline_benchmark(
    topic: Annotated[
        str,
        typer.Option("--topic", "-t", help="Topic number, AIAGENT id, filename, or stem"),
    ] = "AIAGENT-01",
    all_topics: Annotated[
        bool,
        typer.Option("--all", help="Run all 30 topics; this can make many LLM calls"),
    ] = False,
    list_topics: Annotated[
        bool,
        typer.Option("--list-topics", help="List corpus topics and exit"),
    ] = False,
    corpus_root: Annotated[
        Path,
        typer.Option("--corpus-root", help="Offline corpus root directory"),
    ] = Path("data/offline_corpus"),
    max_sources: Annotated[
        int,
        typer.Option("--max-sources", help="Maximum embedded sources retrieved per run"),
    ] = 8,
) -> None:
    """Benchmark baseline vs multi-agent using only the mentor-provided offline corpus."""

    corpus = OfflineCorpus(corpus_root)
    try:
        available = corpus.list_topics()
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        console.print(Panel.fit(str(exc), title="Offline Corpus Error", style="red"))
        raise typer.Exit(code=1) from exc

    if list_topics:
        for topic_id, filename, title in available:
            console.print(f"{topic_id}: {title} ({filename})")
        return

    if not 1 <= max_sources <= 20:
        console.print(
            Panel.fit("--max-sources must be between 1 and 20.", title="Input Error", style="red")
        )
        raise typer.Exit(code=1)

    _init()
    if not get_settings().openai_api_key:
        console.print(
            Panel.fit(
                "OPENAI_API_KEY is required for the offline benchmark LLM calls.",
                title="Offline Benchmark Error",
                style="red",
            )
        )
        raise typer.Exit(code=2)

    try:
        topics = (
            [corpus.load_topic(topic_id) for topic_id, _, _ in available]
            if all_topics
            else [corpus.load_topic(topic)]
        )
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        console.print(Panel.fit(str(exc), title="Offline Corpus Error", style="red"))
        raise typer.Exit(code=1) from exc

    all_metrics: list[BenchmarkMetrics] = []
    records: list[dict[str, Any]] = []
    for current in topics:
        audience = str(current.payload["topic"].get("target_audience") or "technical learners")
        baseline_runner = partial(
            _run_baseline,
            search_client=OfflineCorpusSearchClient(current),
            max_sources=max_sources,
            audience=audience,
        )
        multi_runner = partial(
            _run_multi,
            search_client=OfflineCorpusSearchClient(current),
            max_sources=max_sources,
            audience=audience,
        )
        baseline_state, baseline_metrics = run_benchmark(
            f"baseline-{current.topic_id}", current.benchmark_query, baseline_runner
        )
        multi_state, multi_metrics = run_benchmark(
            f"multi-agent-{current.topic_id}", current.benchmark_query, multi_runner
        )
        all_metrics.extend([baseline_metrics, multi_metrics])
        records.append(
            _offline_result_record(
                current,
                baseline_state,
                baseline_metrics,
                multi_state,
                multi_metrics,
            )
        )
        console.print(
            f"Completed {current.topic_id}: baseline + multi-agent "
            f"({baseline_metrics.total_tokens or 0} / {multi_metrics.total_tokens or 0} tokens)"
        )

    store = LocalArtifactStore()
    report_path = store.write_text(
        "offline_benchmark_report.md",
        _offline_report(topics, all_metrics, max_sources),
    )
    result_path = store.write_text(
        "offline_benchmark_results.json",
        json.dumps(
            {
                "corpus_root": str(corpus_root),
                "max_sources": max_sources,
                "topics": records,
            },
            indent=2,
            ensure_ascii=False,
        ),
    )
    console.print(
        Panel.fit(
            f"Wrote {report_path}\nWrote {result_path}",
            title="Offline Benchmark Complete",
        )
    )


if __name__ == "__main__":
    app()
