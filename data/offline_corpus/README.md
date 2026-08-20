# AI Agent Offline Research Corpus Benchmark v2

This package contains 30 JSON files. Each file is designed to be a **self-contained offline knowledge corpus** for a research-report-writing benchmark. A multi-agent system should be able to plan, retrieve evidence, compare claims, verify citations, and write a substantive report **without internet search**.

## What changed from v1

The first version mainly contained prompts, source metadata, and short evidence packets. Version 2 embeds the knowledge itself. Each topic now contains:

- 7 long-form knowledge articles;
- 9 embedded source documents (6 public-reference knowledge summaries + 3 synthetic benchmark documents);
- at least 30 atomic facts with evidence IDs;
- a failure-mode library;
- 4 detailed synthetic case studies;
- 3 structured data tables;
- glossary and answerable research questions;
- design patterns and anti-patterns;
- the original research task, conflicts, agent roles, report specification, and 100-point rubric.

Average embedded prose per topic: approximately **4,869 words**, excluding structured facts, tables, rubric, and metadata.

## Source classes

`public_reference_summary` entries are paraphrased offline knowledge cards derived from well-known papers, benchmarks, standards, protocols, or engineering guidance. Their URLs are included only as provenance metadata; the benchmark agent does not need to open them.

Synthetic studies, cases, and tables are fictional benchmark evidence and always have `is_synthetic: true`. They exist so the benchmark can test evidence weighting, contradiction handling, and citation discipline.

## Suggested benchmark rule

Disable browser/web-search tools. Give the system one JSON topic file and allow retrieval only inside that file. Require the final report to cite embedded `source_id` or `article_id` values. Score it with the included rubric and separately record cost, latency, turns, retries, and tool calls.
