"""Researcher agent: search first, then compress evidence into notes."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.search_client import SearchClient


class ResearcherAgent(BaseAgent):
    """Collect sources and create concise evidence-grounded research notes."""

    name = "researcher"

    def __init__(
        self,
        search_client: SearchClient | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self.search_client = search_client or SearchClient()
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate sources and research notes, preserving source identifiers."""

        with trace_span(self.name, {"query": state.request.query}) as span:
            sources = self.search_client.search(
                state.request.query,
                max_results=state.request.max_sources,
            )
            state.sources = sources
            source_context = "\n\n".join(
                f"[{index}] {source.title}\nURL: {source.url or 'N/A'}\nEvidence: {source.snippet}"
                for index, source in enumerate(sources, start=1)
            )
            response = self.llm_client.complete(
                system_prompt=(
                    "You are the Researcher in a multi-agent research system. Extract only claims "
                    "supported by the supplied sources. Keep source ids like [1], [2]. Highlight "
                    "uncertainty instead of inventing facts."
                ),
                user_prompt=(
                    f"Research question: {state.request.query}\n"
                    f"Audience: {state.request.audience}\n\nSources:\n{source_context}\n\n"
                    "Produce concise research notes with cited evidence."
                ),
            )
            state.research_notes = response.content
            metadata = {
                "source_count": len(sources),
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "cost_usd": response.cost_usd,
            }
            state.agent_results.append(
                AgentResult(agent=AgentName.RESEARCHER, content=response.content, metadata=metadata)
            )
            span["input_tokens"] = response.input_tokens
            span["output_tokens"] = response.output_tokens
            span["source_count"] = len(sources)
        state.add_trace_event(self.name, span)
        return state
