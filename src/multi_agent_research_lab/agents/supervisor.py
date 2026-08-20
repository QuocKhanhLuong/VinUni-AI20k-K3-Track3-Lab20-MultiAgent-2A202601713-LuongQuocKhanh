"""Deterministic supervisor/router for the research workflow."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.state import ResearchState


class SupervisorAgent(BaseAgent):
    """Route from shared-state completeness instead of spending another LLM call."""

    name = "supervisor"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def run(self, state: ResearchState) -> ResearchState:
        """Choose researcher, analyst, writer, or done and record the decision."""

        if state.iteration >= self.settings.max_iterations:
            route = "done"
            if state.final_answer is None:
                state.errors.append(
                    f"Guardrail stopped workflow at max_iterations={self.settings.max_iterations}."
                )
            state.route_history.append(route)
            state.add_trace_event(
                "supervisor",
                {"route": route, "reason": "max_iterations", "iteration": state.iteration},
            )
            return state

        if not state.sources or not state.research_notes:
            route = "researcher"
            reason = "research evidence missing"
        elif not state.analysis_notes:
            route = "analyst"
            reason = "analysis missing"
        elif not state.final_answer:
            route = "writer"
            reason = "final answer missing"
        else:
            route = "done"
            reason = "all required outputs present"

        state.record_route(route)
        state.add_trace_event(
            "supervisor",
            {"route": route, "reason": reason, "iteration": state.iteration},
        )
        return state
