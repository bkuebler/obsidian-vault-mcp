# Security Policy

## Supported Versions

This project is currently in early development. Only the latest release
receives security updates.

| Version | Supported          |
| ------- | ------------------ |
| 0.2.x   | :white_check_mark: |
| 0.1.x   | :x:                |

## Reporting a Vulnerability

Please **do not** report security vulnerabilities via public GitHub issues.

Instead, send a description of the vulnerability to:
 **<b.kuebler@kuebler-it.de>**

Include as much detail as possible:

- A description of the vulnerability and its potential impact
- Steps to reproduce or a proof-of-concept
- Any suggested mitigations, if known

You can expect an acknowledgement within **3 business days**. If the
vulnerability is confirmed, a fix will be prioritized and you will be kept
informed of progress. If the report is declined, you will receive an
explanation.

## Scope

Security issues that are particularly relevant to this project:

- **Vault path traversal** — reading or writing files outside configured vault
  directories
- **Git command injection** — vault names or file content reaching `subprocess`
  calls unsanitized
- **MCP tool privilege escalation** — a tool exposing more filesystem access
  than intended
- **Configuration leakage** — vault repo URLs or credentials exposed through
  MCP tool responses
- **Convention file injection** — an agent using `note_*` tools to overwrite
  `AGENTS.md` or `CLAUDE.md` and alter the instructions surfaced to other agents
