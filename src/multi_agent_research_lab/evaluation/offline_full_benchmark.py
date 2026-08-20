"""Run the full mentor offline corpus with baseline, multi-agent, and rubric judge."""

from __future__ import annotations

import argparse
import json
from functools import partial
from pathlib import Path
from statistics import mean
from typing import Any

from multi_agent_research_lab.cli import _init, _run_baseline, _run_multi
from multi_agent_research_lab.core.schemas import BenchmarkMetrics
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import run_benchmark
from multi_agent_research_lab.evaluation.report import render_markdown_report
from multi_agent_research_lab.evaluation.rubric_judge import RubricEvaluation, RubricJudge
from multi_agent_research_lab.services.offline_corpus import (
    OfflineCorpus,
    OfflineCorpusSearchClient,
    OfflineTopic,
)
from multi_agent_research_lab.services.storage import LocalArtifactStore


def _score(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1f}"


def _source_ids(state: ResearchState) -> list[str]:
    ids = []
    for index, source in enumerate(state.sources, start=1):
        value = source.metadata.get("citation_id")
        ids.append(str(value) if value else str(index))
    return ids


def _record(
    topic: OfflineTopic,
    baseline_state: ResearchState,
    baseline_metrics: BenchmarkMetrics,
    multi_state: ResearchState,
    multi_metrics: BenchmarkMetrics,
    rubric: RubricEvaluation,
) -> dict[str, Any]:
    return {
        "topic_id": topic.topic_id,
        "topic_number": topic.topic_number,
        "title": topic.title,
        "research_question": topic.research_question,
        "rubric": topic.rubric,
        "failure_conditions": topic.failure_conditions,
        "retrieved_source_ids": _source_ids(baseline_state),
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
        "rubric_judge": rubric.model_dump(),
    }


def _rubric_summary(records: list[dict[str, Any]]) -> list[str]:
    scored = [
        record
        for record in records
        if record["rubric_judge"]["baseline_score"] is not None
        and record["rubric_judge"]["multi_agent_score"] is not None
    ]
    lines = [
        "## Mentor rubric evaluation (/100)",
        "",
        (
            "A single comparative LLM-judge call scores both reports independently against the "
            "exact 100-point rubric embedded in each topic. Judge tokens are evaluation overhead "
            "and are not added to baseline or multi-agent system token totals."
        ),
        "",
    ]
    if not scored:
        lines.extend(["No rubric evaluations were parsed successfully.", ""])
        return lines

    baseline_scores = [record["rubric_judge"]["baseline_score"] for record in scored]
    multi_scores = [record["rubric_judge"]["multi_agent_score"] for record in scored]
    winners = [record["rubric_judge"]["winner"] for record in scored]
    judge_tokens = [
        record["rubric_judge"]["judge_total_tokens"]
        for record in scored
        if record["rubric_judge"]["judge_total_tokens"] is not None
    ]
    judge_latencies = [record["rubric_judge"]["judge_latency_seconds"] for record in scored]

    lines.extend(
        [
            f"- Successfully judged topics: {len(scored)}/{len(records)}",
            f"- Mean rubric score: baseline {mean(baseline_scores):.1f}/100; "
            f"multi-agent {mean(multi_scores):.1f}/100.",
            (
                "- Wins: "
                f"baseline {winners.count('baseline')}; "
                f"multi-agent {winners.count('multi-agent')}; ties {winners.count('tie')}."
            ),
            f"- Mean judge latency: {mean(judge_latencies):.2f}s/topic.",
        ]
    )
    if judge_tokens:
        lines.append(f"- Mean judge token overhead: {mean(judge_tokens):.0f} tokens/topic.")

    lines.extend(
        [
            "",
            "| Topic | Baseline /100 | Multi-agent /100 | Delta | Winner | Failure flags |",
            "|---|---:|---:|---:|---|---:|",
        ]
    )
    for record in records:
        judge = record["rubric_judge"]
        baseline = judge["baseline_score"]
        multi = judge["multi_agent_score"]
        delta = "n/a" if baseline is None or multi is None else f"{multi - baseline:+.1f}"
        failures = len(judge["baseline_failure_conditions"]) + len(
            judge["multi_agent_failure_conditions"]
        )
        lines.append(
            f"| {record['topic_id']} | {_score(baseline)} | {_score(multi)} | {delta} | "
            f"{judge['winner'] or 'n/a'} | {failures} |"
        )

    first_dimensions = scored[0]["rubric_judge"]["dimensions"]
    dimension_names = [item["dimension"] for item in first_dimensions]
    lines.extend(
        [
            "",
            "### Mean score by rubric dimension",
            "",
            "| Dimension | Weight | Baseline mean | Multi-agent mean | Delta |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for dimension in dimension_names:
        baseline_values = []
        multi_values = []
        weight = 0
        for record in scored:
            items = {
                item["dimension"]: item for item in record["rubric_judge"]["dimensions"]
            }
            item = items.get(dimension)
            if item is None:
                continue
            weight = int(item["weight"])
            baseline_values.append(float(item["baseline_score"]))
            multi_values.append(float(item["multi_agent_score"]))
        if not baseline_values or not multi_values:
            continue
        baseline_mean = mean(baseline_values)
        multi_mean = mean(multi_values)
        lines.append(
            f"| {dimension} | {weight} | {baseline_mean:.2f} | {multi_mean:.2f} | "
            f"{multi_mean - baseline_mean:+.2f} |"
        )
    lines.append("")
    return lines


def _render_report(
    topics: list[OfflineTopic],
    metrics: list[BenchmarkMetrics],
    records: list[dict[str, Any]],
    max_sources: int,
) -> str:
    lines = [
        "# Offline Corpus Benchmark Report",
        "",
        "This benchmark disables web search and retrieves evidence only from the mentor-provided "
        "offline corpus. Embedded `document_id`/`article_id` values are preserved as citation ids.",
        "",
        f"- Topics evaluated: {len(topics)}",
        f"- Max retrieved sources per run: {max_sources}",
        "- Mentor rubric: scored by a comparative LLM judge on the bundled 100-point rubric.",
        "",
    ]
    lines.extend(_rubric_summary(records))
    lines.extend(["## Topics", ""])
    for topic in topics:
        lines.extend(
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
    lines.append(quantitative)
    return "\n".join(lines)


def run_full(
    corpus_root: Path,
    max_sources: int,
    topic_id: str | None = None,
) -> None:
    """Run generation plus rubric evaluation for one topic or the full 30-topic corpus."""

    _init()
    corpus = OfflineCorpus(corpus_root)
    available = corpus.list_topics()
    topics = (
        [corpus.load_topic(topic_id)]
        if topic_id is not None
        else [corpus.load_topic(value) for value, _, _ in available]
    )

    judge = RubricJudge()
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
        rubric = judge.evaluate(current, baseline_state, multi_state)
        all_metrics.extend([baseline_metrics, multi_metrics])
        records.append(
            _record(
                current,
                baseline_state,
                baseline_metrics,
                multi_state,
                multi_metrics,
                rubric,
            )
        )
        print(
            f"Completed {current.topic_id}: tokens "
            f"{baseline_metrics.total_tokens or 0}/{multi_metrics.total_tokens or 0}; "
            f"rubric {_score(rubric.baseline_score)}/{_score(rubric.multi_agent_score)}"
        )

    store = LocalArtifactStore()
    report_path = store.write_text(
        "offline_benchmark_report.md",
        _render_report(topics, all_metrics, records, max_sources),
    )
    result_path = store.write_text(
        "offline_benchmark_results.json",
        json.dumps(
            {
                "corpus_root": str(corpus_root),
                "max_sources": max_sources,
                "rubric_judge": {
                    "mode": "single comparative LLM judge call per topic",
                    "score_scale": 100,
                    "judge_overhead_excluded_from_system_metrics": True,
                },
                "topics": records,
            },
            indent=2,
            ensure_ascii=False,
        ),
    )
    print(f"Wrote {report_path}")
    print(f"Wrote {result_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-root", type=Path, default=Path("data/offline_corpus"))
    parser.add_argument("--max-sources", type=int, default=8)
    parser.add_argument(
        "--topic",
        default=None,
        help="Optional topic id/number. Omit to run the full 30-topic corpus.",
    )
    args = parser.parse_args()
    if not 1 <= args.max_sources <= 20:
        parser.error("--max-sources must be between 1 and 20")
    run_full(args.corpus_root, args.max_sources, args.topic)


if __name__ == "__main__":
    main()
