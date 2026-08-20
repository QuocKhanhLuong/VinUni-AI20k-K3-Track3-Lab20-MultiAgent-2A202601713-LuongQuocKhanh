import json
from pathlib import Path

from multi_agent_research_lab.core.schemas import ResearchQuery, SourceDocument
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.rubric_judge import RubricJudge
from multi_agent_research_lab.services.llm_client import LLMResponse
from multi_agent_research_lab.services.offline_corpus import OfflineTopic


class FakeJudgeLLM:
    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        assert "impartial benchmark evaluator" in system_prompt
        assert "BASELINE REPORT" in user_prompt
        payload = {
            "dimensions": [
                {
                    "dimension": "evidence",
                    "baseline_score": 35,
                    "multi_agent_score": 45,
                    "baseline_rationale": "Good evidence use.",
                    "multi_agent_rationale": "Better evidence use.",
                },
                {
                    "dimension": "clarity",
                    "baseline_score": 45,
                    "multi_agent_score": 48,
                    "baseline_rationale": "Clear.",
                    "multi_agent_rationale": "Clearer.",
                },
            ],
            "baseline_failure_conditions": [],
            "multi_agent_failure_conditions": [],
            "overall_rationale": "Multi-agent is stronger on this case.",
        }
        return LLMResponse(
            content=json.dumps(payload),
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.001,
        )


def _topic() -> OfflineTopic:
    payload = {
        "benchmark_metadata": {"topic_id": "AIAGENT-X", "topic_number": 1},
        "topic": {"name": "Test", "research_question": "Which report is better?"},
        "research_task": {
            "evaluation_rubric": [
                {"dimension": "evidence", "weight": 50, "full_credit": "Grounded."},
                {"dimension": "clarity", "weight": 50, "full_credit": "Clear."},
            ],
            "failure_conditions": [],
            "known_conflicts": [],
            "adversarial_elements": [],
        },
    }
    return OfflineTopic(path=Path("topic.json"), payload=payload)


def _state(answer: str) -> ResearchState:
    state = ResearchState(request=ResearchQuery(query="Which report is better?"))
    state.sources = [
        SourceDocument(
            title="Evidence",
            snippet="Grounded evidence.",
            metadata={"citation_id": "S1", "provider": "offline-corpus"},
        )
    ]
    state.final_answer = answer
    return state


def test_rubric_judge_scores_both_reports_in_one_call() -> None:
    result = RubricJudge(llm_client=FakeJudgeLLM()).evaluate(
        _topic(),
        _state("Baseline [S1]"),
        _state("Multi-agent [S1]"),
    )

    assert result.baseline_score == 80
    assert result.multi_agent_score == 93
    assert result.winner == "multi-agent"
    assert result.judge_total_tokens == 150
    assert result.error is None
