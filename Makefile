.PHONY: test validate build

test:
	.venv/bin/pytest

validate:
	.venv/bin/ruff check .
	.venv/bin/ruff format --check .

build:
	docker build -t obsidian-vault-mcp:latest .
