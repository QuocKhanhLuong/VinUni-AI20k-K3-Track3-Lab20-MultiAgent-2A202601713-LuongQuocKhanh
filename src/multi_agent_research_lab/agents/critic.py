"""Optional critic agent for citation and hallucination checks."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.errors import ValidationError
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span
from multi_agent_research_lab.services.llm_client import LLMClient


class CriticAgent(BaseAgent):
    """Review a completed answer without rewriting the primary workflow output."""

    name = "critic"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Append a fact-check result to agent_results and trace."""

        if not state.final_answer:
            raise ValidationError("Critic requires final_answer before it can run.")

        with trace_span(self.name, {"source_count": len(state.sources)}) as span:
            response = self.llm_client.complete(
                system_prompt=(
                    "Audit the supplied answer against the supplied evidence. Flag unsupported "
                    "claims, citation mismatches, and important uncertainty. Do not add new facts."
                ),
                user_prompt=(
                    f"Answer:\n{state.final_answer}\n\nEvidence:\n{state.research_notes or ''}"
                ),
            )
            metadata = {
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "cost_usd": response.cost_usd,
            }
            state.agent_results.append(
                AgentResult(agent=AgentName.CRITIC, content=response.content, metadata=metadata)
            )
            span.update(metadata)
        state.add_trace_event(self.name, span)
        return state
