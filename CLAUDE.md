# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

- Python ≥ 3.13, package manager: **uv**
- Venv lives at `.venv/` — all commands use `.venv/bin/` directly

```bash
uv venv
uv pip install -e ".[dev]"
```

## Commands

```bash
make test        # pytest with branch coverage (always on)
make validate    # ruff check + ruff format --check
.venv/bin/ruff format .   # fix formatting (not in Makefile)
```

## TDD rule

Write the failing test first, then write the minimum implementation to make it pass. **Adjusting tests to match broken implementation is not allowed.**

## Mock boundaries

| Module | Strategy |
|---|---|
| `config.py` | `monkeypatch.setenv` — never touch real `os.environ` |
| `git_sync.py` | Mock `subprocess.run` — never call real git |
| `frontmatter.py` | Real filesystem via `tmp_path` |
| `vault.py` | Real filesystem via `tmp_path`; mock `git_sync` where needed |
| `server.py` | Call tool functions directly as plain Python; mock `git_sync` where needed |
| `conventions.py` | Real filesystem via `tmp_path`; mock `obsidian_vault_mcp.git_sync.commit_file` for the seed-commit path |

## FastMCP SDK import

Always import from the official MCP SDK — **not** the standalone `fastmcp` package by jlowin on PyPI:

```python
from mcp.server.fastmcp import FastMCP  # correct
```

The two diverged after FastMCP 1.0 was incorporated into the SDK in 2024. The standalone package's v3 breaking changes do not apply here.

`mcp.run()` does not accept `host` or `port` kwargs — set them via `mcp.settings.host` and `mcp.settings.port` before calling `run()`. `test_sdk_contract.py` guards this.

`mcp.instructions` is a read-only property backed by `mcp._mcp_server.instructions` (settable). To update instructions at runtime, assign to `mcp._mcp_server.instructions`.

## Vault types

- `VAULT_<NAME>_REPO=<url>` — remote vault: `git clone`/`git pull --rebase` on startup, `git push` in `vault_sync`
- `VAULT_<NAME>_REPO=local` — local vault: `git init` on startup, no push ever

`vault_list` omits `ahead`/`behind` keys for local vaults. `vault_sync` returns `"committed (local only)"` for local vaults.

## Server module patterns

`server.py` uses module-level globals (`_vaults`, `_vault_configs`, `_default`). `server.setup()` resets all of them — call it in tests to configure state, then call tool functions as plain Python functions. The `mcp` singleton is created at import time.

`main()` accepts `args: list[str] | None` and `vaults_root: Path` for testability.

`conventions.py` has a module-level `_cache: dict[str, str]`. `tests/conftest.py` has an `autouse` fixture that clears it before/after every test. Populate it directly in tests via `conventions._cache["vault_name"] = "content"`.

## Adding git operations to existing server tools

When a new `git_sync` call is added to an existing `server.py` tool, **all** existing
tests for that tool break because they don't mock the new call. Update every affected
test to add the new mock — not just the new tests.

## Seeding detection pattern (`__main__.py`)

To detect whether `conventions.load` actually wrote `AGENTS.md` (vs. was mocked):
```python
was_missing = not (vault_path / "AGENTS.md").exists()
conventions.load(vc.name, vault_path)
was_seeded = was_missing and (vault_path / "AGENTS.md").exists()
```
Single before-only check causes spurious pushes when `conventions.load` is mocked in tests.

## AGENTS.md change detection in `vault_sync`

After `pull_rebase`, detect whether `AGENTS.md` changed by comparing file content against
`conventions._cache.get(vault_name, "")` directly — no separate snapshot needed.

## Known gaps (not yet implemented)

- No CI pipeline — SPEC.md describes `ghcr.io/bkuebler/obsidian-vault-mcp:latest` as the target image but no GitHub Actions workflow exists yet
- `git commit` inside the container requires `user.email` and `user.name` to be set in the container environment — not handled in code
