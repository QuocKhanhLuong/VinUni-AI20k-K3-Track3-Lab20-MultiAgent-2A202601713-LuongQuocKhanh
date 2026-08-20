from multi_agent_research_lab.agents import (
    AnalystAgent,
    ResearcherAgent,
    SupervisorAgent,
    WriterAgent,
)
from multi_agent_research_lab.core.config import Settings
from multi_agent_research_lab.core.schemas import ResearchQuery, SourceDocument
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.services.llm_client import LLMResponse


class FakeSearchClient:
    def search(self, query: str, max_results: int = 5) -> list[SourceDocument]:
        del query
        return [
            SourceDocument(title="Source A", url="https://example.com/a", snippet="Evidence A"),
            SourceDocument(title="Source B", url="https://example.com/b", snippet="Evidence B"),
        ][:max_results]


class FakeLLMClient:
    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        del user_prompt
        if "Researcher" in system_prompt:
            content = "Finding A [1]. Finding B [2]."
        elif "Analyst" in system_prompt:
            content = "The two findings are complementary [1][2]."
        else:
            content = "Final grounded answer based on A [1] and B [2]. " * 8
        return LLMResponse(content=content, input_tokens=10, output_tokens=5, cost_usd=0.001)


def _state() -> ResearchState:
    return ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))


def test_supervisor_routes_from_missing_state_fields() -> None:
    supervisor = SupervisorAgent(Settings(max_iterations=6))
    state = _state()
    supervisor.run(state)
    assert state.route_history[-1] == "researcher"

    state.sources = [SourceDocument(title="A", snippet="evidence")]
    state.research_notes = "notes"
    supervisor.run(state)
    assert state.route_history[-1] == "analyst"

    state.analysis_notes = "analysis"
    supervisor.run(state)
    assert state.route_history[-1] == "writer"

    state.final_answer = "answer"
    supervisor.run(state)
    assert state.route_history[-1] == "done"


def test_workflow_runs_end_to_end_with_injected_clients() -> None:
    settings = Settings(max_iterations=6)
    fake_llm = FakeLLMClient()
    workflow = MultiAgentWorkflow(
        settings=settings,
        supervisor=SupervisorAgent(settings),
        researcher=ResearcherAgent(search_client=FakeSearchClient(), llm_client=fake_llm),
        analyst=AnalystAgent(llm_client=fake_llm),
        writer=WriterAgent(llm_client=fake_llm),
    )
    result = workflow.run(_state())

    assert result.route_history == ["researcher", "analyst", "writer", "done"]
    assert result.research_notes
    assert result.analysis_notes
    assert result.final_answer
    assert "[1]" in result.final_answer
    assert len(result.agent_results) == 3


def test_supervisor_stops_at_max_iterations() -> None:
    settings = Settings(max_iterations=1)
    supervisor = SupervisorAgent(settings)
    state = _state()
    state.iteration = 1
    supervisor.run(state)
    assert state.route_history[-1] == "done"
    assert state.errors
