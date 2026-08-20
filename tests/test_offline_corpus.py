from pathlib import Path

from multi_agent_research_lab.services.offline_corpus import (
    OfflineCorpus,
    OfflineCorpusSearchClient,
)


def test_offline_corpus_loads_all_topics() -> None:
    corpus = OfflineCorpus(Path("data/offline_corpus"))
    topics = corpus.list_topics()
    assert len(topics) == 30
    assert topics[0][0] == "AIAGENT-01"


def test_offline_topic_resolution_and_search_stay_local() -> None:
    corpus = OfflineCorpus(Path("data/offline_corpus"))
    topic = corpus.load_topic("1")
    assert topic.topic_id == "AIAGENT-01"
    assert topic.research_question
    assert sum(int(item.get("weight", 0)) for item in topic.rubric) == 100

    results = OfflineCorpusSearchClient(topic).search(topic.research_question, max_results=8)
    assert len(results) == 8
    assert all(item.metadata.get("provider") == "offline-corpus" for item in results)
    assert all(item.metadata.get("citation_id") for item in results)
    assert sum(
        item.metadata.get("document_class") == "public_reference_summary" for item in results
    ) >= 4
    assert any(item.metadata.get("is_synthetic") is True for item in results)
