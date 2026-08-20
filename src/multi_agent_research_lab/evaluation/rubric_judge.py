"""LLM judge for the mentor-provided 100-point offline corpus rubric."""

from __future__ import annotations

import json
from time import perf_counter
from typing import Any, Literal

from pydantic import BaseModel, Field

from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.offline_corpus import OfflineTopic


class RubricDimensionScore(BaseModel):
    """Independent baseline and multi-agent scores for one rubric dimension."""

    dimension: str
    weight: int = Field(ge=1)
    baseline_score: float = Field(ge=0)
    multi_agent_score: float = Field(ge=0)
    baseline_rationale: str = ""
    multi_agent_rationale: str = ""


class RubricEvaluation(BaseModel):
    """Normalized 100-point mentor-rubric evaluation plus judge overhead."""

    baseline_score: float | None = Field(default=None, ge=0, le=100)
    multi_agent_score: float | None = Field(default=None, ge=0, le=100)
    winner: Literal["baseline", "multi-agent", "tie"] | None = None
    dimensions: list[RubricDimensionScore] = Field(default_factory=list)
    baseline_failure_conditions: list[str] = Field(default_factory=list)
    multi_agent_failure_conditions: list[str] = Field(default_factory=list)
    overall_rationale: str = ""
    judge_latency_seconds: float = Field(default=0.0, ge=0)
    judge_input_tokens: int | None = None
    judge_output_tokens: int | None = None
    judge_total_tokens: int | None = None
    judge_cost_usd: float | None = None
    error: str | None = None


class RubricJudge:
    """Score baseline and multi-agent answers in one comparative judge call."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    @staticmethod
    def _citation_id(source: Any, index: int) -> str:
        value = source.metadata.get("citation_id")
        return str(value) if value else str(index)

    def _evidence_context(
        self,
        baseline_state: ResearchState,
        multi_state: ResearchState,
    ) -> str:
        unique: dict[str, Any] = {}
        for state in (baseline_state, multi_state):
            for index, source in enumerate(state.sources, start=1):
                citation_id = self._citation_id(source, index)
                unique.setdefault(citation_id, source)

        blocks = []
        for citation_id, source in unique.items():
            metadata = source.metadata
            blocks.append(
                "\n".join(
                    [
                        f"[{citation_id}] {source.title}",
                        f"class={metadata.get('document_class') or 'unknown'}",
                        f"synthetic={bool(metadata.get('is_synthetic', False))}",
                        f"recommended_weight={metadata.get('recommended_weight') or 'n/a'}",
                        f"evidence={source.snippet[:1400]}",
                    ]
                )
            )
        return "\n\n".join(blocks)

    @staticmethod
    def _extract_json(text: str) -> dict[str, Any]:
        stripped = text.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            stripped = "\n".join(lines).strip()
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("judge response did not contain a JSON object")
        value = json.loads(stripped[start : end + 1])
        if not isinstance(value, dict):
            raise ValueError("judge response root must be a JSON object")
        return value

    @staticmethod
    def _normalize(
        topic: OfflineTopic,
        payload: dict[str, Any],
        *,
        latency: float,
        input_tokens: int | None,
        output_tokens: int | None,
        cost_usd: float | None,
    ) -> RubricEvaluation:
        raw_dimensions = payload.get("dimensions", [])
        by_name = {
            str(item.get("dimension")): item
            for item in raw_dimensions
            if isinstance(item, dict) and item.get("dimension")
        }
        dimensions: list[RubricDimensionScore] = []
        baseline_total = 0.0
        multi_total = 0.0

        for rubric_item in topic.rubric:
            dimension = str(rubric_item.get("dimension"))
            weight = int(rubric_item.get("weight", 0))
            raw = by_name.get(dimension, {})
            baseline_score = min(max(float(raw.get("baseline_score", 0.0)), 0.0), weight)
            multi_score = min(max(float(raw.get("multi_agent_score", 0.0)), 0.0), weight)
            baseline_total += baseline_score
            multi_total += multi_score
            dimensions.append(
                RubricDimensionScore(
                    dimension=dimension,
                    weight=weight,
                    baseline_score=baseline_score,
                    multi_agent_score=multi_score,
                    baseline_rationale=str(raw.get("baseline_rationale") or ""),
                    multi_agent_rationale=str(raw.get("multi_agent_rationale") or ""),
                )
            )

        delta = multi_total - baseline_total
        winner: Literal["baseline", "multi-agent", "tie"]
        if delta > 0.5:
            winner = "multi-agent"
        elif delta < -0.5:
            winner = "baseline"
        else:
            winner = "tie"

        total_tokens = (
            input_tokens + output_tokens
            if input_tokens is not None and output_tokens is not None
            else None
        )
        return RubricEvaluation(
            baseline_score=round(baseline_total, 2),
            multi_agent_score=round(multi_total, 2),
            winner=winner,
            dimensions=dimensions,
            baseline_failure_conditions=[
                str(value) for value in payload.get("baseline_failure_conditions", [])
            ],
            multi_agent_failure_conditions=[
                str(value) for value in payload.get("multi_agent_failure_conditions", [])
            ],
            overall_rationale=str(payload.get("overall_rationale") or ""),
            judge_latency_seconds=latency,
            judge_input_tokens=input_tokens,
            judge_output_tokens=output_tokens,
            judge_total_tokens=total_tokens,
            judge_cost_usd=cost_usd,
        )

    def evaluate(
        self,
        topic: OfflineTopic,
        baseline_state: ResearchState,
        multi_state: ResearchState,
    ) -> RubricEvaluation:
        """Evaluate both systems against the topic's exact bundled rubric."""

        rubric_json = json.dumps(topic.rubric, ensure_ascii=False, indent=2)
        failure_json = json.dumps(topic.failure_conditions, ensure_ascii=False, indent=2)
        task = topic.payload["research_task"]
        conflict_json = json.dumps(task.get("known_conflicts", []), ensure_ascii=False, indent=2)
        adversarial_json = json.dumps(
            task.get("adversarial_elements", []), ensure_ascii=False, indent=2
        )
        evidence_context = self._evidence_context(baseline_state, multi_state)
        baseline_answer = baseline_state.final_answer or ""
        multi_answer = multi_state.final_answer or ""
        multi_route = multi_state.route_history

        system_prompt = (
            "You are an impartial benchmark evaluator. Score TWO research reports independently "
            "against the exact weighted rubric supplied by the benchmark. Use only the supplied "
            "offline evidence. Do not reward the multi-agent report merely for using more agents. "
            "For the multi_agent_coordination dimension, judge the baseline on analogous process "
            "discipline, provenance, non-duplication, and verification appropriate to a single "
            "agent; never assign zero solely because it is single-agent. Treat synthetic evidence "
            "as synthetic, verify claim-citation alignment against the evidence cards, and trigger "
            "a failure condition only when it is clearly present. Return JSON only."
        )
        output_schema = {
            "dimensions": [
                {
                    "dimension": "exact rubric dimension name",
                    "baseline_score": "number from 0 to dimension weight",
                    "multi_agent_score": "number from 0 to dimension weight",
                    "baseline_rationale": "brief evidence-based rationale",
                    "multi_agent_rationale": "brief evidence-based rationale",
                }
            ],
            "baseline_failure_conditions": ["exact triggered failure condition"],
            "multi_agent_failure_conditions": ["exact triggered failure condition"],
            "overall_rationale": "short comparative explanation",
        }
        user_prompt = (
            f"Topic: {topic.topic_id} — {topic.title}\n"
            f"Research question: {topic.research_question}\n\n"
            f"RUBRIC (weights sum to 100):\n{rubric_json}\n\n"
            f"FAILURE CONDITIONS:\n{failure_json}\n\n"
            f"KNOWN CONFLICTS:\n{conflict_json}\n\n"
            f"ADVERSARIAL ELEMENTS:\n{adversarial_json}\n\n"
            f"OFFLINE EVIDENCE CARDS:\n{evidence_context}\n\n"
            "BASELINE PROCESS: one capable agent retrieves the same offline evidence and writes "
            "the report in one LLM pass.\n\n"
            f"BASELINE REPORT:\n{baseline_answer}\n\n"
            f"MULTI-AGENT PROCESS ROUTE: {multi_route}\n"
            "The multi-agent workflow uses Supervisor -> Researcher -> Analyst -> Writer with "
            "shared state and deterministic routing.\n\n"
            f"MULTI-AGENT REPORT:\n{multi_answer}\n\n"
            f"Return exactly this JSON shape, with one entry for EVERY rubric dimension:\n"
            f"{json.dumps(output_schema, ensure_ascii=False, indent=2)}"
        )

        started = perf_counter()
        total_input = 0
        total_output = 0
        total_cost = 0.0
        has_input = False
        has_output = False
        has_cost = False
        last_error: Exception | None = None

        for _ in range(2):
            response = self.llm_client.complete(
                system_prompt=system_prompt, user_prompt=user_prompt
            )
            if response.input_tokens is not None:
                total_input += response.input_tokens
                has_input = True
            if response.output_tokens is not None:
                total_output += response.output_tokens
                has_output = True
            if response.cost_usd is not None:
                total_cost += response.cost_usd
                has_cost = True
            try:
                payload = self._extract_json(response.content)
                return self._normalize(
                    topic,
                    payload,
                    latency=perf_counter() - started,
                    input_tokens=total_input if has_input else None,
                    output_tokens=total_output if has_output else None,
                    cost_usd=total_cost if has_cost else None,
                )
            except (TypeError, ValueError) as exc:
                last_error = exc

        return RubricEvaluation(
            judge_latency_seconds=perf_counter() - started,
            judge_input_tokens=total_input if has_input else None,
            judge_output_tokens=total_output if has_output else None,
            judge_total_tokens=(total_input + total_output) if has_input and has_output else None,
            judge_cost_usd=total_cost if has_cost else None,
            error=f"Rubric judge output could not be parsed after 2 attempts: {last_error}",
        )
