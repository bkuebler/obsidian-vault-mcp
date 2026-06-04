# Development Tasks — Obsidian Vault MCP

TDD rule: write the failing test first, then write the minimum implementation to make it pass. Adjusting tests to match broken implementation is not allowed.

Mock boundaries:
- `config.py` — mock `os.environ`
- `git_sync.py` — mock `subprocess.run`
- `frontmatter.py` — real filesystem via `tmp_path`
- `vault.py` — real filesystem via `tmp_path`; mock `git_sync` where needed
- `server.py` — FastMCP in-process test client + `tmp_path`; mock `git_sync` where needed

---

## Phase 0 — Project scaffolding

- [x] **0.1** Create `pyproject.toml`
  - Package name `obsidian-vault-mcp`, requires Python ≥ 3.13
  - Runtime deps: `mcp`, `python-frontmatter`
  - Dev deps: `pytest`, `pytest-asyncio`
  - Entry point: `obsidian_vault_mcp.__main__`

- [x] **0.2** Create empty package files
  - `obsidian_vault_mcp/__init__.py`
  - `obsidian_vault_mcp/__main__.py`
  - `obsidian_vault_mcp/config.py`
  - `obsidian_vault_mcp/git_sync.py`
  - `obsidian_vault_mcp/frontmatter.py`
  - `obsidian_vault_mcp/vault.py`
  - `obsidian_vault_mcp/server.py`

- [x] **0.3** Create `tests/` directory with empty `__init__.py` and `conftest.py`

---

## Phase 1 — `config.py`

### 1.1 Vault discovery from env vars

- [x] **RED** Write `tests/test_config.py`:
  - `test_single_vault_parsed` — env `VAULT_PERSONAL_REPO=https://...` → vault name `personal` with that URL
  - `test_multiple_vaults_parsed` — two `VAULT_*_REPO` vars → two vault entries
  - `test_unrelated_env_vars_ignored` — `DATABASE_URL`, `PATH` etc. not included
  - `test_vault_name_lowercased` — `VAULT_CORPORATE_REPO` → name `corporate`

- [x] **GREEN** Implement vault discovery in `config.py`: scan `os.environ` for keys matching `VAULT_*_REPO`, extract name segment, lowercase it.

### 1.2 Local vs remote detection

- [x] **RED** Add tests:
  - `test_local_vault_detected` — `VAULT_NOTES_REPO=local` → `is_local=True`
  - `test_remote_vault_detected` — URL value → `is_local=False`

- [x] **GREEN** Implement `is_local` flag on vault config entries.

### 1.3 Default vault

- [x] **RED** Add tests:
  - `test_default_vault_set` — `VAULT_DEFAULT=personal` → default is `personal`
  - `test_default_vault_missing_raises` — no `VAULT_DEFAULT` and multiple vaults → raises `ValueError`
  - `test_default_vault_implicit` — only one vault configured, no `VAULT_DEFAULT` → that vault is default

- [x] **GREEN** Implement `VAULT_DEFAULT` resolution with fallback for single-vault case.

### 1.4 Server config

- [x] **RED** Add tests:
  - `test_server_port_default` — no `SERVER_PORT` → `8080`
  - `test_server_port_override` — `SERVER_PORT=9000` → `9000` (int)
  - `test_server_ip_default` — no `SERVER_IP` → `"0.0.0.0"`
  - `test_server_ip_override` — `SERVER_IP=127.0.0.1` → `"127.0.0.1"`

- [x] **GREEN** Implement `ServerConfig` with `port` and `ip` fields read from env.

---

## Phase 2 — `git_sync.py`

All tests mock `subprocess.run`. Assert it is called with the expected command list and `check=True`.

### 2.1 Remote vault initialisation

- [x] **RED** Write `tests/test_git_sync.py`:
  - `test_clone_when_dir_missing` — path does not exist → calls `git clone <url> <path>`
  - `test_pull_rebase_when_dir_exists` — path exists → calls `git -C <path> pull --rebase`

- [x] **GREEN** Implement `init_vault(path, url)` in `git_sync.py`.

### 2.2 Local vault initialisation

- [x] **RED** Add tests:
  - `test_git_init_when_dir_missing` — path does not exist → calls `git init <path>`
  - `test_noop_when_local_dir_exists` — path exists → `subprocess.run` not called

- [x] **GREEN** Implement `init_local_vault(path)` in `git_sync.py`.

### 2.3 Commit

- [x] **RED** Add tests:
  - `test_commit_stages_and_commits` — calls `git add -A` then `git commit -m <message>`
  - `test_commit_default_message` — no message arg → uses a non-empty default string

- [x] **GREEN** Implement `commit(path, message=None)`.

### 2.4 Push

- [x] **RED** Add tests:
  - `test_push_calls_git_push` — calls `git -C <path> push`

- [x] **GREEN** Implement `push(path)`.

### 2.5 Dirty check

- [x] **RED** Add tests:
  - `test_is_dirty_true` — `git status --porcelain` returns non-empty output → `True`
  - `test_is_dirty_false` — empty output → `False`

- [x] **GREEN** Implement `is_dirty(path)`.

### 2.6 Ahead/behind counts (remote vaults only)

- [x] **RED** Add tests:
  - `test_ahead_behind_parsed` — `git rev-list --left-right --count HEAD...@{u}` returns `"2\t1"` → `(ahead=2, behind=1)`
  - `test_ahead_behind_zero` — `"0\t0"` → `(0, 0)`

- [x] **GREEN** Implement `ahead_behind(path)`.

---

## Phase 3 — `frontmatter.py`

All tests use `tmp_path` (real filesystem).

### 3.1 Read

- [x] **RED** Write `tests/test_frontmatter.py`:
  - `test_read_returns_metadata_and_body` — file with YAML frontmatter block → metadata dict and body string returned separately
  - `test_read_file_without_frontmatter` — plain markdown → empty metadata dict, full content as body

- [x] **GREEN** Implement `read(path)` returning `(metadata: dict, body: str)`.

### 3.2 Write

- [x] **RED** Add tests:
  - `test_write_creates_file_with_frontmatter` — write metadata + body → file starts with `---` block
  - `test_write_roundtrip` — write then read → same metadata and body recovered
  - `test_write_creates_parent_dirs` — path with non-existent subdirectory → dirs created

- [x] **GREEN** Implement `write(path, metadata: dict, body: str)`.

### 3.3 Default frontmatter fields

- [x] **RED** Add tests:
  - `test_build_metadata_title_from_stem` — path `Sessions/2026-05-30-topic.md` → `title: "2026-05-30-topic"`
  - `test_build_metadata_created_today` — `created` field equals today's date
  - `test_build_metadata_modified_today` — `modified` field equals today's date
  - `test_build_metadata_empty_aliases` — `aliases: []`
  - `test_build_metadata_tags_included` — tags list passed in → present in metadata
  - `test_build_metadata_no_tags` — no tags passed → `tags: []`

- [x] **GREEN** Implement `build_metadata(path, tags=None)`.

### 3.4 Tag merging

- [x] **RED** Add tests:
  - `test_merge_tags_adds_new` — existing `["a"]` + new `["b"]` → `["a", "b"]`
  - `test_merge_tags_no_duplicates` — existing `["a"]` + new `["a"]` → `["a"]`
  - `test_merge_tags_preserves_order` — original tags come first

- [x] **GREEN** Implement `merge_tags(existing: list, new: list) -> list`.

---

## Phase 4 — `vault.py`

All tests use `tmp_path` as the vault root.

### 4.1 Path resolution and traversal protection

- [x] **RED** Write `tests/test_vault.py`:
  - `test_resolve_path_within_vault` — `notes/foo.md` → absolute path under vault root
  - `test_traversal_raises` — `../../etc/passwd` → raises `ValueError`
  - `test_traversal_encoded_raises` — `notes/%2e%2e/secret` → raises `ValueError`

- [x] **GREEN** Implement `Vault.resolve(path)` with `..` guard.

### 4.2 `note_create`

- [x] **RED** Add tests:
  - `test_note_create_writes_file` — file exists after call
  - `test_note_create_frontmatter_present` — file has `title`, `created`, `modified` fields
  - `test_note_create_body_present` — body content in file
  - `test_note_create_with_tags` — tags appear in frontmatter
  - `test_note_create_creates_subdirs` — path with nested folder → dirs created

- [x] **GREEN** Implement `Vault.note_create(path, content, tags=None)`.

### 4.3 `note_read`

- [x] **RED** Add tests:
  - `test_note_read_returns_metadata_and_body` — returns frontmatter dict and body separately
  - `test_note_read_missing_file_raises` — `FileNotFoundError`

- [x] **GREEN** Implement `Vault.note_read(path)`.

### 4.4 `note_update`

- [x] **RED** Add tests (one per row of the spec table):
  - `test_update_replaces_body` — `content` provided, `append` omitted → body replaced
  - `test_update_appends_body` — `content` provided, `append=True` → content appended with newline
  - `test_update_tags_only` — `content` omitted, `append` omitted → only tags updated, body unchanged
  - `test_update_append_without_content_raises` — `content` omitted, `append=True` → raises `ValueError`
  - `test_update_bumps_modified` — any update → `modified` date equals today
  - `test_update_never_changes_created` — `created` date unchanged after update

- [x] **GREEN** Implement `Vault.note_update(path, content=None, append=False, tags=None)`.

### 4.5 `note_delete`

- [x] **RED** Add tests:
  - `test_note_delete_removes_file` — file gone after call
  - `test_note_delete_missing_file_raises` — `FileNotFoundError`

- [x] **GREEN** Implement `Vault.note_delete(path)`.

### 4.6 `note_list`

- [x] **RED** Add tests:
  - `test_note_list_root` — returns all `.md` files under vault root
  - `test_note_list_folder` — returns only `.md` files under specified subfolder
  - `test_note_list_returns_paths_and_titles` — each entry has `path` and `title` from frontmatter
  - `test_note_list_ignores_non_md` — `.txt`, `.png` files not included

- [x] **GREEN** Implement `Vault.note_list(folder=None)`.

### 4.7 `note_search`

- [x] **RED** Add tests:
  - `test_search_matches_body_content` — query in body → file returned
  - `test_search_matches_frontmatter` — query in frontmatter value → file returned
  - `test_search_case_insensitive` — uppercase query matches lowercase content
  - `test_search_no_match_returns_empty` — unmatched query → empty list
  - `test_search_tag_filter` — tag filter applied → only files with that tag returned
  - `test_search_folder_scoped` — folder param → only files under that folder searched

- [x] **GREEN** Implement `Vault.note_search(query, tags=None, folder=None)` using `grep -r -i` subprocess.

---

## Phase 5 — `server.py`

Use FastMCP's in-process test client. Mock `git_sync` functions. Each test group covers one tool.

### 5.1 `vault_list`

- [x] **RED** Write `tests/test_server.py`:
  - `test_vault_list_returns_all_vaults` — lists each configured vault by name
  - `test_vault_list_remote_includes_ahead_behind` — remote vault entry has ahead/behind counts
  - `test_vault_list_local_no_ahead_behind` — local vault entry has dirty flag, no ahead/behind

- [x] **GREEN** Implement `vault_list` tool in `server.py`.

### 5.2 `note_create`

- [x] **RED** Add tests:
  - `test_tool_note_create_success` — tool call returns success, file exists
  - `test_tool_note_create_default_vault` — no `vault` param → default vault used
  - `test_tool_note_create_explicit_vault` — `vault` param overrides default

- [x] **GREEN** Implement `note_create` tool.

### 5.3 `note_read`

- [x] **RED** Add tests:
  - `test_tool_note_read_returns_frontmatter_and_body` — response contains both parts
  - `test_tool_note_read_missing_returns_error` — missing file → error response, not exception

- [x] **GREEN** Implement `note_read` tool.

### 5.4 `note_update`

- [x] **RED** Add tests (mirror the spec table):
  - `test_tool_note_update_replace`
  - `test_tool_note_update_append`
  - `test_tool_note_update_tags_only`
  - `test_tool_note_update_append_no_content_returns_error`

- [x] **GREEN** Implement `note_update` tool.

### 5.5 `note_delete`

- [x] **RED** Add tests:
  - `test_tool_note_delete_success` — file removed
  - `test_tool_note_delete_missing_returns_error`

- [x] **GREEN** Implement `note_delete` tool.

### 5.6 `note_list`

- [x] **RED** Add tests:
  - `test_tool_note_list_no_folder`
  - `test_tool_note_list_with_folder`

- [x] **GREEN** Implement `note_list` tool.

### 5.7 `note_search`

- [x] **RED** Add tests:
  - `test_tool_note_search_query_only`
  - `test_tool_note_search_with_tags`
  - `test_tool_note_search_with_folder`

- [x] **GREEN** Implement `note_search` tool.

### 5.8 `vault_sync`

- [x] **RED** Add tests (mock `git_sync`):
  - `test_tool_vault_sync_dirty_remote` — dirty tree, remote vault → commit + push → `"committed and pushed"`
  - `test_tool_vault_sync_clean_remote_with_unpushed` — clean tree, remote vault → push only → `"nothing to commit, pushed 1 existing commit"`
  - `test_tool_vault_sync_nothing_to_do_remote` — clean + nothing ahead → `"nothing to commit or push"`
  - `test_tool_vault_sync_dirty_local` — dirty tree, local vault → commit, no push → `"committed (local only)"`
  - `test_tool_vault_sync_clean_local` — clean tree, local vault → `"nothing to commit or push"`
  - `test_tool_vault_sync_custom_message` — message param → passed to `commit()`

- [x] **GREEN** Implement `vault_sync` tool.

---

## Phase 6 — `__main__.py`

### 6.1 Transport flag

- [x] **RED** Write `tests/test_main.py`:
  - `test_transport_streamable_http` — `--transport streamable-http` → server started with `transport="streamable-http"`
  - `test_transport_stdio` — `--transport stdio` → server started with `transport="stdio"`
  - `test_transport_default_is_streamable_http` — no flag → defaults to `streamable-http`

- [x] **GREEN** Implement `--transport` arg parsing in `__main__.py`.

### 6.2 Server bind config

- [x] **RED** Add tests:
  - `test_port_from_env` — `SERVER_PORT=9090` → server started with port `9090`
  - `test_ip_from_env` — `SERVER_IP=127.0.0.1` → server started with host `127.0.0.1`

- [x] **GREEN** Pass `ServerConfig.port` and `ServerConfig.ip` into `mcp.run()`.

### 6.3 Startup sequence

- [x] **RED** Add tests:
  - `test_vaults_initialised_before_server_starts` — `init_vault`/`init_local_vault` called before `mcp.run()`
  - `test_all_configured_vaults_initialised` — each vault in config → one init call each

- [x] **GREEN** Implement startup sequence: iterate vaults, call correct init function per type, then start server.

---

## Phase 7 — Packaging and container

- [x] **7.1** Create `.dockerignore` — exclude `.git/`, `*.md`, `.env*`, `__pycache__/`, `.ruff_cache/`, `tests/`

- [x] **7.2** Create `Dockerfile` as specified in SPEC.md

- [x] **7.3** Verify `docker build` completes without error — run manually: `docker build -t obsidian-vault-mcp:dev .`

- [x] **7.4** Smoke test — run manually: `docker run --rm -e VAULT_TEST_REPO=local -e VAULT_DEFAULT=test obsidian-vault-mcp:dev --transport stdio`

---

## Phase 8 — Convention authority (`AGENTS.md`)

The vault is self-describing: each vault carries an `AGENTS.md` at its root. The server seeds a default if missing, loads it on startup, returns it via MCP `initialize.serverInfo.instructions`, exposes it via `vault_conventions`, and allows mutation only via `update_conventions`. `note_*` tools refuse to touch `AGENTS.md` / `CLAUDE.md` at vault root.

### 8.1 Bundle the default template

- [x] **8.1.1** Confirm `obsidian_vault_mcp/default_AGENTS.md` exists in the package (already added). Ensure `pyproject.toml` includes it as package data so it ships in the wheel and is readable via `importlib.resources`.

### 8.2 `conventions.py` — module

Create a new module. All tests use `tmp_path` (real filesystem).

- [x] **8.2.1 RED** Write `tests/test_conventions.py`:
  - `test_load_returns_existing_agents_md` — `<vault>/AGENTS.md` exists with content → returned as-is
  - `test_load_seeds_default_when_missing` — `AGENTS.md` absent → file is created with `default_AGENTS.md` content, returned
  - `test_seeded_file_is_committed` — after seeding, `git status` shows the file as committed (mock `subprocess.run`, assert `git add AGENTS.md` + `git commit` were called; push **not** called)

- [x] **8.2.2 GREEN** Implement `conventions.load(vault_path)` returning the concatenated string and seeding `AGENTS.md` from `importlib.resources` if missing. Use `git_sync.commit()` for the seed commit; do not push.

### 8.3 In-memory cache + refresh

- [x] **8.3.1 RED** Add tests:
  - `test_cache_returns_same_content_on_repeated_calls` — `load` then `get` returns cached value without re-reading disk
  - `test_refresh_rereads_from_disk` — edit file out-of-band, call `refresh(vault_path)` → cache reflects new content
  - `test_per_vault_cache_isolation` — two vaults → caches do not bleed into each other

- [x] **8.3.2 GREEN** Implement a per-vault cache keyed by vault name (dict in `conventions.py`). Expose `get(vault_name)`, `refresh(vault_name, vault_path)`.

### 8.4 `vault_conventions` MCP tool

- [x] **8.4.1 RED** Add to `tests/test_server.py`:
  - `test_tool_vault_conventions_default_vault` — no `vault` param → returns default vault's conventions
  - `test_tool_vault_conventions_explicit_vault` — `vault` param → returns that vault's conventions
  - `test_tool_vault_conventions_unknown_vault_returns_error` — bad vault name → error response

- [x] **8.4.2 GREEN** Add `vault_conventions(vault?)` tool calling `conventions.get(...)`.

### 8.5 `update_conventions` MCP tool

- [x] **8.5.1 RED** Add tests:
  - `test_tool_update_conventions_replaces_full_file` — `content` only → `AGENTS.md` rewritten; cache refreshed
  - `test_tool_update_conventions_replaces_section` — `section="Frontmatter"`, `content="..."` → only that `## heading` block replaced, others preserved
  - `test_tool_update_conventions_missing_section_creates_it` — `section` not in file → section appended at end
  - `test_tool_update_conventions_refuses_other_paths` — implicit: tool target is hardcoded to `AGENTS.md`; verify no other path is writable through it
  - `test_tool_update_conventions_no_implicit_push` — verifies commit happens but push does not (push is `vault_sync`'s job)

- [x] **8.5.2 GREEN** Implement `update_conventions(vault?, content, section?)`: write full file or in-place section replace, then `conventions.refresh()`, then `git_sync.commit()` (no push).

### 8.6 Protected paths on `note_*` tools

- [x] **8.6.1 RED** Add to `tests/test_vault.py`:
  - `test_note_create_refuses_agents_md` — path `AGENTS.md` at root → raises (or returns a typed error)
  - `test_note_create_refuses_claude_md` — same for `CLAUDE.md`
  - `test_note_read_refuses_agents_md`
  - `test_note_read_refuses_claude_md`
  - `test_note_update_refuses_protected`
  - `test_note_delete_refuses_protected`
  - `test_protected_only_at_root` — `Notes/AGENTS.md` is **not** protected (only vault root counts)

- [x] **8.6.2 GREEN** Add a protected-path check in `Vault.resolve()` or wrappers used by the four `note_*` methods. Constant: `PROTECTED_ROOT_FILES = {"AGENTS.md", "CLAUDE.md"}`.

- [x] **8.6.3 RED** Add tool-level tests in `tests/test_server.py` confirming the error surfaces as an MCP error response, not an unhandled exception, for each of the four tools.

- [x] **8.6.4 GREEN** Adjust tool error handling if needed.

### 8.7 `note_list` excludes protected files

- [x] **8.7.1 RED** Add to `tests/test_vault.py`:
  - `test_note_list_excludes_agents_md_at_root` — vault root contains `AGENTS.md`, `notes/foo.md` → result contains `foo.md` only
  - `test_note_list_excludes_claude_md_at_root`
  - `test_note_list_includes_nested_agents_md` — `Notes/AGENTS.md` exists → included (exclusion is root-only)

- [x] **8.7.2 GREEN** Filter `PROTECTED_ROOT_FILES` out of `note_list` results when listing the vault root.

### 8.8 Startup seeding + cache priming

- [x] **8.8.1 RED** Add to `tests/test_main.py`:
  - `test_startup_seeds_missing_agents_md` — vault initialised without `AGENTS.md` → after startup, file exists and is committed
  - `test_startup_loads_conventions_for_each_vault` — `conventions.load()` called once per configured vault before `mcp.run()`

- [x] **8.8.2 GREEN** Extend the startup sequence in `__main__.py` to call `conventions.load(vault_path)` for each vault after init, before starting the server.

### 8.9 MCP `initialize.instructions`

- [x] **8.9.1 RED** Add to `tests/test_server.py`:
  - `test_initialize_instructions_contains_all_vault_conventions` — in-process MCP client `initialize` response → `serverInfo.instructions` contains a labelled `## Vault: <name>` section for every configured vault, with that vault's conventions text
  - `test_initialize_instructions_updated_after_update_conventions` — call `update_conventions`, re-initialize → new content reflected

- [x] **8.9.2 GREEN** Build the `instructions` payload in `server.py` at FastMCP construction time (or via a getter the server framework calls each handshake) by iterating `conventions.get(vault_name)` for each configured vault.

---

## Phase 9 — `ENFORCE_FRONTMATTER` flag

Default `true` preserves current behaviour. Set `false` to make the server schema-agnostic: no auto-injection of `title`/`created`/`modified`/`aliases`, no `modified` bump on update. Tag merging (mechanical preservation) is independent of the flag.

### 9.1 Config flag

- [x] **9.1.1 RED** Add to `tests/test_config.py`:
  - `test_enforce_frontmatter_default_true` — no `ENFORCE_FRONTMATTER` env → `True`
  - `test_enforce_frontmatter_false` — `ENFORCE_FRONTMATTER=false` → `False`
  - `test_enforce_frontmatter_true_explicit` — `ENFORCE_FRONTMATTER=true` → `True`
  - `test_enforce_frontmatter_case_insensitive` — `False`, `FALSE`, `0` all parse as `False`; `True`, `TRUE`, `1` as `True`

- [x] **9.1.2 GREEN** Add `enforce_frontmatter: bool` to `ServerConfig` (or wherever the runtime config lives). Default `True`.

### 9.2 `note_create` respects the flag

- [x] **9.2.1 RED** Add to `tests/test_vault.py`:
  - `test_note_create_no_enforcement_no_default_fields` — `enforce=False`, no tags passed → file has no `title`, `created`, `modified`, `aliases` (frontmatter block may be empty or absent)
  - `test_note_create_no_enforcement_preserves_passed_tags` — `enforce=False`, `tags=["x"]` → file has `tags: [x]` only

- [x] **9.2.2 GREEN** Branch in `Vault.note_create` on the enforcement flag (plumbed in via constructor or call arg). When off, skip `build_metadata` defaults and write only what was passed.

### 9.3 `note_update` respects the flag

- [x] **9.3.1 RED** Add to `tests/test_vault.py`:
  - `test_note_update_no_enforcement_does_not_bump_modified` — `enforce=False`, update existing note → `modified` field unchanged (or absent)
  - `test_note_update_no_enforcement_preserves_existing_fields` — existing custom field (e.g., `author`) preserved untouched
  - `test_note_update_no_enforcement_tag_merge_still_works` — tag merging still applies

- [x] **9.3.2 GREEN** Branch in `Vault.note_update`: when enforcement off, do not touch `modified`, and skip default-field injection. Keep tag merging.

### 9.4 Wire flag from config → server → vault

- [x] **9.4.1 RED** Add to `tests/test_server.py`:
  - `test_server_passes_enforce_flag_to_vault` — `ENFORCE_FRONTMATTER=false` → tool calls behave per Phase 9.2 / 9.3 through the MCP interface

- [x] **9.4.2 GREEN** Read `ServerConfig.enforce_frontmatter` in `server.py` and pass it to `Vault` instances (or to the relevant methods).

### 9.5 SPEC alignment check

- [x] **9.5.1** Manual: re-read SPEC.md `## Config` and `## Frontmatter format` sections to confirm `ENFORCE_FRONTMATTER` is documented (env var, default, behaviour on/off). Already updated in this iteration — verify against the implementation when done.

---

## Notes on already-checked phases

The following items remain green because their original behaviour is the default-on path. They do **not** need to be unchecked, but the new tasks above extend their coverage:

- **1.4 / 1.x ServerConfig** — extended by **9.1** (new `enforce_frontmatter` field).
- **3.3 build_metadata / 3.4 merge_tags** — still correct; `build_metadata` is now only called when `enforce_frontmatter=True` (handled at the call site in `vault.py`, see **9.2 / 9.3**).
- **4.2–4.5 note_* methods** — extended by **8.6** (protected-path guard) and **9.2 / 9.3** (enforcement flag).
- **4.6 note_list** — extended by **8.7** (root-level exclusion of protected files).
- **5.2–5.5 note_* tools** — extended by **8.6.3** (typed error on protected paths).
- **6.3 startup sequence** — extended by **8.8** (convention loading per vault).

---

## Phase 10 — Multi-writer safety (`pull --rebase`)

The server may run as multiple instances against the same vault remote (local + central + Obsidian app on host as a third clone). To stay coherent, `vault_sync` and `update_conventions` now pull-rebase before pushing, and AGENTS.md seeding handles the first-boot race. `note_*` writes are still local-only — they sync through `vault_sync`.

This phase supersedes the no-push behaviour of **8.5** (`update_conventions` used to defer its push to `vault_sync`; it now pushes immediately with rebase) and the simple push behaviour of **5.8** (`vault_sync` now pulls before pushing).

### 10.1 `git_sync.pull_rebase` helper

- [ ] **10.1.1 RED** Add to `tests/test_git_sync.py`:
  - `test_pull_rebase_calls_git` — calls `git -C <path> pull --rebase`
  - `test_pull_rebase_returns_clean_on_success` — `subprocess.run` returns 0 → returns a "clean" marker (e.g. `PullResult(conflict=False, files=[])`)
  - `test_pull_rebase_returns_conflict_with_paths` — rebase exits non-zero and `git diff --name-only --diff-filter=U` returns two paths → returns `PullResult(conflict=True, files=[<paths>])` and the helper has called `git rebase --abort` to leave the tree clean

- [ ] **10.1.2 GREEN** Implement `pull_rebase(path) -> PullResult` in `git_sync.py`. On non-zero exit, query unmerged paths, run `git rebase --abort`, return the conflict result. Do not raise — callers handle the result.

### 10.2 `vault_sync` pull-rebase + AGENTS.md cache refresh

- [ ] **10.2.1 RED** Extend `tests/test_server.py` (mock `git_sync.pull_rebase` and `git_sync.push`):
  - `test_vault_sync_pulls_before_push_remote` — remote vault, dirty tree → commit, pull-rebase, push, in that order
  - `test_vault_sync_skips_pull_for_local` — local vault → no pull-rebase call
  - `test_vault_sync_rebase_conflict_aborts_and_reports` — pull-rebase returns conflict → push **not** called; response message contains `"rebase conflict"` and the conflicting paths; tool returns a typed error, not an unhandled exception
  - `test_vault_sync_refreshes_conventions_when_agents_md_changed` — pull-rebase brings down a new `AGENTS.md` → `conventions.refresh()` is called for this vault before the response returns
  - `test_vault_sync_no_refresh_when_agents_md_unchanged` — pull-rebase brings down notes only → `conventions.refresh()` not called
  - `test_vault_sync_status_messages_post_rebase` — update the existing status-message assertions to reflect the new step (`"committed and pushed"`, `"nothing to commit, pushed 1 existing commit after rebase"`, `"nothing to commit or push"`, `"committed (local only)"`, `"rebase conflict: <paths>"`)

- [ ] **10.2.2 GREEN** Update `vault_sync` tool in `server.py`: after commit (if any), call `pull_rebase` for remote vaults, branch on result, refresh conventions when needed, then push.

### 10.3 `update_conventions` pushes immediately

- [ ] **10.3.1 RED** Update `tests/test_server.py`. Replace the old `test_tool_update_conventions_no_implicit_push` with the inverse behaviour, and add the rebase-conflict path:
  - `test_tool_update_conventions_pushes_immediately_remote` — remote vault → commit, pull-rebase, push, all within the single tool call
  - `test_tool_update_conventions_skips_push_for_local` — local vault → commit only, no pull/push
  - `test_tool_update_conventions_rebase_conflict_aborts` — pull-rebase returns conflict on `AGENTS.md` → push not called; cache refreshed from the (now-current) remote state; response indicates `"conventions diverged — re-read with vault_conventions and reapply"`
  - `test_tool_update_conventions_cache_refreshed_after_success` — successful push → cache holds the just-pushed content
  - **Remove** the obsolete assertion that push is *not* called for remote vaults

- [ ] **10.3.2 GREEN** Update `update_conventions` tool in `server.py`: after commit, for remote vaults call `pull_rebase`, branch on result (abort + refresh + error response on conflict; otherwise push + refresh).

### 10.4 Startup seeding race

- [ ] **10.4.1 RED** Add to `tests/test_main.py` (or `tests/test_conventions.py`, wherever the startup seed currently lives):
  - `test_startup_seed_after_pull_not_before` — verify call order: clone/pull first, then check for AGENTS.md, then seed if missing. Mock `git_sync` to assert ordering
  - `test_startup_seed_pushes_immediately_remote` — remote vault, no remote AGENTS.md → after startup, push has been called for the seed commit
  - `test_startup_seed_handles_lost_race` — simulate push rejection on seed (mock `push` to raise non-fast-forward) → server runs `git reset --hard origin/<branch>`, re-loads `AGENTS.md` from the now-current remote, cache reflects the **remote** content, not the local default template
  - `test_startup_seed_local_vault_no_push` — local vault → seed commit only, no push attempt

- [ ] **10.4.2 GREEN** Update the startup seeding step (in `conventions.py` or `__main__.py`, wherever it lives) to: pull/clone first, then check AGENTS.md, then on missing → seed + commit + (remote only) pull-rebase + push, with the reset-hard fallback on push rejection.

### 10.5 SPEC alignment check

- [ ] **10.5.1** Manual: re-read SPEC.md sections `## Convention Authority: AGENTS.md` (Load order on startup), `### vault_sync behaviour`, `### update_conventions behaviour`. Confirm the implemented behaviour matches: pull-rebase ordering, conflict abort + error response, cache refresh after pull, immediate push for `update_conventions`, seed-after-pull with reset-hard fallback.

---

## Notes on superseded phases

- **5.8 vault_sync tests** — original tests assumed commit + push only. Phase **10.2** adds the pull-rebase step, the conflict path, and the AGENTS.md cache-refresh trigger. Existing status-message assertions need updating in place (see **10.2.1**).
- **8.5 update_conventions tests** — original test `test_tool_update_conventions_no_implicit_push` is now wrong: `update_conventions` **does** push immediately. Remove that assertion and add the new ones in **10.3.1**.
- **8.8 startup seeding** — original test confirmed file exists + committed. Phase **10.4** tightens the ordering (after pull, not before) and adds the lost-race fallback.
