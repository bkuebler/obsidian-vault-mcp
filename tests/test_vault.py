from datetime import date
import pytest
from obsidian_vault_mcp.vault import Vault


# --- 4.1 Path resolution and traversal protection ---


def test_resolve_path_within_vault(tmp_path):
    vault = Vault(tmp_path)
    resolved = vault.resolve("notes/foo.md")
    assert resolved == tmp_path / "notes" / "foo.md"
    assert resolved.is_relative_to(tmp_path)


def test_traversal_raises(tmp_path):
    vault = Vault(tmp_path)
    with pytest.raises(ValueError, match="traversal"):
        vault.resolve("../../etc/passwd")


def test_traversal_encoded_raises(tmp_path):
    vault = Vault(tmp_path)
    with pytest.raises(ValueError, match="traversal"):
        vault.resolve("notes/%2e%2e/secret")


# --- 4.2 note_create ---


def test_note_create_writes_file(tmp_path):
    vault = Vault(tmp_path)
    vault.note_create("note.md", "Hello world")
    assert (tmp_path / "note.md").exists()


def test_note_create_frontmatter_present(tmp_path):
    vault = Vault(tmp_path)
    vault.note_create("note.md", "Hello world")
    content = (tmp_path / "note.md").read_text()
    assert "title:" in content
    assert "created:" in content
    assert "modified:" in content


def test_note_create_body_present(tmp_path):
    vault = Vault(tmp_path)
    vault.note_create("note.md", "Hello world")
    content = (tmp_path / "note.md").read_text()
    assert "Hello world" in content


def test_note_create_with_tags(tmp_path):
    vault = Vault(tmp_path)
    vault.note_create("note.md", "Content", tags=["work", "session"])
    content = (tmp_path / "note.md").read_text()
    assert "work" in content
    assert "session" in content


def test_note_create_creates_subdirs(tmp_path):
    vault = Vault(tmp_path)
    vault.note_create("Sessions/2026-06-01-topic.md", "Content")
    assert (tmp_path / "Sessions" / "2026-06-01-topic.md").exists()


# --- 4.3 note_read ---


def test_note_read_returns_metadata_and_body(tmp_path):
    vault = Vault(tmp_path)
    vault.note_create("note.md", "Body text", tags=["foo"])
    metadata, body = vault.note_read("note.md")
    assert "title" in metadata
    assert "foo" in metadata["tags"]
    assert "Body text" in body


def test_note_read_missing_file_raises(tmp_path):
    vault = Vault(tmp_path)
    with pytest.raises(FileNotFoundError):
        vault.note_read("nonexistent.md")


# --- 4.4 note_update ---


def test_update_replaces_body(tmp_path):
    vault = Vault(tmp_path)
    vault.note_create("note.md", "Original body")
    vault.note_update("note.md", content="New body")
    _, body = vault.note_read("note.md")
    assert "New body" in body
    assert "Original body" not in body


def test_update_appends_body(tmp_path):
    vault = Vault(tmp_path)
    vault.note_create("note.md", "Original body")
    vault.note_update("note.md", content="Appended line", append=True)
    _, body = vault.note_read("note.md")
    assert "Original body" in body
    assert "Appended line" in body


def test_update_tags_only(tmp_path):
    vault = Vault(tmp_path)
    vault.note_create("note.md", "Unchanged body")
    vault.note_update("note.md", tags=["new-tag"])
    metadata, body = vault.note_read("note.md")
    assert "new-tag" in metadata["tags"]
    assert "Unchanged body" in body


def test_update_append_without_content_raises(tmp_path):
    vault = Vault(tmp_path)
    vault.note_create("note.md", "Body")
    with pytest.raises(ValueError):
        vault.note_update("note.md", append=True)


def test_update_bumps_modified(tmp_path):
    vault = Vault(tmp_path)
    vault.note_create("note.md", "Body")
    vault.note_update("note.md", content="New body")
    metadata, _ = vault.note_read("note.md")
    assert metadata["modified"] == date.today()


def test_update_never_changes_created(tmp_path):
    vault = Vault(tmp_path)
    vault.note_create("note.md", "Body")
    original_created = vault.note_read("note.md")[0]["created"]
    vault.note_update("note.md", content="Updated body")
    metadata, _ = vault.note_read("note.md")
    assert metadata["created"] == original_created


# --- 4.5 note_delete ---


def test_note_delete_removes_file(tmp_path):
    vault = Vault(tmp_path)
    vault.note_create("note.md", "Body")
    vault.note_delete("note.md")
    assert not (tmp_path / "note.md").exists()


def test_note_delete_missing_file_raises(tmp_path):
    vault = Vault(tmp_path)
    with pytest.raises(FileNotFoundError):
        vault.note_delete("nonexistent.md")


# --- 4.6 note_list ---


def test_note_list_root(tmp_path):
    vault = Vault(tmp_path)
    vault.note_create("a.md", "A")
    vault.note_create("b.md", "B")
    entries = vault.note_list()
    paths = [e["path"] for e in entries]
    assert "a.md" in paths
    assert "b.md" in paths


def test_note_list_folder(tmp_path):
    vault = Vault(tmp_path)
    vault.note_create("Sessions/s1.md", "S1")
    vault.note_create("Notes/n1.md", "N1")
    entries = vault.note_list(folder="Sessions")
    paths = [e["path"] for e in entries]
    assert "Sessions/s1.md" in paths
    assert all("Sessions" in p for p in paths)


def test_note_list_returns_paths_and_titles(tmp_path):
    vault = Vault(tmp_path)
    vault.note_create("my-note.md", "Content")
    entries = vault.note_list()
    assert len(entries) == 1
    assert "path" in entries[0]
    assert "title" in entries[0]
    assert entries[0]["title"] == "my-note"


def test_note_list_ignores_non_md(tmp_path):
    vault = Vault(tmp_path)
    vault.note_create("note.md", "Content")
    (tmp_path / "image.png").write_bytes(b"")
    (tmp_path / "data.txt").write_text("text")
    entries = vault.note_list()
    assert len(entries) == 1


# --- 4.7 note_search ---


def test_search_matches_body_content(tmp_path):
    vault = Vault(tmp_path)
    vault.note_create("note.md", "The quick brown fox")
    results = vault.note_search("quick")
    assert len(results) == 1


def test_search_matches_frontmatter(tmp_path):
    vault = Vault(tmp_path)
    vault.note_create("note.md", "Body", tags=["research"])
    results = vault.note_search("research")
    assert len(results) == 1


def test_search_case_insensitive(tmp_path):
    vault = Vault(tmp_path)
    vault.note_create("note.md", "hello world")
    results = vault.note_search("HELLO")
    assert len(results) == 1


def test_search_no_match_returns_empty(tmp_path):
    vault = Vault(tmp_path)
    vault.note_create("note.md", "hello world")
    results = vault.note_search("zzznomatch")
    assert results == []


def test_search_tag_filter(tmp_path):
    vault = Vault(tmp_path)
    vault.note_create("tagged.md", "content", tags=["keep"])
    vault.note_create("other.md", "content")
    results = vault.note_search("content", tags=["keep"])
    paths = [r["path"] for r in results]
    assert "tagged.md" in paths
    assert "other.md" not in paths


def test_search_folder_scoped(tmp_path):
    vault = Vault(tmp_path)
    vault.note_create("Sessions/s1.md", "needle")
    vault.note_create("Notes/n1.md", "needle")
    results = vault.note_search("needle", folder="Sessions")
    paths = [r["path"] for r in results]
    assert all("Sessions" in p for p in paths)
    assert len(results) == 1


# --- 8.6 Protected paths ---


def test_note_create_refuses_agents_md(tmp_path):
    vault = Vault(tmp_path)
    with pytest.raises(PermissionError):
        vault.note_create("AGENTS.md", "content")


def test_note_create_refuses_claude_md(tmp_path):
    vault = Vault(tmp_path)
    with pytest.raises(PermissionError):
        vault.note_create("CLAUDE.md", "content")


def test_note_read_refuses_agents_md(tmp_path):
    vault = Vault(tmp_path)
    (tmp_path / "AGENTS.md").write_text("content")
    with pytest.raises(PermissionError):
        vault.note_read("AGENTS.md")


def test_note_read_refuses_claude_md(tmp_path):
    vault = Vault(tmp_path)
    (tmp_path / "CLAUDE.md").write_text("content")
    with pytest.raises(PermissionError):
        vault.note_read("CLAUDE.md")


def test_note_update_refuses_protected(tmp_path):
    vault = Vault(tmp_path)
    (tmp_path / "AGENTS.md").write_text("---\ntitle: x\n---\nbody")
    with pytest.raises(PermissionError):
        vault.note_update("AGENTS.md", content="hack")


def test_note_delete_refuses_protected(tmp_path):
    vault = Vault(tmp_path)
    (tmp_path / "AGENTS.md").write_text("content")
    with pytest.raises(PermissionError):
        vault.note_delete("AGENTS.md")


def test_protected_only_at_root(tmp_path):
    vault = Vault(tmp_path)
    vault.note_create("Notes/AGENTS.md", "nested")
    assert (tmp_path / "Notes" / "AGENTS.md").exists()


# --- 8.7 note_list excludes protected files at root ---


def test_note_list_excludes_agents_md_at_root(tmp_path):
    vault = Vault(tmp_path)
    (tmp_path / "AGENTS.md").write_text("---\ntitle: agents\n---\n")
    vault.note_create("notes/foo.md", "body")
    entries = vault.note_list()
    paths = [e["path"] for e in entries]
    assert "AGENTS.md" not in paths
    assert "notes/foo.md" in paths


def test_note_list_excludes_claude_md_at_root(tmp_path):
    vault = Vault(tmp_path)
    (tmp_path / "CLAUDE.md").write_text("---\ntitle: claude\n---\n")
    vault.note_create("a.md", "body")
    entries = vault.note_list()
    paths = [e["path"] for e in entries]
    assert "CLAUDE.md" not in paths


def test_note_list_includes_nested_agents_md(tmp_path):
    vault = Vault(tmp_path)
    vault.note_create("Notes/AGENTS.md", "nested agents")
    entries = vault.note_list()
    paths = [e["path"] for e in entries]
    assert any("AGENTS.md" in p and "Notes" in p for p in paths)


# --- 9.2 note_create enforcement flag ---


def test_note_create_no_enforcement_no_default_fields(tmp_path):
    vault = Vault(tmp_path, enforce_frontmatter=False)
    vault.note_create("note.md", "content")
    content = (tmp_path / "note.md").read_text()
    assert "title:" not in content
    assert "created:" not in content
    assert "modified:" not in content
    assert "aliases:" not in content


def test_note_create_no_enforcement_preserves_passed_tags(tmp_path):
    vault = Vault(tmp_path, enforce_frontmatter=False)
    vault.note_create("note.md", "content", tags=["x"])
    content = (tmp_path / "note.md").read_text()
    assert "x" in content


# --- 9.3 note_update enforcement flag ---


def test_note_update_no_enforcement_does_not_bump_modified(tmp_path):
    vault_on = Vault(tmp_path, enforce_frontmatter=True)
    vault_on.note_create("note.md", "body")
    original_modified = vault_on.note_read("note.md")[0]["modified"]

    vault_off = Vault(tmp_path, enforce_frontmatter=False)
    vault_off.note_update("note.md", content="updated body")
    new_modified = vault_off.note_read("note.md")[0]["modified"]
    assert new_modified == original_modified


def test_note_update_no_enforcement_preserves_existing_fields(tmp_path):
    (tmp_path / "note.md").write_text("---\nauthor: Alice\n---\nBody\n")
    vault = Vault(tmp_path, enforce_frontmatter=False)
    vault.note_update("note.md", content="Updated body")
    meta, _ = vault.note_read("note.md")
    assert meta.get("author") == "Alice"


def test_note_update_no_enforcement_tag_merge_still_works(tmp_path):
    (tmp_path / "note.md").write_text("---\ntags:\n  - existing\n---\nBody\n")
    vault = Vault(tmp_path, enforce_frontmatter=False)
    vault.note_update("note.md", tags=["new"])
    meta, _ = vault.note_read("note.md")
    assert "existing" in meta["tags"]
    assert "new" in meta["tags"]
