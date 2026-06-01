# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/bkuebler/obsidian-vault-mcp/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/bkuebler/obsidian-vault-mcp/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/bkuebler/obsidian-vault-mcp/releases/tag/v0.1.0
