"""LangGraph workflow for Supervisor -> Researcher -> Analyst -> Writer."""

from __future__ import annotations

import importlib
from typing import Any, TypedDict

from multi_agent_research_lab.agents.analyst import AnalystAgent
from multi_agent_research_lab.agents.researcher import ResearcherAgent
from multi_agent_research_lab.agents.supervisor import SupervisorAgent
from multi_agent_research_lab.agents.writer import WriterAgent
from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.state import ResearchState


class _WorkflowState(TypedDict):
    state: ResearchState


class _SequentialGraph:
    """Offline-compatible fallback used when the optional LangGraph extra is absent."""

    def __init__(self, workflow: MultiAgentWorkflow) -> None:
        self.workflow = workflow

    def invoke(
        self, payload: _WorkflowState, config: dict[str, Any] | None = None
    ) -> _WorkflowState:
        del config
        state = payload["state"]
        while True:
            state = self.workflow.supervisor.run(state)
            route = state.route_history[-1]
            if route == "done":
                break
            if route == "researcher":
                state = self.workflow.researcher.run(state)
            elif route == "analyst":
                state = self.workflow.analyst.run(state)
            elif route == "writer":
                state = self.workflow.writer.run(state)
            else:
                state.errors.append(f"Unknown route: {route}")
                break
        return {"state": state}


class MultiAgentWorkflow:
    """Build and execute a guarded LangGraph research workflow."""

    def __init__(
        self,
        settings: Settings | None = None,
        supervisor: SupervisorAgent | None = None,
        researcher: ResearcherAgent | None = None,
        analyst: AnalystAgent | None = None,
        writer: WriterAgent | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.supervisor = supervisor or SupervisorAgent(self.settings)
        self.researcher = researcher or ResearcherAgent()
        self.analyst = analyst or AnalystAgent()
        self.writer = writer or WriterAgent()

    def _supervisor_node(self, payload: _WorkflowState) -> _WorkflowState:
        return {"state": self.supervisor.run(payload["state"])}

    def _researcher_node(self, payload: _WorkflowState) -> _WorkflowState:
        return {"state": self.researcher.run(payload["state"])}

    def _analyst_node(self, payload: _WorkflowState) -> _WorkflowState:
        return {"state": self.analyst.run(payload["state"])}

    def _writer_node(self, payload: _WorkflowState) -> _WorkflowState:
        return {"state": self.writer.run(payload["state"])}

    @staticmethod
    def _route_after_supervisor(payload: _WorkflowState) -> str:
        history = payload["state"].route_history
        return history[-1] if history else "done"

    def build(self) -> Any:
        """Create LangGraph nodes, conditional edges, and a stop condition."""

        try:
            graph_module = importlib.import_module("langgraph.graph")
        except ImportError:
            return _SequentialGraph(self)

        state_graph = graph_module.StateGraph(_WorkflowState)
        state_graph.add_node("supervisor", self._supervisor_node)
        state_graph.add_node("researcher", self._researcher_node)
        state_graph.add_node("analyst", self._analyst_node)
        state_graph.add_node("writer", self._writer_node)
        state_graph.add_edge(graph_module.START, "supervisor")
        state_graph.add_conditional_edges(
            "supervisor",
            self._route_after_supervisor,
            {
                "researcher": "researcher",
                "analyst": "analyst",
                "writer": "writer",
                "done": graph_module.END,
            },
        )
        state_graph.add_edge("researcher", "supervisor")
        state_graph.add_edge("analyst", "supervisor")
        state_graph.add_edge("writer", "supervisor")
        return state_graph.compile()

    def run(self, state: ResearchState) -> ResearchState:
        """Execute the compiled graph and return the final validated state."""

        graph = self.build()
        recursion_limit = max(25, self.settings.max_iterations * 4)
        result = graph.invoke({"state": state}, config={"recursion_limit": recursion_limit})
        final_state = result["state"]
        if isinstance(final_state, ResearchState):
            return final_state
        return ResearchState.model_validate(final_state)
