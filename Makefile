.PHONY: sync test lint format check run

sync:
	uv sync --all-groups

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

check: lint test

run:
	uv run quant --help
