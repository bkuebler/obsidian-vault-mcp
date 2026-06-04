# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-06-04

### Added

- `vault_conventions(vault?)` tool — returns cached `AGENTS.md` content for a vault
- `update_conventions(vault?, content, section?)` tool — rewrites `AGENTS.md` in full
  or replaces a single `## heading` section; commits but does not push
- Convention authority: each vault carries `AGENTS.md` at its root defining folder
  structure, frontmatter rules, and link style. A default template is seeded and
  committed (`chore: seed AGENTS.md`) on first start if the file is missing.
- `initialize.serverInfo.instructions` — on the MCP `initialize` handshake the server
  returns the concatenated `AGENTS.md` content for all configured vaults under labelled
  `## Vault: <name>` headings; spec-compliant clients surface this to their model
  automatically without a tool call
- `ENFORCE_FRONTMATTER` environment variable (default `true`): set to `false` to disable
  auto-injection of `title`, `created`, `modified`, and `aliases` fields; `note_update`
  will not bump `modified`; tag merging is unaffected by this flag
- Protected files: `note_*` tools refuse any read or write operation on `AGENTS.md` or
  `CLAUDE.md` at vault root; `note_list` excludes them from results. Mutations to
  `AGENTS.md` are only possible via `update_conventions`.

## [0.1.1] - 2026-06-01

### Fixed

- Docker image now published as a multi-platform manifest (`linux/amd64`, `linux/arm64`)

## [0.1.0] - 2026-06-01

### Added

- 8 MCP tools: `vault_list`, `note_create`, `note_read`, `note_update`,
  `note_delete`, `note_list`, `note_search`, `vault_sync`
- Multi-vault support via `VAULT_*_REPO` environment variables; vault name
  derived from the key segment between `VAULT_` and `_REPO`
- Remote vault mode: `git clone` on first start, `git pull --rebase` on
  subsequent starts
- Local vault mode: `VAULT_*_REPO=local` initialises a local-only git
  repository with no remote; `vault_sync` commits but skips push
- `VAULT_DEFAULT` to set the default vault; omitted when only one vault is
  configured
- `SERVER_PORT` and `SERVER_IP` environment variables to override bind address
  (defaults: `8080`, `0.0.0.0`)
- `--transport` CLI flag with choices `streamable-http` (default) and `stdio`
- YAML frontmatter on every note: `title`, `created`, `modified`, `tags`,
  `aliases`; `modified` bumped on every `note_update`, `created` never changed
- Tag merging on `note_update`: new tags appended, duplicates suppressed,
  original order preserved
- Path traversal protection: rejects `..` segments and percent-encoded
  equivalents (`%2e%2e`)
- Argument injection hardening: `--` separator in `git clone`, `-e`/`--`
  flags in `grep`; URL scheme validation in `git_sync`
- Streamable HTTP transport via FastMCP (SSE superseded)
- Docker image based on `python:3.13-slim` with git and ca-certificates;
  vault data persisted in a named `/vaults` volume
- `make test` — runs pytest with branch coverage report
- `make validate` — runs ruff check and ruff format check
- `make build` — builds the Docker image as `obsidian-vault-mcp:latest`
- SDK contract tests to guard against breaking changes in MCP SDK upgrades

[Unreleased]: https://github.com/bkuebler/obsidian-vault-mcp/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/bkuebler/obsidian-vault-mcp/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/bkuebler/obsidian-vault-mcp/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/bkuebler/obsidian-vault-mcp/releases/tag/v0.1.0
