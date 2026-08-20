"""Search client abstraction for the Researcher agent."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.schemas import SourceDocument


class SearchClient:
    """Use Tavily when configured, otherwise a transparent deterministic mock."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _mock_search(self, query: str, max_results: int) -> list[SourceDocument]:
        catalog = [
            SourceDocument(
                title="LangGraph overview",
                url="https://docs.langchain.com/oss/python/langgraph/overview",
                snippet=(
                    "LangGraph is a low-level orchestration framework for long-running, "
                    "stateful agents with graph-based control flow."
                ),
                metadata={"provider": "mock", "query": query},
            ),
            SourceDocument(
                title="Building effective agents",
                url="https://www.anthropic.com/engineering/building-effective-agents",
                snippet=(
                    "Agentic systems benefit from simple composable patterns, clear tool use, "
                    "and adding complexity only when it improves outcomes."
                ),
                metadata={"provider": "mock", "query": query},
            ),
            SourceDocument(
                title="OpenAI agent orchestration",
                url="https://developers.openai.com/api/docs/guides/agents/orchestration",
                snippet=(
                    "Agent orchestration coordinates specialized responsibilities and handoffs "
                    "while preserving context and control."
                ),
                metadata={"provider": "mock", "query": query},
            ),
            SourceDocument(
                title="LangSmith tracing",
                url="https://docs.langchain.com/langsmith/observability-quickstart",
                snippet=(
                    "Tracing records application runs, nested calls, latency, inputs, outputs, "
                    "and metadata for debugging agent workflows."
                ),
                metadata={"provider": "mock", "query": query},
            ),
        ]
        return catalog[:max_results]

    def search(self, query: str, max_results: int = 5) -> list[SourceDocument]:
        """Search Tavily, falling back to local mock sources when unavailable."""

        if not self.settings.tavily_api_key:
            return self._mock_search(query, max_results)

        payload = json.dumps(
            {
                "api_key": self.settings.tavily_api_key,
                "query": query,
                "max_results": max_results,
                "search_depth": "basic",
                "include_answer": False,
            }
        ).encode("utf-8")
        request = Request(
            "https://api.tavily.com/search",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.settings.timeout_seconds) as response:
                body: dict[str, Any] = json.loads(response.read().decode("utf-8"))
            documents = [
                SourceDocument(
                    title=str(item.get("title") or "Untitled source"),
                    url=str(item["url"]) if item.get("url") else None,
                    snippet=str(item.get("content") or item.get("snippet") or ""),
                    metadata={
                        "provider": "tavily",
                        "score": item.get("score"),
                    },
                )
                for item in body.get("results", [])[:max_results]
            ]
            return documents or self._mock_search(query, max_results)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
            fallback = self._mock_search(query, max_results)
            for item in fallback:
                item.metadata["provider"] = "mock-fallback"
            return fallback
