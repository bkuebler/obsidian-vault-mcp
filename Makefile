.PHONY: test validate build clean prepare

test:
	.venv/bin/pytest

validate:
	.venv/bin/ruff check .
	.venv/bin/ruff format --check .

build:
	docker build -t obsidian-vault-mcp:latest .

clean:
	git clean -fdx .

prepare:
	uv venv
	uv pip install -e ".[dev]"
