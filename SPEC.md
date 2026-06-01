# Obsidian Vault MCP — Spec

Custom MCP server that operates directly on Obsidian vault git repositories.
Replaces `mcp-obsidian` / Obsidian Local REST API plugin approach.

## Why custom

| | Obsidian REST API (`mcp-obsidian`) | Custom vault MCP |
| --- | --- | --- |
| Obsidian must be open | Yes | No |
| Multi-vault support | One vault, one port | Any number, configured |
| Git sync | External, manual | Built-in (clone, pull, push) |
| Frontmatter control | Via API (limited) | Full |
| Works headless/CI | No | Yes |
| Deployment | Host process | Docker container |

## Deployment

Lives in its own git repository. A CI pipeline builds the Docker image and pushes
it to a container registry (`ghcr.io/bkuebler/obsidian-vault-mcp:latest`). The VM's
`docker-compose.yml` pulls the image directly — no source code on the VM.

Runs as a Docker container (Streamable HTTP transport, port 8080) as part of the
shared MCP stack on the VM. Each service gets its own container IP via Docker
Compose, so port collisions are not a concern. Port and bind address can be
overridden via `SERVER_PORT` and `SERVER_IP` environment variables.

Vault repos are cloned into a named Docker volume on container startup. The
Obsidian app on the host is a separate clone of the same git remotes — both
sync via git. The container is fully self-contained; no host path mounting
required for vault content.

## Config

Passed via environment variables in `~/.ai-memory/.env`:

```bash
VAULT_PERSONAL_REPO=https://ghp_xxxxxxxxxxxxxxxxxxxx@github.com/user/obsidian-personal.git
VAULT_CORPORATE_REPO=https://ghp_yyyyyyyyyyyyyyyyyyyy@github.com/org/obsidian-corporate.git
VAULT_NOTES_REPO=local
VAULT_DEFAULT=personal

# Optional overrides (defaults shown)
SERVER_PORT=8080
SERVER_IP=0.0.0.0
```

Vault name is derived from the env var key by extracting the segment between
`VAULT_` and `_REPO`, lowercased: `VAULT_PERSONAL_REPO` → `personal`,
`VAULT_CORPORATE_REPO` → `corporate`.

`VAULT_DEFAULT` specifies the vault used when the `vault` parameter is omitted
from any tool call. All tools accept an explicit `vault` override regardless.

Tokens are embedded directly in the repo URLs. Each vault can use a different
token, which is useful when personal and corporate vaults live on different
GitHub accounts or organisations.

Setting a vault to `local` instead of a URL creates a local-only git repository
under `/vaults/<name>/` with no remote. `vault_sync` for a local vault commits
any pending changes but skips the push step.

## Dockerfile

A `.dockerignore` must be present to prevent `.git/`, `*.md`, `.env*`,
`__pycache__`, and `.ruff_cache` from being included in the image layer.

```dockerfile
FROM python:3.13-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .
RUN pip install -e .

VOLUME /vaults
EXPOSE 8080

ENTRYPOINT ["python", "-m", "obsidian_vault_mcp"]
```

## Startup behaviour

On container start, before the MCP server begins accepting connections:

1. For each configured vault:
   - **Remote vault** (`VAULT_*_REPO` is a URL):
     - If `/vaults/<name>/` does not exist → `git clone <repo-url> /vaults/<name>/`
     - If `/vaults/<name>/` exists → `git -C /vaults/<name> pull --rebase`
   - **Local vault** (`VAULT_*_REPO=local`):
     - If `/vaults/<name>/` does not exist → `git init /vaults/<name>/`
     - If `/vaults/<name>/` exists → no-op
2. Start FastMCP server on `0.0.0.0:8080`

## Transport

Supports two modes via `--transport` flag:

```bash
python -m obsidian_vault_mcp --transport streamable-http   # Docker (default in container)
python -m obsidian_vault_mcp --transport stdio             # local dev / testing
```

Port and bind address are read from `SERVER_PORT` (default `8080`) and
`SERVER_IP` (default `0.0.0.0`) — no CLI flags needed.

`streamable-http` is the recommended network transport in the official MCP SDK (SSE is
superseded). Internally `server.py` calls `mcp.run(transport="streamable-http")`.
Traefik proxies it transparently — no label changes required.

## Tools (8 total)

| Tool | Parameters | Purpose |
| --- | --- | --- |
| `vault_list` | — | List configured vaults + dirty flag and ahead/behind remote counts for each (remote vaults only; local vaults show dirty flag only) |
| `note_create` | `vault?, path, content, tags?` | Write note with frontmatter; path relative to vault root |
| `note_read` | `vault?, path` | Return frontmatter + body separately |
| `note_update` | `vault?, path, content?, append?, tags?` | Replace or append content; always bumps `modified` date |
| `note_delete` | `vault?, path` | Delete note |
| `note_list` | `vault?, folder?` | List `.md` files under folder (or root), return paths + titles |
| `note_search` | `vault?, query, tags?, folder?` | Case-insensitive grep across content + frontmatter; filter by tags |
| `vault_sync` | `vault?, message?` | Commit if changes exist, then push; returns status message |

### note_update behaviour

| `content` | `append` | Result |
| --- | --- | --- |
| provided | omitted / false | Replace body with `content` |
| provided | true | Append `content` to existing body (newline-separated) |
| omitted | omitted / false | Tags-only update; body unchanged |
| omitted | true | Error — `append=True` requires `content` |

### note_search behaviour

Uses `grep -r -i` (subprocess) across all `.md` files in the target folder (or vault
root). Tag filter is applied as a post-filter on the matched files' frontmatter.

### vault_sync behaviour

1. If working tree is dirty: `git add -A && git commit -m <message>`
2. For remote vaults: `git push` (runs regardless of whether a new commit was
   made, to push any previously committed but unpushed changes)
   For local vaults: push step is skipped
3. Returns a status message indicating what was done (e.g. `"committed and pushed"`,
   `"nothing to commit, pushed 1 existing commit"`, `"nothing to commit or push"`,
   `"committed (local only)"`)

## Frontmatter format

Every created note gets:

```yaml
---
title: 2026-05-30-topic
created: 2026-05-30
modified: 2026-05-30
tags:
  - session
aliases: []
---
```

Rules:

- `title` defaults to the raw filename stem (no extension, no transformation):
  `Sessions/2026-05-30-topic.md` → `title: 2026-05-30-topic`
- `note_update` always bumps `modified`
- `created` is never changed after initial write
- Tags are merged (not replaced) when `tags` param is passed to `note_update`

## Dependencies

```text
mcp                  # official MCP Python SDK (modelcontextprotocol/python-sdk)
python-frontmatter   # parse + write YAML frontmatter cleanly
```

Use `from mcp.server.fastmcp import FastMCP` — this is the official SDK's built-in
FastMCP, **not** the standalone `fastmcp` package by jlowin on PyPI. The two diverged
after FastMCP 1.0 was incorporated into the official SDK in 2024 and are no longer
the same codebase. The standalone package's v3 breaking changes (`ui=` → `app=` rename,
16 removed constructor kwargs) do not apply here.

Git operations via `subprocess` — no gitpython dependency.

## File structure

```text
(own repository)
├── .dockerignore
├── Dockerfile
├── pyproject.toml
└── obsidian_vault_mcp/
    ├── __init__.py
    ├── __main__.py    # entry point: parses --transport flag, reads SERVER_PORT/SERVER_IP, calls server.run()
    ├── server.py      # FastMCP server, tool definitions
    ├── vault.py       # Vault class: path resolution, note CRUD
    ├── frontmatter.py # Frontmatter read/write helpers
    ├── git_sync.py    # subprocess-based clone, pull, commit, push
    └── config.py      # Config loading from env vars
```

## Path safety

All note paths are resolved relative to `/vaults/<name>/` and checked against
`..` traversal before any read or write operation.

## Usage patterns (Level 4)

| Use case | Tool call |
| --- | --- |
| Research session | `note_create(vault="corporate", path="Sessions/2026-05-30-topic.md", ...)` |
| Architecture decision | `note_create(vault="corporate", path="Decisions/project/auth.md", ...)` |
| Personal reference | `note_create(vault="personal", path="Tools/claude-code.md", ...)` |
| Sync after writes | `vault_sync(vault="corporate", message="session: add auth decision note")` |
| Browse recent | `note_list(vault="corporate", folder="Sessions")` |
