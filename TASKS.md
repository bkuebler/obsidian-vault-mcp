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
