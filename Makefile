.PHONY: test lint typecheck check

test:
	uv run pytest -q

lint:
	uv run ruff check src tests

typecheck:
	uv run mypy src

check: test lint typecheck
