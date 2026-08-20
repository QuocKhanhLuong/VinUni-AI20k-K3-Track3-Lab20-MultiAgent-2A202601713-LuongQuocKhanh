"""Writer agent: synthesize the final grounded answer."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.errors import ValidationError
from multi_agent_research_lab.core.schemas import AgentName, AgentResult, SourceDocument
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span
from multi_agent_research_lab.services.llm_client import LLMClient


def _citation_id(source: SourceDocument, index: int) -> str:
    value = source.metadata.get("citation_id")
    return str(value) if value else str(index)


class WriterAgent(BaseAgent):
    """Produce a readable answer from research and analysis notes."""

    name = "writer"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate final_answer with inline source ids and a source list."""

        if not state.research_notes or not state.analysis_notes:
            raise ValidationError("Writer requires both research_notes and analysis_notes.")

        source_ids = [
            _citation_id(source, index) for index, source in enumerate(state.sources, start=1)
        ]
        with trace_span(self.name, {"source_count": len(state.sources)}) as span:
            response = self.llm_client.complete(
                system_prompt=(
                    "You are the Writer in a multi-agent research system. Answer the user clearly "
                    "using only the supplied research and analysis. Cite factual claims inline "
                    "with the exact existing source ids in square brackets. Never fabricate or "
                    "renumber a citation. Preserve synthetic-evidence labels and uncertainty."
                ),
                user_prompt=(
                    f"Question: {state.request.query}\nAudience: {state.request.audience}\n"
                    f"Allowed citation ids: {source_ids}\n\n"
                    f"Research notes:\n{state.research_notes}\n\n"
                    f"Analysis notes:\n{state.analysis_notes}\n\n"
                    "Write the final answer."
                ),
            )
            answer = response.content.strip()
            if state.sources:
                source_lines = [
                    (
                        f"[{_citation_id(source, index)}] {source.title} — "
                        f"{source.url or 'embedded offline evidence'}"
                    )
                    for index, source in enumerate(state.sources, start=1)
                ]
                answer = f"{answer}\n\nSources:\n" + "\n".join(source_lines)
            state.final_answer = answer
            metadata = {
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "cost_usd": response.cost_usd,
            }
            state.agent_results.append(
                AgentResult(agent=AgentName.WRITER, content=answer, metadata=metadata)
            )
            span.update(metadata)
        state.add_trace_event(self.name, span)
        return state
