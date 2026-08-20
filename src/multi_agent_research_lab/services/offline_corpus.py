"""Offline corpus loader and lexical retrieval for mentor-provided benchmark topics."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from multi_agent_research_lab.core.schemas import SourceDocument
from multi_agent_research_lab.services.search_client import SearchClient

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "what",
    "when",
    "which",
    "with",
}


def _tokens(text: str) -> set[str]:
    return {token for token in _TOKEN_RE.findall(text.lower()) if token not in _STOP_WORDS}


@dataclass(frozen=True)
class OfflineTopic:
    """One self-contained mentor benchmark topic."""

    path: Path
    payload: dict[str, Any]

    @property
    def topic_id(self) -> str:
        return str(self.payload["benchmark_metadata"]["topic_id"])

    @property
    def topic_number(self) -> int:
        return int(self.payload["benchmark_metadata"]["topic_number"])

    @property
    def title(self) -> str:
        return str(self.payload["topic"]["name"])

    @property
    def research_question(self) -> str:
        return str(self.payload["topic"]["research_question"])

    @property
    def expected_report_length_words(self) -> int | None:
        value = self.payload["topic"].get("expected_report_length_words")
        return int(value) if isinstance(value, int | float) else None

    @property
    def benchmark_query(self) -> str:
        """Compose the topic question with the benchmark's report requirements."""

        task = self.payload["research_task"]
        subquestions = task.get("subquestions", [])
        expected_report = task.get("expected_report", {})
        sections = expected_report.get("required_sections", [])
        citation_rule = self.payload["offline_usage_instructions"].get(
            "recommended_citation_format",
            "Use embedded source ids in square brackets.",
        )
        lines = [
            self.research_question,
            "",
            "Offline benchmark constraints:",
            "- Use only evidence retrieved from the supplied offline corpus; do not use the web.",
            f"- Citation format: {citation_rule}.",
            "- Synthetic benchmark evidence must remain explicitly labeled synthetic.",
        ]
        if self.expected_report_length_words is not None:
            lines.append(
                f"- Target report length: about {self.expected_report_length_words} words."
            )
        if isinstance(subquestions, list) and subquestions:
            lines.extend(["", "Required subquestions:"])
            for item in subquestions:
                if isinstance(item, dict) and item.get("question"):
                    lines.append(f"- {item['question']}")
        if isinstance(sections, list) and sections:
            lines.extend(["", "Required report sections:"])
            lines.extend(f"- {section}" for section in sections)
        return "\n".join(lines)

    @property
    def rubric(self) -> list[dict[str, Any]]:
        value = self.payload["research_task"].get("evaluation_rubric", [])
        return value if isinstance(value, list) else []

    @property
    def failure_conditions(self) -> list[str]:
        value = self.payload["research_task"].get("failure_conditions", [])
        return [str(item) for item in value] if isinstance(value, list) else []


class OfflineCorpus:
    """Resolve and validate the 30 mentor-provided offline topic files."""

    REQUIRED_TOP_LEVEL = {
        "benchmark_metadata",
        "topic",
        "offline_usage_instructions",
        "knowledge_base",
        "research_task",
        "machine_schemas",
    }

    def __init__(self, root: Path = Path("data/offline_corpus")) -> None:
        self.root = root
        self.topics_dir = root / "topics"
        self.manifest_path = root / "manifest.csv"

    def _manifest_rows(self) -> list[dict[str, str]]:
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Offline corpus manifest not found: {self.manifest_path}")
        rows: list[dict[str, str]] = []
        with self.manifest_path.open(encoding="utf-8", newline="") as handle:
            for raw_row in csv.DictReader(handle):
                rows.append(
                    {
                        str(key): str(value or "")
                        for key, value in raw_row.items()
                        if key is not None
                    }
                )
        return rows

    def list_topics(self) -> list[tuple[str, str, str]]:
        """Return ``(topic_id, filename, title)`` tuples in manifest order."""

        return [
            (str(row["topic_id"]), str(row["filename"]), str(row["title"]))
            for row in self._manifest_rows()
        ]

    def load_topic(self, identifier: str | int) -> OfflineTopic:
        """Load by topic number, ``AIAGENT-XX`` id, filename, or filename stem."""

        raw = str(identifier).strip()
        normalized = raw.lower()
        numeric = raw.lstrip("0") if raw.isdigit() else None
        selected: dict[str, str] | None = None

        for row in self._manifest_rows():
            candidates = {
                str(row["topic_id"]).lower(),
                str(row["filename"]).lower(),
                Path(str(row["filename"])).stem.lower(),
            }
            if normalized in candidates:
                selected = row
                break
            if numeric is not None and str(row["topic_number"]).lstrip("0") == numeric:
                selected = row
                break

        if selected is None:
            raise ValueError(
                f"Unknown offline topic {raw!r}. Use --list-topics to see valid topic ids."
            )

        path = self.topics_dir / str(selected["filename"])
        if not path.exists():
            raise FileNotFoundError(f"Offline topic file not found: {path}")
        payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        missing = self.REQUIRED_TOP_LEVEL.difference(payload)
        if missing:
            raise ValueError(f"Offline topic {path.name} is missing keys: {sorted(missing)}")
        return OfflineTopic(path=path, payload=payload)


class OfflineCorpusSearchClient(SearchClient):
    """Search only the embedded evidence of one offline topic; never call the web."""

    def __init__(self, topic: OfflineTopic) -> None:
        self.topic = topic

    @staticmethod
    def _source_document(item: dict[str, Any]) -> SourceDocument:
        citation_id = str(
            item.get("document_id") or item.get("source_id") or item.get("citation_label")
        )
        takeaways = item.get("key_takeaways", [])
        takeaway_text = "\n".join(f"- {value}" for value in takeaways if str(value).strip())
        full_text = str(item.get("full_text") or "")
        synthetic = bool(item.get("is_synthetic", False))
        synthetic_note = (
            "SYNTHETIC BENCHMARK EVIDENCE: do not present this as a real publication.\n"
            if synthetic
            else ""
        )
        snippet = f"{synthetic_note}{takeaway_text}\n\n{full_text[:2200]}".strip()
        return SourceDocument(
            title=str(item.get("title") or citation_id),
            url=str(item["provenance_url"]) if item.get("provenance_url") else None,
            snippet=snippet,
            metadata={
                "provider": "offline-corpus",
                "citation_id": citation_id,
                "document_class": item.get("document_class"),
                "is_synthetic": synthetic,
                "recommended_weight": item.get("recommended_weight"),
            },
        )

    @staticmethod
    def _knowledge_article(item: dict[str, Any]) -> SourceDocument:
        citation_id = str(item.get("article_id") or "article")
        return SourceDocument(
            title=str(item.get("title") or citation_id),
            snippet=str(item.get("content") or "")[:2400],
            metadata={
                "provider": "offline-corpus",
                "citation_id": citation_id,
                "document_class": "knowledge_article",
                "is_synthetic": False,
                "recommended_for": item.get("recommended_for", []),
            },
        )

    @staticmethod
    def _score(query_tokens: set[str], document: SourceDocument) -> tuple[int, int, str]:
        title_tokens = _tokens(document.title)
        body_tokens = _tokens(document.snippet)
        lexical = 4 * len(query_tokens & title_tokens) + len(query_tokens & body_tokens)
        source_bonus = 2 if document.metadata.get("document_class") != "knowledge_article" else 0
        citation_id = str(document.metadata.get("citation_id") or document.title)
        return lexical + source_bonus, len(body_tokens), citation_id

    def search(self, query: str, max_results: int = 8) -> list[SourceDocument]:
        """Rank embedded source documents/articles with deterministic lexical overlap."""

        knowledge_base = self.topic.payload["knowledge_base"]
        documents = [
            self._source_document(item)
            for item in knowledge_base.get("source_documents", [])
            if isinstance(item, dict)
        ]
        documents.extend(
            self._knowledge_article(item)
            for item in knowledge_base.get("knowledge_articles", [])
            if isinstance(item, dict)
        )
        query_tokens = _tokens(query)
        ranked = sorted(
            documents,
            key=lambda document: self._score(query_tokens, document),
            reverse=True,
        )

        public_sources = [
            document
            for document in ranked
            if document.metadata.get("document_class") == "public_reference_summary"
        ]
        synthetic_sources = [
            document for document in ranked if document.metadata.get("is_synthetic") is True
        ]
        articles = [
            document
            for document in ranked
            if document.metadata.get("document_class") == "knowledge_article"
        ]

        selected: list[SourceDocument] = []
        public_quota = min(5, max_results)
        selected.extend(public_sources[:public_quota])
        if len(selected) < max_results and synthetic_sources:
            selected.append(synthetic_sources[0])
        if len(selected) < max_results and articles:
            selected.append(articles[0])
        for document in ranked:
            if len(selected) >= max_results:
                break
            if document not in selected:
                selected.append(document)
        return selected
