# Benchmark Report

The same query set is run through the single-agent baseline and the multi-agent workflow. `Total tokens` is always available as the cost proxy when provider token usage is returned. USD cost is shown only when model pricing is configured in `.env`.

| Run | Latency (s) | Input tok. | Output tok. | Total tok. | Cost (USD) | Quality* | Citation cov. | Failure rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline-q1 | 9.88 | 1565 | 581 | 2146 | n/a | 10.0 | 100% | 0% |
| multi-agent-q1 | 25.96 | 3715 | 2010 | 5725 | n/a | 9.6 | 80% | 0% |
| baseline-q2 | 6.36 | 1247 | 467 | 1714 | n/a | 10.0 | 100% | 0% |
| multi-agent-q2 | 26.63 | 2955 | 1646 | 4601 | n/a | 10.0 | 100% | 0% |
| baseline-q3 | 10.11 | 1404 | 486 | 1890 | n/a | 10.0 | 100% | 0% |
| multi-agent-q3 | 17.04 | 2945 | 1305 | 4250 | n/a | 10.0 | 100% | 0% |

## Comparison

- Mean latency: baseline 8.78s; multi-agent 23.21s.
- Mean token cost proxy: baseline 1917; multi-agent 4859 tokens.
- Mean automated quality proxy: baseline 10.0/10; multi-agent 9.9/10.

## Failure mode and fix

A common failure mode is **Supervisor ↔ worker looping** when a worker returns without filling the shared-state field that the router expects. The implementation fixes this with deterministic state-based routing, `max_iterations`, and an explicit `done` route. A second trade-off is that multi-agent execution usually adds latency and tokens because Researcher, Analyst, and Writer each call the model. That overhead is justified only when role separation improves grounding, debuggability, or answer quality.

*Quality is an automated regression proxy, not the final human rubric score. Replace or supplement it with peer-review 0-10 scoring for the submitted benchmark.
