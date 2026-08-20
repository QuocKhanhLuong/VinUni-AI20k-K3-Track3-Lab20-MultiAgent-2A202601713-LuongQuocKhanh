"""Benchmark helpers for single-agent vs multi-agent runs."""

from __future__ import annotations

import re
from collections.abc import Callable
from time import perf_counter

from multi_agent_research_lab.core.schemas import BenchmarkMetrics, ResearchQuery
from multi_agent_research_lab.core.state import ResearchState

Runner = Callable[[str], ResearchState]


def _token_totals(state: ResearchState) -> tuple[int | None, int | None, int | None]:
    input_values = [
        result.metadata.get("input_tokens")
        for result in state.agent_results
        if isinstance(result.metadata.get("input_tokens"), int)
    ]
    output_values = [
        result.metadata.get("output_tokens")
        for result in state.agent_results
        if isinstance(result.metadata.get("output_tokens"), int)
    ]
    input_tokens = sum(input_values) if input_values else None
    output_tokens = sum(output_values) if output_values else None
    total_tokens = (
        input_tokens + output_tokens
        if input_tokens is not None and output_tokens is not None
        else None
    )
    return input_tokens, output_tokens, total_tokens


def _estimated_cost(state: ResearchState) -> float | None:
    values = [
        result.metadata.get("cost_usd")
        for result in state.agent_results
        if isinstance(result.metadata.get("cost_usd"), int | float)
    ]
    return float(sum(values)) if values else None


def _citation_coverage(state: ResearchState) -> float | None:
    if not state.final_answer or not state.sources:
        return None
    body = state.final_answer.split("\n\nSources:", maxsplit=1)[0]
    cited = {int(match) for match in re.findall(r"\[(\d+)\]", body)}
    valid = {index for index in cited if 1 <= index <= len(state.sources)}
    return len(valid) / len(state.sources)


def _quality_proxy(state: ResearchState) -> float:
    """Deterministic 0-10 proxy; peer review remains the authoritative lab score."""

    if not state.final_answer:
        return 0.0
    score = 4.0
    answer = state.final_answer
    if len(answer) >= 250:
        score += 2.0
    if state.sources:
        score += 1.0
    coverage = _citation_coverage(state)
    if coverage is not None:
        score += 2.0 * coverage
    if not state.errors:
        score += 1.0
    return min(score, 10.0)


def run_benchmark(
    run_name: str, query: str, runner: Runner
) -> tuple[ResearchState, BenchmarkMetrics]:
    """Run one query and measure latency, token cost proxy, quality, and failures."""

    started = perf_counter()
    try:
        state = runner(query)
    except Exception as exc:
        latency = perf_counter() - started
        failed_state = ResearchState(
            request=ResearchQuery(query=query),
            errors=[str(exc)],
        )
        metrics = BenchmarkMetrics(
            run_name=run_name,
            latency_seconds=latency,
            quality_score=0.0,
            failure_rate=1.0,
            notes=f"failed: {type(exc).__name__}: {exc}",
        )
        return failed_state, metrics

    latency = perf_counter() - started
    input_tokens, output_tokens, total_tokens = _token_totals(state)
    metrics = BenchmarkMetrics(
        run_name=run_name,
        latency_seconds=latency,
        estimated_cost_usd=_estimated_cost(state),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        quality_score=_quality_proxy(state),
        citation_coverage=_citation_coverage(state),
        failure_rate=1.0 if state.errors or not state.final_answer else 0.0,
        notes="quality is an automated proxy; use peer rubric for final evaluation",
    )
    return state, metrics
