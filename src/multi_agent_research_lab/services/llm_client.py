"""Provider-agnostic LLM client used by all agents."""

from __future__ import annotations

import importlib
import os
import time
from dataclasses import dataclass
from typing import Any

from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.errors import AgentExecutionError


@dataclass(frozen=True)
class LLMResponse:
    content: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


class LLMClient:
    """Small OpenAI-backed client with retry, timeout, token, and cost logging."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._openai_client: Any | None = None

    def _build_client(self) -> Any:
        if self._openai_client is not None:
            return self._openai_client
        if not self.settings.openai_api_key:
            raise AgentExecutionError(
                "OPENAI_API_KEY is missing. Copy .env.example to .env and configure a provider key."
            )

        try:
            openai = importlib.import_module("openai")
        except ImportError as exc:
            raise AgentExecutionError(
                'OpenAI SDK is not installed. Run `pip install -e ".[dev,llm]"`.'
            ) from exc

        client = openai.OpenAI(
            api_key=self.settings.openai_api_key,
            timeout=self.settings.timeout_seconds,
        )

        if self.settings.langsmith_api_key:
            os.environ.setdefault("LANGSMITH_TRACING", "true")
            os.environ.setdefault("LANGSMITH_API_KEY", self.settings.langsmith_api_key)
            os.environ.setdefault("LANGSMITH_PROJECT", self.settings.langsmith_project)
            try:
                wrappers = importlib.import_module("langsmith.wrappers")
            except (ImportError, AttributeError):
                wrappers = None
            if wrappers is not None:
                client = wrappers.wrap_openai(client)

        self._openai_client = client
        return client

    def _estimate_cost(self, input_tokens: int | None, output_tokens: int | None) -> float | None:
        input_rate = self.settings.openai_input_cost_per_million_usd
        output_rate = self.settings.openai_output_cost_per_million_usd
        if (
            input_rate is None
            or output_rate is None
            or input_tokens is None
            or output_tokens is None
        ):
            return None
        return (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Call the configured chat model and return a structured response."""

        client = self._build_client()
        last_error: Exception | None = None

        for attempt in range(3):
            try:
                response = client.chat.completions.create(
                    model=self.settings.openai_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.2,
                )
                content = response.choices[0].message.content or ""
                usage = getattr(response, "usage", None)
                input_tokens = getattr(usage, "prompt_tokens", None) if usage else None
                output_tokens = getattr(usage, "completion_tokens", None) if usage else None
                return LLMResponse(
                    content=content.strip(),
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=self._estimate_cost(input_tokens, output_tokens),
                )
            except Exception as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(0.5 * (2**attempt))

        raise AgentExecutionError(
            f"LLM request failed after 3 attempts: {last_error}"
        ) from last_error
