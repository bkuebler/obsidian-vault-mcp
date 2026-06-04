# obsidian-vault-mcp

![GitHub Sponsors](https://img.shields.io/github/sponsors/bkuebler)
[![codecov](https://codecov.io/github/bkuebler/obsidian-vault-mcp/graph/badge.svg?token=NDE84P5R5S)](https://codecov.io/github/bkuebler/obsidian-vault-mcp)
[![Maintainability](https://qlty.sh/gh/bkuebler/projects/obsidian-vault-mcp/maintainability.svg)](https://qlty.sh/gh/bkuebler/projects/obsidian-vault-mcp)

An MCP server that operates directly on Obsidian vault git repositories.
No Obsidian app required — works headless, supports multiple vaults, and handles git sync automatically.

## Why

| | Obsidian REST API (`mcp-obsidian`) | obsidian-vault-mcp |
|---|---|---|
| Obsidian must be open | Yes | No |
| Multi-vault support | One vault, one port | Any number, configured |
| Git sync | External, manual | Built-in (clone, pull, push) |
| Frontmatter control | Via API (limited) | Full |
| Works headless / CI | No | Yes |
| Deployment | Host process | Docker container |

## Requirements

- Docker (recommended) or Python 3.13+
- Git repositories for your vaults (or `local` for git-only, no remote)

## Quick start

```bash
docker run -d \
  --name obsidian-vault-mcp \
  -e VAULT_PERSONAL_REPO=https://ghp_xxxx@github.com/user/obsidian-personal.git \
  -e VAULT_DEFAULT=personal \
  -v obsidian-vaults:/vaults \
  ghcr.io/bkuebler/obsidian-vault-mcp:latest
```

## Configuration

All configuration is via environment variables.

### Vault configuration

| Variable | Example | Description |
|---|---|---|
| `VAULT_<NAME>_REPO` | `https://ghp_xx@github.com/user/repo.git` | Remote git URL with embedded token. One per vault. |
| `VAULT_<NAME>_REPO` | `local` | Local-only vault, no remote. `vault_sync` commits but does not push. |
| `VAULT_DEFAULT` | `personal` | Vault used when the `vault` parameter is omitted. Optional if only one vault is configured. |

Vault names are derived from the key: `VAULT_PERSONAL_REPO` → `personal`, `VAULT_CORPORATE_REPO` → `corporate`.

Multiple vaults example:

```bash
VAULT_PERSONAL_REPO=https://ghp_xxxxxxxxxxxxxxxxxxxx@github.com/user/obsidian-personal.git
VAULT_CORPORATE_REPO=https://ghp_yyyyyyyyyyyyyyyyyyyy@github.com/org/obsidian-corporate.git
VAULT_NOTES_REPO=local
VAULT_DEFAULT=personal
```

### Server configuration

| Variable | Default | Description |
|---|---|---|
| `SERVER_PORT` | `8080` | TCP port to bind (http-alt per IANA) |
| `SERVER_IP` | `0.0.0.0` | IP address to bind |
| `ENFORCE_FRONTMATTER` | `true` | Set `false` to disable auto-injection of `title`, `created`, `modified`, `aliases`; `note_update` will not bump `modified`; tag merging is unaffected |

### Transport

```bash
# Streamable HTTP — default, used in Docker behind Traefik
python -m obsidian_vault_mcp --transport streamable-http

# stdio — local dev and testing
python -m obsidian_vault_mcp --transport stdio
```

## Docker Compose

```yaml
services:
  obsidian-vault-mcp:
    image: ghcr.io/bkuebler/obsidian-vault-mcp:latest
    env_file: ~/.ai-memory/.env
    volumes:
      - obsidian-vaults:/vaults
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.obsidian-mcp.rule=Host(`obsidian-mcp.example.com`)"

volumes:
  obsidian-vaults:
```

## Startup behaviour

On container start, before accepting MCP connections:

1. For each configured vault:
   - **Remote** — `git clone <url> /vaults/<name>/` if the directory does not exist, otherwise `git pull --rebase`
   - **Local** — `git init /vaults/<name>/` if the directory does not exist, otherwise no-op
   - If `AGENTS.md` is missing → write default template, commit (`chore: seed AGENTS.md`); for remote vaults push immediately — if the push is rejected (another instance seeded first), discard the local seed (`git reset --hard origin/<branch>`) and load the remote `AGENTS.md` instead
   - Load `AGENTS.md` into per-vault convention cache
2. Build `initialize.instructions` payload from all cached conventions
3. FastMCP server starts on `SERVER_IP:SERVER_PORT`

## Tools

| Tool | Parameters | Description |
|---|---|---|
| `vault_list` | — | Lists all configured vaults with dirty flag and ahead/behind counts (remote vaults only) |
| `vault_conventions` | `vault?` | Returns cached `AGENTS.md` content for a vault |
| `update_conventions` | `vault?`, `content`, `section?` | Rewrites `AGENTS.md` (full or single `## heading` section); commits, pull-rebases, and pushes immediately (remote vaults); commits only for local vaults |
| `note_create` | `path`, `content`, `vault?`, `tags?` | Creates a note with YAML frontmatter; refuses `AGENTS.md` / `CLAUDE.md` at vault root |
| `note_read` | `path`, `vault?` | Returns frontmatter and body separately; refuses protected files |
| `note_update` | `path`, `vault?`, `content?`, `append?`, `tags?` | Replaces or appends body; merges tags; bumps `modified` (unless `ENFORCE_FRONTMATTER=false`); refuses protected files |
| `note_delete` | `path`, `vault?` | Deletes a note; refuses protected files |
| `note_list` | `vault?`, `folder?` | Lists `.md` files with titles; excludes `AGENTS.md` / `CLAUDE.md` at vault root |
| `note_search` | `query`, `vault?`, `tags?`, `folder?` | Case-insensitive full-text search with optional tag filter |
| `vault_sync` | `vault?`, `message?` | Commits any changes and pushes (remote) or commits only (local) |

Parameters marked `?` are optional. All tools default to `VAULT_DEFAULT` when `vault` is omitted.

### `note_update` behaviour

| `content` | `append` | Result |
|---|---|---|
| provided | omitted / false | Replace body |
| provided | true | Append to body (newline-separated) |
| omitted | omitted / false | Tags-only update; body unchanged |
| omitted | true | Error |

### `vault_sync` return values

| Condition | Return value |
|---|---|
| Dirty tree, remote vault | `committed and pushed` |
| Clean tree, unpushed commits, remote vault | `nothing to commit, pushed N existing commit after rebase` |
| Clean tree, nothing ahead, remote vault | `nothing to commit or push` |
| Rebase conflict, remote vault | `rebase conflict: <paths>` |
| Dirty tree, local vault | `committed (local only)` |
| Clean tree, local vault | `nothing to commit or push` |

## Convention authority

Each vault carries an `AGENTS.md` at its root that defines folder structure, frontmatter rules, link style, and any vault-specific conventions. The server:

- Seeds a default template on first start if `AGENTS.md` is absent; commits and pushes the seed immediately for remote vaults (with race-safe reset-hard fallback)
- Returns the content via `initialize.serverInfo.instructions` on every MCP handshake — spec-compliant clients surface this to the model automatically
- Exposes it on demand via `vault_conventions` as a fallback for clients that don't surface `initialize.instructions`
- Allows mutations only through `update_conventions` — which commits, pull-rebases, and pushes in one step; `note_*` tools refuse to touch `AGENTS.md` (or `CLAUDE.md`) at vault root

Edit conventions with:

```
update_conventions(vault="personal", section="Frontmatter", content="...")  # replace one section
update_conventions(vault="personal", content="# Full rewrite\n...")         # replace entire file
```

## Frontmatter

Every note created by `note_create` gets:

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

- `title` defaults to the filename stem (no transformation)
- `modified` is bumped on every `note_update`
- `created` is never changed after initial write
- Tags passed to `note_update` are merged, not replaced

Set `ENFORCE_FRONTMATTER=false` to disable auto-injection of these fields. The vault's `AGENTS.md` then becomes the sole source of frontmatter rules and the agent is responsible for constructing them.

## Development

### Setup

```bash
git clone https://github.com/bkuebler/obsidian-vault-mcp.git
cd obsidian-vault-mcp
uv venv
uv pip install -e ".[dev]"
```

### Commands

```bash
make test        # pytest with branch coverage report
make validate    # ruff check + ruff format --check
make build       # docker build -t obsidian-vault-mcp:latest .
```

### Project layout

```
obsidian_vault_mcp/
├── __main__.py        # Entry point: --transport flag, SERVER_PORT/SERVER_IP, startup sequence
├── config.py          # Loads configuration from environment variables
├── git_sync.py        # subprocess-based clone, pull, init, commit, push
├── frontmatter.py     # YAML frontmatter read/write helpers
├── conventions.py     # AGENTS.md load/seed/cache/refresh; replace_section helper
├── vault.py           # Vault class: path resolution, note CRUD, search, protected-path guard
├── server.py          # FastMCP server and tool definitions
└── default_AGENTS.md  # Default template seeded into vaults missing AGENTS.md
tests/
├── test_config.py
├── test_conventions.py
├── test_frontmatter.py
├── test_git_sync.py
├── test_main.py
├── test_sdk_contract.py
├── test_server.py
└── test_vault.py
```

### Running locally (stdio)

```bash
VAULT_PERSONAL_REPO=local \
VAULT_DEFAULT=personal \
python -m obsidian_vault_mcp --transport stdio
```

## Security

- Tokens are embedded in repo URLs (`https://<token>@host/repo`) and never written to disk
- All note paths are validated against `..` traversal and percent-encoded equivalents before any read or write
- `git clone` uses `--` to prevent flag smuggling from URLs
- `grep` uses `-e` and `--` to prevent flag smuggling from search queries
- URL scheme is validated against an allowlist (`https`, `ssh`, `git`) before any git operation

## License

MIT
