# AGENTS.md

> Default template seeded by `obsidian-vault-mcp` when a vault has no `AGENTS.md` at its root.
>
> This file is the **authoritative source** of vault conventions. The MCP server returns its
> content via the MCP `initialize.serverInfo.instructions` field so every connecting client
> surfaces it to its agent automatically. It is also available on demand through the
> `vault_conventions` tool.
>
> Edit via the `update_conventions` MCP tool, not via `note_update` — the `note_*` tools refuse
> to read or write `AGENTS.md` (or `CLAUDE.md`) at vault root.
>
> **Customise this file for your vault.** The defaults below are minimal placeholders.

---

# Vault Conventions

This file defines the structural and formatting conventions for this Obsidian vault.
Any AI agent writing to this vault — whether via MCP, direct file access, or an
editor — must follow these rules.

## Vault Structure

Default categories — adjust to match your vault:

- **Sessions/** — Research / working session notes. Filename: `YYYY-MM-DD-<topic>.md`
- **Decisions/** — Architecture and project decisions. Path: `Decisions/<project>/<topic>.md`
- **Tools/** — Tool references and notes. Path: `Tools/<tool>.md`

## Filing Rules

- New session note → `Sessions/YYYY-MM-DD-<topic>.md`
- Architecture or design decision → `Decisions/<project>/<topic>.md`
- Reference or how-to for a specific tool → `Tools/<tool>.md`

Anything that doesn't fit these three categories: introduce a new top-level folder
and document it in this file via the `update_conventions` MCP tool.

## Frontmatter

The MCP server enforces a fixed frontmatter schema on every note it creates or
updates. Agents do not need to construct frontmatter manually — the server
applies the rules below.

```yaml
---
title: <filename stem>
created: YYYY-MM-DD
modified: YYYY-MM-DD
tags:
  - <relevant-tags>
aliases: []
---
```

Rules (server-enforced):
- `title` defaults to the raw filename stem (no extension, no transformation)
- `created` is set on first write and never changed afterwards
- `modified` is bumped on every `note_update` call
- `tags` are merged (not replaced) when the `tags` parameter is passed to `note_update`
- `aliases: []` is seeded on create and preserved across updates
- Any additional fields already present on an existing note are preserved

If your vault needs extra fields beyond these five, document them in this file
and the agent will include them when it writes — but the five fields above are
always present on server-created notes regardless of what this file says.

**Disabling enforcement.** If your vault uses a fundamentally different
frontmatter schema (different field names, ISO timestamps, no `aliases`, etc.),
start the MCP server with `ENFORCE_FRONTMATTER=false`. The server then writes
only what the agent passes. In that mode this file becomes the **only** source
of frontmatter rules — rewrite this section to describe the schema the agent
should construct, and the agent will follow it via the
`initialize.instructions` channel.

## Link Style

- Internal links use **standard Markdown** syntax: `[text](relative/path.md)`
- Avoid `[[wikilink]]` syntax if you ever export via Marp or pandoc — it breaks those
  pipelines. Obsidian tracks and auto-updates standard Markdown links on rename

## See Also Section

Notes should end with a `## See Also` section listing related notes as standard
Markdown links, unless they are formal documents (contracts, templates, references)
where editorial additions don't belong.

## File Types

- All notes are Markdown (`.md`)
- Canvas files (`.canvas`) are JSON-based Obsidian diagrams — do not edit
- Do not modify `.obsidian/` configuration

## Media

Image / audio / video attachments go in `Media/` unless your vault declares
section-specific exceptions (e.g., Marp presentation assets alongside the slide `.md`).

## Protected Files

The MCP server protects these files at vault root from `note_*` operations:
- `AGENTS.md` — this file (edit via `update_conventions`)
- `CLAUDE.md` — if present, loaded as supplementary instructions

Anything else is fair game for `note_create`, `note_update`, `note_delete`.
