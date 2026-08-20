.PHONY: install test lint format typecheck run-baseline run-multi benchmark clean

install:
	pip install -e ".[dev,llm]"

test:
	pytest

lint:
	ruff check src tests

format:
	ruff format src tests

typecheck:
	mypy src

run-baseline:
	python -m multi_agent_research_lab.cli baseline --query "Research GraphRAG state-of-the-art"

run-multi:
	python -m multi_agent_research_lab.cli multi-agent --query "Research GraphRAG state-of-the-art"

benchmark:
	python -m multi_agent_research_lab.cli benchmark

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache dist build *.egg-info
