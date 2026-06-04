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
| Convention authority | Implicit / per-client | `<vault>/AGENTS.md`, served via MCP `initialize.instructions` |
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
ENFORCE_FRONTMATTER=true
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

## Convention Authority: `AGENTS.md`

**The vault is self-describing.** Each vault carries an `AGENTS.md` at its root
that defines folder structure, frontmatter rules, link style, filing rules, and
any vault-specific conventions. The MCP server treats this file as the single
source of truth for how agents must write to that vault. The server itself is
schema-agnostic — it enforces path safety and the protected-file list, nothing
more about content shape.

### Load order on startup

For each configured vault, after the clone/pull/init step:

1. If `<vault>/AGENTS.md` **exists** → read and cache its content
2. If **missing** → the server writes the bundled default template
   (`obsidian_vault_mcp/default_AGENTS.md`) to `<vault>/AGENTS.md`, then caches it.
   The seed file is staged and committed (`chore: seed AGENTS.md`) but **not**
   pushed automatically — push happens on the next `vault_sync` call

The cache is refreshed when `update_conventions` is called, and re-read after
every `vault_sync` pull (in case another machine updated it).

### Surfacing to agents

The server exposes vault conventions through **two channels** so every client
receives them regardless of capability:

1. **`initialize.serverInfo.instructions`** — on the MCP `initialize` handshake,
   the server returns the concatenated convention text for all configured vaults.
   MCP-spec-compliant clients surface this to their model automatically, no tool
   call required. Per-vault sections are labelled:
   `## Vault: personal\n<AGENTS.md content>\n\n## Vault: corporate\n<AGENTS.md content>`
2. **`vault_conventions(vault?)` tool** — explicit on-demand fetch. Use this as
   a fallback in agent prompts / skills for clients that do not surface
   `initialize.instructions` reliably, or to re-read after a long session

### Protected files

The `note_*` tools refuse any operation whose resolved path matches one of:
- `<vault-root>/AGENTS.md`
- `<vault-root>/CLAUDE.md`

This prevents agents from corrupting vault rules through ordinary note operations.
`AGENTS.md` is mutated only via `update_conventions`. `CLAUDE.md` is treated as
read-only by the MCP server — users edit it manually if they want it (it remains
loaded as supplementary instructions).

`note_list` excludes these files from its results.

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
   - If `<vault>/AGENTS.md` is missing → write `default_AGENTS.md`, stage and
     commit (`chore: seed AGENTS.md`); push deferred to next `vault_sync`
   - Load `AGENTS.md` into per-vault convention cache
2. Build the `initialize.instructions` payload by concatenating all per-vault
   conventions under labelled headings
3. Start FastMCP server on `0.0.0.0:8080`

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

## Tools (10 total)

| Tool | Parameters | Purpose |
| --- | --- | --- |
| `vault_list` | — | List configured vaults + dirty flag and ahead/behind remote counts for each (remote vaults only; local vaults show dirty flag only) |
| `vault_conventions` | `vault?` | Return cached `AGENTS.md` content for that vault |
| `update_conventions` | `vault?, content, section?` | Replace `AGENTS.md` (or one `## heading` section) at vault root; refreshes cache; refuses any other path |
| `note_create` | `vault?, path, content, tags?` | Write note with frontmatter; path relative to vault root; refuses `AGENTS.md` / `CLAUDE.md` at root |
| `note_read` | `vault?, path` | Return frontmatter + body separately; refuses protected files |
| `note_update` | `vault?, path, content?, append?, tags?` | Replace or append content; refuses protected files |
| `note_delete` | `vault?, path` | Delete note; refuses protected files |
| `note_list` | `vault?, folder?` | List `.md` files under folder (or root); excludes `AGENTS.md` / `CLAUDE.md` from results |
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

Rules (enforced by the server when `ENFORCE_FRONTMATTER=true`, the default):

- `title` defaults to the raw filename stem (no extension, no transformation):
  `Sessions/2026-05-30-topic.md` → `title: 2026-05-30-topic`
- `note_update` always bumps `modified`
- `created` is never changed after initial write
- Tags are merged (not replaced) when `tags` param is passed to `note_update`
- `aliases: []` is seeded on create; preserved across updates

The bundled `default_AGENTS.md` documents this schema so agents see it through
the `initialize.instructions` channel as well. A vault may extend the schema
in its own `AGENTS.md` (additional fields), but the five fields above are
always present on server-created notes — unless enforcement is disabled.

### Disabling enforcement

Set `ENFORCE_FRONTMATTER=false` to make the server schema-agnostic. With
enforcement off:

- No auto-injection of `title`, `created`, `modified`, or `aliases`
- `note_update` does **not** bump `modified`
- Only what the agent passes is written; existing frontmatter is preserved
  field-for-field, including additions
- `tags` argument still merges with existing tags (mechanical preservation
  is independent of enforcement)
- The agent becomes responsible for any timestamp / title conventions —
  declare them in the vault's `AGENTS.md` so the agent knows what to write

Use this when a vault has frontmatter conventions that don't match the default
schema (e.g., different field names, ISO timestamps, no `aliases`, etc.).
With enforcement off, the vault's `AGENTS.md` becomes the only source of
frontmatter rules — the server contributes nothing beyond parsing and
preservation.

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
    ├── __main__.py        # entry point: parses --transport flag, reads SERVER_PORT/SERVER_IP, calls server.run()
    ├── server.py          # FastMCP server, tool definitions, initialize.instructions assembly
    ├── vault.py           # Vault class: path resolution, note CRUD, protected-path guard
    ├── conventions.py     # AGENTS.md load / write / cache; default template seeding
    ├── default_AGENTS.md  # Bundled default template (seeded into vaults missing AGENTS.md)
    ├── frontmatter.py     # Frontmatter read/write helpers
    ├── git_sync.py        # subprocess-based clone, pull, commit, push
    └── config.py          # Config loading from env vars
```

## Path safety

All note paths are resolved relative to `/vaults/<name>/` and checked against
`..` traversal before any read or write operation. Additionally, `note_*` tools
reject paths where the resolved basename matches `AGENTS.md` or `CLAUDE.md` at
vault root — see "Convention Authority" above.

## Usage patterns (Level 4)

The vault's `AGENTS.md` is authoritative for paths and conventions. The
examples below assume the default template's placeholder structure; real
vaults will use their own folder layout as declared in their `AGENTS.md`.

| Use case | Tool call |
| --- | --- |
| First write of a session | `vault_conventions(vault="personal")` then `note_create(...)` if the client did not surface `initialize.instructions` |
| Create note (path per vault `AGENTS.md`) | `note_create(vault="personal", path="<folder>/<name>.md", content=..., tags=[...])` |
| Update existing note | `note_update(vault="personal", path="...", append="...")` |
| Search by tag | `note_search(vault="personal", query="bgp", tags=["networking"])` |
| Browse a folder | `note_list(vault="personal", folder="<folder>")` |
| Sync after writes | `vault_sync(vault="personal", message="session: add BGP peering note")` |
| Adjust a vault convention | `update_conventions(vault="personal", section="Frontmatter", content="...")` |
