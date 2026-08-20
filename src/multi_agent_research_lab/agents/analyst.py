"""Analyst agent: compare claims and assess evidence quality."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.errors import ValidationError
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span
from multi_agent_research_lab.services.llm_client import LLMClient


class AnalystAgent(BaseAgent):
    """Turn research notes into structured, source-aware analysis."""

    name = "analyst"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate analysis notes from previously gathered research evidence."""

        if not state.research_notes:
            raise ValidationError("Analyst requires research_notes before it can run.")

        with trace_span(self.name, {"source_count": len(state.sources)}) as span:
            response = self.llm_client.complete(
                system_prompt=(
                    "You are the Analyst in a multi-agent research system. Compare claims, detect "
                    "agreement or conflict, assess evidence strength, and preserve citation ids. "
                    "Do not introduce facts absent from the research notes."
                ),
                user_prompt=(
                    f"Question: {state.request.query}\n\nResearch notes:\n"
                    f"{state.research_notes}\n\nReturn structured analysis with key findings, "
                    "trade-offs, weak evidence, and remaining uncertainty."
                ),
            )
            state.analysis_notes = response.content
            metadata = {
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "cost_usd": response.cost_usd,
            }
            state.agent_results.append(
                AgentResult(agent=AgentName.ANALYST, content=response.content, metadata=metadata)
            )
            span.update(metadata)
        state.add_trace_event(self.name, span)
        return state
