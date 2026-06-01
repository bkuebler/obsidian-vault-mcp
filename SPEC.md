# Obsidian Vault MCP — Spec

Custom MCP server that operates directly on Obsidian vault git repositories.
Replaces `mcp-obsidian` / Obsidian Local REST API plugin approach.

## Why custom

| | Obsidian REST API (`mcp-obsidian`) | Custom vault MCP |
|---|---|---|
| Obsidian must be open | Yes | No |
| Multi-vault support | One vault, one port | Any number, configured |
| Git sync | External, manual | Built-in (clone, pull, push) |
| Frontmatter control | Via API (limited) | Full |
| Works headless/CI | No | Yes |
| Deployment | Host process | Docker container |

## Deployment

Lives in its own git repository. A CI pipeline builds the Docker image and pushes
it to a container registry (`ghcr.io/<owner>/obsidian-vault-mcp:latest`). The VM's
`docker-compose.yml` pulls the image directly — no source code on the VM.

Runs as a Docker container (Streamable HTTP transport, port 4001) as part of the
shared MCP stack on the VM.

Vault repos are cloned into a named Docker volume on container startup. The
Obsidian app on the host is a separate clone of the same git remotes — both
sync via git. The container is fully self-contained; no host path mounting
required for vault content.

## Config

Passed via environment variables in `~/.ai-memory/.env`:

```bash
VAULT_PERSONAL_REPO=https://github.com/user/obsidian-personal.git
VAULT_CORPORATE_REPO=https://github.com/org/obsidian-corporate.git
VAULT_GIT_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
VAULT_DEFAULT=personal
```

Token is embedded in clone URLs as `https://<token>@github.com/...` — never
written to config files, only used at runtime.

## Dockerfile

```dockerfile
FROM python:3.13-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .
RUN pip install -e .

VOLUME /vaults
EXPOSE 4001

ENTRYPOINT ["python", "-m", "obsidian_vault_mcp"]
```

## Startup behaviour

On container start, before the SSE server begins accepting connections:

1. For each configured vault:
   - If `/vaults/<name>/` does not exist → `git clone https://<token>@<repo> /vaults/<name>/`
   - If `/vaults/<name>/` exists → `git -C /vaults/<name> pull --rebase`
2. Start FastMCP SSE server on `0.0.0.0:4001`

## Transport

Supports two modes via `--transport` flag:

```bash
python -m obsidian_vault_mcp --transport streamable-http --port 4001   # Docker (default in container)
python -m obsidian_vault_mcp --transport stdio                         # local dev / testing
```

`streamable-http` is the recommended network transport in the official MCP SDK (SSE is
superseded). Internally `server.py` calls `mcp.run(transport="streamable-http")`.
Traefik proxies it transparently — no label changes required.

## Tools (8 total)

| Tool | Parameters | Purpose |
|---|---|---|
| `vault_list` | — | List configured vaults + git status of each |
| `note_create` | `vault, path, content, tags?` | Write note with frontmatter; path relative to vault root |
| `note_read` | `vault, path` | Return frontmatter + body separately |
| `note_update` | `vault, path, content?, append?, tags?` | Replace or append content; always bumps `modified` date |
| `note_delete` | `vault, path` | Delete note |
| `note_list` | `vault, folder?` | List `.md` files under folder (or root), return paths + titles |
| `note_search` | `vault, query, tags?, folder?` | Grep content + frontmatter; filter by tags |
| `vault_sync` | `vault, message?` | `git add -A && git commit -m ... && git push` |

## Frontmatter format

Every created note gets:

```yaml
---
title: Derived from filename if not specified
created: 2026-05-30
modified: 2026-05-30
tags:
  - session
aliases: []
---
```

Rules:
- `note_update` always bumps `modified`
- `created` is never changed after initial write
- Tags are merged (not replaced) when `tags` param is passed to `note_update`

## Dependencies

```
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

```
(own repository)
├── Dockerfile
├── pyproject.toml
├── server.py          # FastMCP server, tool definitions, transport flag
├── vault.py           # Vault class: path resolution, note CRUD
├── frontmatter.py     # Frontmatter read/write helpers
├── git_sync.py        # subprocess-based clone, pull, commit, push
└── config.py          # Config loading from env vars
```

## Path safety

All note paths are resolved relative to `/vaults/<name>/` and checked against
`..` traversal before any read or write operation.

## Usage patterns (Level 4)

| Use case | Tool call |
|---|---|
| Research session | `note_create(vault="corporate", path="Sessions/2026-05-30-topic.md", ...)` |
| Architecture decision | `note_create(vault="corporate", path="Decisions/project/auth.md", ...)` |
| Personal reference | `note_create(vault="personal", path="Tools/claude-code.md", ...)` |
| Sync after writes | `vault_sync(vault="corporate", message="session: add auth decision note")` |
| Browse recent | `note_list(vault="corporate", folder="Sessions")` |
