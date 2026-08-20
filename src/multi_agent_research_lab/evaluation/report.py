"""Benchmark report rendering."""

from statistics import mean

from multi_agent_research_lab.core.schemas import BenchmarkMetrics


def _display(value: float | None, digits: int = 2) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def render_markdown_report(metrics: list[BenchmarkMetrics]) -> str:
    """Render quantitative results plus an explicit trade-off/failure analysis."""

    lines = [
        "# Benchmark Report",
        "",
        "The same query set is run through the single-agent baseline and the multi-agent "
        "workflow. `Total tokens` is always available as the cost proxy when provider token "
        "usage is returned. USD cost is shown only when model pricing is configured in `.env`.",
        "",
        (
            "| Run | Latency (s) | Input tok. | Output tok. | Total tok. | Cost (USD) | "
            "Quality* | Citation cov. | Failure rate |"
        ),
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in metrics:
        input_tokens = "n/a" if item.input_tokens is None else str(item.input_tokens)
        output_tokens = "n/a" if item.output_tokens is None else str(item.output_tokens)
        total_tokens = "n/a" if item.total_tokens is None else str(item.total_tokens)
        citation = "n/a" if item.citation_coverage is None else f"{item.citation_coverage:.0%}"
        failure = "n/a" if item.failure_rate is None else f"{item.failure_rate:.0%}"
        lines.append(
            f"| {item.run_name} | {item.latency_seconds:.2f} | {input_tokens} | "
            f"{output_tokens} | {total_tokens} | {_display(item.estimated_cost_usd, 4)} | "
            f"{_display(item.quality_score, 1)} | {citation} | {failure} |"
        )

    baseline = [item for item in metrics if item.run_name.startswith("baseline")]
    multi = [item for item in metrics if item.run_name.startswith("multi-agent")]
    lines.extend(["", "## Comparison", ""])
    if baseline and multi:
        lines.append(
            f"- Mean latency: baseline {mean(item.latency_seconds for item in baseline):.2f}s; "
            f"multi-agent {mean(item.latency_seconds for item in multi):.2f}s."
        )
        baseline_tokens = [item.total_tokens for item in baseline if item.total_tokens is not None]
        multi_tokens = [item.total_tokens for item in multi if item.total_tokens is not None]
        if baseline_tokens and multi_tokens:
            lines.append(
                f"- Mean token cost proxy: baseline {mean(baseline_tokens):.0f}; "
                f"multi-agent {mean(multi_tokens):.0f} tokens."
            )
        baseline_quality = [
            item.quality_score for item in baseline if item.quality_score is not None
        ]
        multi_quality = [item.quality_score for item in multi if item.quality_score is not None]
        if baseline_quality and multi_quality:
            lines.append(
                f"- Mean automated quality proxy: baseline {mean(baseline_quality):.1f}/10; "
                f"multi-agent {mean(multi_quality):.1f}/10."
            )
    else:
        lines.append("Live comparison has not been run yet.")

    lines.extend(
        [
            "",
            "## Failure mode and fix",
            "",
            (
                "A common failure mode is **Supervisor ↔ worker looping** when a worker returns "
                "without filling the shared-state field that the router expects. The "
                "implementation "
                "fixes this with deterministic state-based routing, `max_iterations`, and an "
                "explicit `done` route. A second trade-off is that multi-agent execution usually "
                "adds latency and tokens because Researcher, Analyst, and Writer each call the "
                "model. That overhead is justified only when role separation improves grounding, "
                "debuggability, or answer quality."
            ),
            "",
            (
                "*Quality is an automated regression proxy, not the final human rubric score. "
                "Replace or supplement it with peer-review 0-10 scoring for the submitted "
                "benchmark."
            ),
            "",
        ]
    )
    return "\n".join(lines)
