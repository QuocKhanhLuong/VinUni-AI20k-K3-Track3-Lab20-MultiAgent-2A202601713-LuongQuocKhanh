"""Tracing hooks with a local span and optional LangSmith export."""

from __future__ import annotations

import importlib
import os
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from time import perf_counter
from typing import Any

from multi_agent_research_lab.core.config import Settings


def configure_tracing(settings: Settings) -> None:
    """Configure LangSmith environment variables when a key is supplied."""

    if settings.langsmith_api_key:
        os.environ.setdefault("LANGSMITH_TRACING", "true")
        os.environ.setdefault("LANGSMITH_API_KEY", settings.langsmith_api_key)
        os.environ.setdefault("LANGSMITH_PROJECT", settings.langsmith_project)


@contextmanager
def trace_span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[dict[str, Any]]:
    """Record local timing and mirror the span to LangSmith when available."""

    started = perf_counter()
    span: dict[str, Any] = {
        "name": name,
        "attributes": attributes or {},
        "duration_seconds": None,
    }
    with ExitStack() as stack:
        if os.getenv("LANGSMITH_TRACING", "").lower() in {"1", "true", "yes"}:
            try:
                langsmith = importlib.import_module("langsmith")
                trace = getattr(langsmith, "trace", None)
                if trace is not None:
                    stack.enter_context(
                        trace(name, run_type="chain", inputs=attributes or {})
                    )
            except (ImportError, AttributeError, TypeError):
                trace = None
        try:
            yield span
        finally:
            span["duration_seconds"] = perf_counter() - started
