# Benchmark Report

> **Live run required:** implementation is complete, but this repository must be executed once with a real `OPENAI_API_KEY` to record submission-grade latency/token/quality values. Run `make benchmark`; this file will be overwritten with measured results for all queries in `configs/lab_default.yaml`.

## Benchmark matrix

| Run | Latency (s) | Input tok. | Output tok. | Total tok. (cost proxy) | Cost (USD) | Quality* | Citation cov. | Failure rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline-q1 | pending | pending | pending | pending | optional | pending | pending | pending |
| multi-agent-q1 | pending | pending | pending | pending | optional | pending | pending | pending |
| baseline-q2 | pending | pending | pending | pending | optional | pending | pending | pending |
| multi-agent-q2 | pending | pending | pending | pending | optional | pending | pending | pending |
| baseline-q3 | pending | pending | pending | pending | optional | pending | pending | pending |
| multi-agent-q3 | pending | pending | pending | pending | optional | pending | pending | pending |

`Total tok.` is the always-available cost proxy requested by the lab. USD estimates are populated only if `OPENAI_INPUT_COST_PER_MILLION_USD` and `OPENAI_OUTPUT_COST_PER_MILLION_USD` are configured to match the selected model's current pricing.

## Failure mode and fix

A common failure mode is **Supervisor ↔ worker looping** when a worker returns without filling the shared-state field that the router expects. The implementation prevents this with deterministic state-based routing, `max_iterations`, and an explicit `done` route. Search failures also fall back to a labeled deterministic mock source set instead of leaving `sources` empty.

The expected trade-off is that multi-agent execution will usually be slower and consume more tokens because Researcher, Analyst, and Writer each call the LLM. It is only a win when specialization improves grounding, citation coverage, debuggability, or answer quality enough to justify that overhead.

*Quality in the automated benchmark is a deterministic regression proxy. For the final class submission, supplement it with the peer-review 0–10 rubric if required by the instructor.
