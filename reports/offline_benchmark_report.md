# Offline Corpus Benchmark Report

This benchmark disables web search and retrieves evidence only from the mentor-provided offline corpus. Embedded `document_id`/`article_id` values are preserved as citation ids.

- Topics evaluated: 30
- Max retrieved sources per run: 8
- Mentor rubric: scored by a comparative LLM judge on the bundled 100-point rubric.

## Mentor rubric evaluation (/100)

A single comparative LLM-judge call scores both reports independently against the exact 100-point rubric embedded in each topic. Judge tokens are evaluation overhead and are not added to baseline or multi-agent system token totals.

- Successfully judged topics: 30/30
- Mean rubric score: baseline 96.8/100; multi-agent 92.9/100.
- Wins: baseline 22; multi-agent 6; ties 2.
- Mean judge latency: 10.25s/topic.
- Mean judge token overhead: 6496 tokens/topic.

| Topic | Baseline /100 | Multi-agent /100 | Delta | Winner | Failure flags |
|---|---:|---:|---:|---|---:|
| AIAGENT-01 | 97.0 | 97.0 | +0.0 | tie | 0 |
| AIAGENT-02 | 98.0 | 95.0 | -3.0 | baseline | 0 |
| AIAGENT-03 | 98.0 | 100.0 | +2.0 | multi-agent | 0 |
| AIAGENT-04 | 98.0 | 78.0 | -20.0 | baseline | 1 |
| AIAGENT-05 | 98.0 | 100.0 | +2.0 | multi-agent | 0 |
| AIAGENT-06 | 95.0 | 85.0 | -10.0 | baseline | 1 |
| AIAGENT-07 | 98.0 | 92.0 | -6.0 | baseline | 0 |
| AIAGENT-08 | 98.0 | 95.0 | -3.0 | baseline | 0 |
| AIAGENT-09 | 98.0 | 100.0 | +2.0 | multi-agent | 0 |
| AIAGENT-10 | 98.0 | 97.0 | -1.0 | baseline | 0 |
| AIAGENT-11 | 100.0 | 95.0 | -5.0 | baseline | 0 |
| AIAGENT-12 | 98.0 | 95.0 | -3.0 | baseline | 0 |
| AIAGENT-13 | 98.0 | 83.0 | -15.0 | baseline | 1 |
| AIAGENT-14 | 98.0 | 97.0 | -1.0 | baseline | 0 |
| AIAGENT-15 | 98.0 | 97.0 | -1.0 | baseline | 0 |
| AIAGENT-16 | 98.0 | 97.0 | -1.0 | baseline | 0 |
| AIAGENT-17 | 98.0 | 84.0 | -14.0 | baseline | 0 |
| AIAGENT-18 | 98.0 | 100.0 | +2.0 | multi-agent | 0 |
| AIAGENT-19 | 97.0 | 84.0 | -13.0 | baseline | 1 |
| AIAGENT-20 | 98.0 | 95.0 | -3.0 | baseline | 0 |
| AIAGENT-21 | 98.0 | 100.0 | +2.0 | multi-agent | 0 |
| AIAGENT-22 | 98.0 | 97.0 | -1.0 | baseline | 0 |
| AIAGENT-23 | 100.0 | 100.0 | +0.0 | tie | 0 |
| AIAGENT-24 | 82.0 | 80.0 | -2.0 | baseline | 0 |
| AIAGENT-25 | 98.0 | 84.0 | -14.0 | baseline | 1 |
| AIAGENT-26 | 98.0 | 93.0 | -5.0 | baseline | 0 |
| AIAGENT-27 | 81.0 | 79.0 | -2.0 | baseline | 0 |
| AIAGENT-28 | 95.0 | 100.0 | +5.0 | multi-agent | 0 |
| AIAGENT-29 | 98.0 | 91.0 | -7.0 | baseline | 0 |
| AIAGENT-30 | 98.0 | 96.0 | -2.0 | baseline | 0 |

### Mean score by rubric dimension

| Dimension | Weight | Baseline mean | Multi-agent mean | Delta |
|---|---:|---:|---:|---:|
| question_decomposition | 10 | 9.87 | 9.87 | +0.00 |
| source_quality_reasoning | 15 | 14.80 | 13.80 | -1.00 |
| claim_citation_alignment | 15 | 14.87 | 13.87 | -1.00 |
| conflict_resolution | 10 | 9.87 | 9.70 | -0.17 |
| multi_agent_coordination | 10 | 7.87 | 9.13 | +1.27 |
| technical_depth | 15 | 14.70 | 12.63 | -2.07 |
| evaluation_design | 10 | 9.93 | 9.23 | -0.70 |
| safety_governance | 5 | 4.93 | 4.93 | +0.00 |
| report_structure_and_clarity | 5 | 4.97 | 4.87 | -0.10 |
| uncertainty_calibration | 5 | 4.97 | 4.83 | -0.13 |

## Topics

### AIAGENT-01 — Single-Agent vs Multi-Agent Architectures for Complex Research Tasks

**Research question:** When does a multi-agent architecture produce better research reports than a single capable agent, after accounting for quality, cost, latency, and coordination failure?

**Rubric weight total:** 100

### AIAGENT-02 — Role Specialization in Multi-Agent Systems

**Research question:** How should roles such as planner, researcher, critic, fact-checker, and synthesizer be allocated in an LLM multi-agent research team?

**Rubric weight total:** 100

### AIAGENT-03 — Centralized Orchestrators vs Decentralized Agent Coordination

**Research question:** What are the trade-offs between a central supervisor agent and decentralized peer-to-peer coordination for long research workflows?

**Rubric weight total:** 100

### AIAGENT-04 — Planning Strategies: ReAct, Plan-and-Execute, and Search-Based Reasoning

**Research question:** How should an agent choose between interleaved ReAct-style reasoning, explicit plan-and-execute, and search over multiple candidate reasoning paths?

**Rubric weight total:** 100

### AIAGENT-05 — Reflection and Self-Correction Loops in Language Agents

**Research question:** Under what conditions do reflection loops improve agent reliability, and when do they merely reinforce an incorrect trajectory?

**Rubric weight total:** 100

### AIAGENT-06 — Long-Term Memory Architectures for AI Agents

**Research question:** What memory architecture best supports long-lived agents: full-history context, summarization, vector retrieval, episodic stores, or hierarchical memory?

**Rubric weight total:** 100

### AIAGENT-07 — Tool Selection and Reliable API Use by Autonomous Agents

**Research question:** How can agents decide when to call tools, choose the right tool, validate arguments, and recover from tool errors without excessive retries?

**Rubric weight total:** 100

### AIAGENT-08 — Retrieval-Augmented Research Agents and Evidence Grounding

**Research question:** How should a research agent retrieve, rank, cross-check, and cite external evidence while preventing weak retrieval from dominating synthesis?

**Rubric weight total:** 100

### AIAGENT-09 — MCP and A2A for Agent Interoperability

**Research question:** How do Model Context Protocol and Agent2Agent address different layers of an agent ecosystem, and what architecture is needed when both are used?

**Rubric weight total:** 100

### AIAGENT-10 — Shared State and Context Engineering in Multi-Agent Systems

**Research question:** What information should be shared among agents, summarized, isolated, or made immutable during collaborative research?

**Rubric weight total:** 100

### AIAGENT-11 — Debate, Voting, and Conflict Resolution Between Agents

**Research question:** Do debate and voting protocols improve factual accuracy and reasoning quality in multi-agent systems, and how should disagreements be resolved?

**Rubric weight total:** 100

### AIAGENT-12 — Critic and Verifier Agents for Research Report Quality

**Research question:** How should verifier agents check claims, citations, calculations, and logical consistency without becoming redundant with the primary researcher?

**Rubric weight total:** 100

### AIAGENT-13 — Cascading Hallucinations in Multi-Agent Pipelines

**Research question:** Why can multi-agent chains amplify fabricated facts, and which architectural controls reduce error propagation?

**Rubric weight total:** 100

### AIAGENT-14 — Long-Horizon Task Reliability and Recovery

**Research question:** What mechanisms allow agents to recover from local failures without losing the overall goal during long, multi-step tasks?

**Rubric weight total:** 100

### AIAGENT-15 — Web-Browsing Agents for Open-Ended Research

**Research question:** How should browsing agents navigate websites, assess source credibility, and maintain task state during open-ended research?

**Rubric weight total:** 100

### AIAGENT-16 — Software Engineering Agents and Multi-Agent Coding Teams

**Research question:** When do specialized coding agents outperform a single coding agent on issue resolution, design, implementation, review, and testing?

**Rubric weight total:** 100

### AIAGENT-17 — Embodied and Environment-Interacting Agents

**Research question:** What lessons from embodied agents generalize to digital research and enterprise agents?

**Rubric weight total:** 100

### AIAGENT-18 — AI Agents for Scientific Literature Research

**Research question:** How should a multi-agent system conduct a scientific literature review while preserving citation fidelity, uncertainty, and methodological nuance?

**Rubric weight total:** 100

### AIAGENT-19 — Autonomous Data Analysis Agents

**Research question:** How should agents combine code execution, data profiling, statistical checks, visualization, and narrative synthesis in a trustworthy analysis workflow?

**Rubric weight total:** 100

### AIAGENT-20 — Enterprise Multi-Agent Workflow Automation

**Research question:** What architectural patterns are appropriate for deploying multi-agent systems across enterprise tools, approvals, and long-running workflows?

**Rubric weight total:** 100

### AIAGENT-21 — Human-in-the-Loop Control for Agentic Systems

**Research question:** Where should human review be inserted in an agent workflow to maximize safety and quality without eliminating automation benefits?

**Rubric weight total:** 100

### AIAGENT-22 — Cost, Latency, and Parallelism in Multi-Agent Research

**Research question:** How should a multi-agent system trade off more agents and parallel searches against inference cost, latency, and marginal quality improvement?

**Rubric weight total:** 100

### AIAGENT-23 — Observability, Tracing, and Debugging of Agent Systems

**Research question:** What should be logged and traced to diagnose failures in a multi-agent pipeline without exposing unnecessary sensitive data?

**Rubric weight total:** 100

### AIAGENT-24 — Prompt Injection and Tool Poisoning Against Autonomous Agents

**Research question:** How can agents distinguish trusted instructions from malicious content encountered in webpages, retrieved documents, tool metadata, or messages from other agents?

**Rubric weight total:** 100

### AIAGENT-25 — Privacy and Sensitive-Data Leakage in Multi-Agent Systems

**Research question:** How do multi-agent architectures change the privacy risk of prompts, memories, tool outputs, and inter-agent messages?

**Rubric weight total:** 100

### AIAGENT-26 — Least Privilege, Sandboxing, and Action Authorization

**Research question:** How should autonomous agents be permissioned when they can execute code, modify files, call APIs, or transact with external services?

**Rubric weight total:** 100

### AIAGENT-27 — Benchmarks and Metrics for Evaluating AI Agents

**Research question:** Which metrics best capture agent quality beyond final-answer accuracy, especially for long-horizon and multi-agent workflows?

**Rubric weight total:** 100

### AIAGENT-28 — Reproducibility and Regression Testing for Agent Pipelines

**Research question:** How can teams regression-test stochastic multi-agent workflows when models, tools, websites, and prompts all change?

**Rubric weight total:** 100

### AIAGENT-29 — Governance and Risk Management for Agentic AI

**Research question:** How should organizations adapt AI governance to systems that plan, delegate, call tools, maintain memory, and act over long periods?

**Rubric weight total:** 100

### AIAGENT-30 — Future Agent Ecosystems: Open Standards, Marketplaces, and Cross-Vendor Collaboration

**Research question:** What technical and governance challenges emerge as agents from different vendors discover one another, negotiate capabilities, and collaborate across organizational boundaries?

**Rubric weight total:** 100

## Quantitative comparison

The same query set is run through the single-agent baseline and the multi-agent workflow. `Total tokens` is always available as the cost proxy when provider token usage is returned. USD cost is shown only when model pricing is configured in `.env`.

| Run | Latency (s) | Input tok. | Output tok. | Total tok. | Cost (USD) | Quality* | Citation cov. | Failure rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline-AIAGENT-01 | 14.16 | 3831 | 746 | 4577 | n/a | 10.0 | 100% | 0% |
| multi-agent-AIAGENT-01 | 28.64 | 6607 | 2082 | 8689 | n/a | 9.8 | 88% | 0% |
| baseline-AIAGENT-02 | 9.21 | 3811 | 737 | 4548 | n/a | 10.0 | 100% | 0% |
| multi-agent-AIAGENT-02 | 24.73 | 6533 | 1968 | 8501 | n/a | 10.0 | 100% | 0% |
| baseline-AIAGENT-03 | 8.66 | 3943 | 816 | 4759 | n/a | 10.0 | 100% | 0% |
| multi-agent-AIAGENT-03 | 24.46 | 6823 | 2161 | 8984 | n/a | 10.0 | 100% | 0% |
| baseline-AIAGENT-04 | 11.03 | 3970 | 969 | 4939 | n/a | 10.0 | 100% | 0% |
| multi-agent-AIAGENT-04 | 33.12 | 7142 | 2598 | 9740 | n/a | 9.8 | 88% | 0% |
| baseline-AIAGENT-05 | 9.45 | 3942 | 826 | 4768 | n/a | 8.8 | 38% | 0% |
| multi-agent-AIAGENT-05 | 24.50 | 6592 | 1910 | 8502 | n/a | 10.0 | 100% | 0% |
| baseline-AIAGENT-06 | 9.62 | 3857 | 769 | 4626 | n/a | 9.8 | 88% | 0% |
| multi-agent-AIAGENT-06 | 30.71 | 6934 | 2513 | 9447 | n/a | 10.0 | 100% | 0% |
| baseline-AIAGENT-07 | 7.10 | 3962 | 761 | 4723 | n/a | 10.0 | 100% | 0% |
| multi-agent-AIAGENT-07 | 19.96 | 6536 | 1867 | 8403 | n/a | 10.0 | 100% | 0% |
| baseline-AIAGENT-08 | 9.46 | 3875 | 758 | 4633 | n/a | 9.8 | 88% | 0% |
| multi-agent-AIAGENT-08 | 31.31 | 6829 | 2373 | 9202 | n/a | 10.0 | 100% | 0% |
| baseline-AIAGENT-09 | 10.31 | 4005 | 970 | 4975 | n/a | 10.0 | 100% | 0% |
| multi-agent-AIAGENT-09 | 27.75 | 7280 | 2528 | 9808 | n/a | 9.8 | 88% | 0% |
| baseline-AIAGENT-10 | 8.01 | 3953 | 805 | 4758 | n/a | 9.8 | 88% | 0% |
| multi-agent-AIAGENT-10 | 23.53 | 7007 | 2406 | 9413 | n/a | 10.0 | 100% | 0% |
| baseline-AIAGENT-11 | 12.81 | 3822 | 794 | 4616 | n/a | 10.0 | 100% | 0% |
| multi-agent-AIAGENT-11 | 25.60 | 6482 | 2044 | 8526 | n/a | 9.8 | 88% | 0% |
| baseline-AIAGENT-12 | 11.19 | 3927 | 880 | 4807 | n/a | 10.0 | 100% | 0% |
| multi-agent-AIAGENT-12 | 34.51 | 6878 | 2332 | 9210 | n/a | 9.8 | 88% | 0% |
| baseline-AIAGENT-13 | 17.75 | 3946 | 926 | 4872 | n/a | 10.0 | 100% | 0% |
| multi-agent-AIAGENT-13 | 31.67 | 7437 | 2772 | 10209 | n/a | 10.0 | 100% | 0% |
| baseline-AIAGENT-14 | 8.13 | 3823 | 737 | 4560 | n/a | 10.0 | 100% | 0% |
| multi-agent-AIAGENT-14 | 28.41 | 6405 | 1856 | 8261 | n/a | 9.8 | 88% | 0% |
| baseline-AIAGENT-15 | 10.94 | 3911 | 837 | 4748 | n/a | 10.0 | 100% | 0% |
| multi-agent-AIAGENT-15 | 25.04 | 6459 | 1837 | 8296 | n/a | 10.0 | 100% | 0% |
| baseline-AIAGENT-16 | 10.94 | 3812 | 891 | 4703 | n/a | 10.0 | 100% | 0% |
| multi-agent-AIAGENT-16 | 29.43 | 6607 | 2276 | 8883 | n/a | 10.0 | 100% | 0% |
| baseline-AIAGENT-17 | 8.97 | 3899 | 776 | 4675 | n/a | 9.5 | 75% | 0% |
| multi-agent-AIAGENT-17 | 28.80 | 6844 | 2098 | 8942 | n/a | 9.8 | 88% | 0% |
| baseline-AIAGENT-18 | 9.37 | 3871 | 844 | 4715 | n/a | 10.0 | 100% | 0% |
| multi-agent-AIAGENT-18 | 21.93 | 6476 | 1877 | 8353 | n/a | 10.0 | 100% | 0% |
| baseline-AIAGENT-19 | 11.86 | 3871 | 811 | 4682 | n/a | 10.0 | 100% | 0% |
| multi-agent-AIAGENT-19 | 25.51 | 6907 | 2271 | 9178 | n/a | 10.0 | 100% | 0% |
| baseline-AIAGENT-20 | 11.83 | 3949 | 791 | 4740 | n/a | 10.0 | 100% | 0% |
| multi-agent-AIAGENT-20 | 34.86 | 7052 | 2510 | 9562 | n/a | 9.8 | 88% | 0% |
| baseline-AIAGENT-21 | 17.87 | 3897 | 1044 | 4941 | n/a | 10.0 | 100% | 0% |
| multi-agent-AIAGENT-21 | 24.70 | 6671 | 2051 | 8722 | n/a | 9.8 | 88% | 0% |
| baseline-AIAGENT-22 | 9.03 | 3830 | 809 | 4639 | n/a | 10.0 | 100% | 0% |
| multi-agent-AIAGENT-22 | 29.04 | 6818 | 2233 | 9051 | n/a | 10.0 | 100% | 0% |
| baseline-AIAGENT-23 | 11.39 | 3974 | 960 | 4934 | n/a | 9.5 | 75% | 0% |
| multi-agent-AIAGENT-23 | 25.15 | 7043 | 2340 | 9383 | n/a | 10.0 | 100% | 0% |
| baseline-AIAGENT-24 | 9.90 | 3820 | 875 | 4695 | n/a | 10.0 | 100% | 0% |
| multi-agent-AIAGENT-24 | 22.32 | 6568 | 1990 | 8558 | n/a | 9.8 | 88% | 0% |
| baseline-AIAGENT-25 | 9.29 | 3938 | 854 | 4792 | n/a | 10.0 | 100% | 0% |
| multi-agent-AIAGENT-25 | 27.05 | 6730 | 2058 | 8788 | n/a | 10.0 | 100% | 0% |
| baseline-AIAGENT-26 | 8.25 | 3938 | 797 | 4735 | n/a | 10.0 | 100% | 0% |
| multi-agent-AIAGENT-26 | 24.65 | 6891 | 2215 | 9106 | n/a | 10.0 | 100% | 0% |
| baseline-AIAGENT-27 | 8.12 | 3850 | 722 | 4572 | n/a | 10.0 | 100% | 0% |
| multi-agent-AIAGENT-27 | 24.99 | 6524 | 1947 | 8471 | n/a | 10.0 | 100% | 0% |
| baseline-AIAGENT-28 | 9.88 | 3829 | 918 | 4747 | n/a | 9.8 | 88% | 0% |
| multi-agent-AIAGENT-28 | 25.13 | 6734 | 2178 | 8912 | n/a | 10.0 | 100% | 0% |
| baseline-AIAGENT-29 | 9.36 | 3970 | 812 | 4782 | n/a | 10.0 | 100% | 0% |
| multi-agent-AIAGENT-29 | 23.88 | 6662 | 1953 | 8615 | n/a | 10.0 | 100% | 0% |
| baseline-AIAGENT-30 | 8.42 | 3914 | 834 | 4748 | n/a | 10.0 | 100% | 0% |
| multi-agent-AIAGENT-30 | 27.16 | 6788 | 2166 | 8954 | n/a | 9.8 | 88% | 0% |

## Comparison

- Mean latency: baseline 10.41s; multi-agent 26.95s.
- Mean token cost proxy: baseline 4734; multi-agent 8956 tokens.
- Mean automated quality proxy: baseline 9.9/10; multi-agent 9.9/10.

## Failure mode and fix

A common failure mode is **Supervisor ↔ worker looping** when a worker returns without filling the shared-state field that the router expects. The implementation fixes this with deterministic state-based routing, `max_iterations`, and an explicit `done` route. A second trade-off is that multi-agent execution usually adds latency and tokens because Researcher, Analyst, and Writer each call the model. That overhead is justified only when role separation improves grounding, debuggability, or answer quality.

*Quality is an automated regression proxy, not the final human rubric score. Replace or supplement it with peer-review 0-10 scoring for the submitted benchmark.
