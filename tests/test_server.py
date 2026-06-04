from unittest.mock import patch
import pytest
from obsidian_vault_mcp.config import Config, VaultConfig, ServerConfig
from obsidian_vault_mcp import conventions, server
from obsidian_vault_mcp.git_sync import PullResult


# --- helpers ---


def _make_config(vaults: dict[str, str], default: str | None = None) -> Config:
    vault_configs = [
        VaultConfig(name=name, url=url, is_local=(url == "local"))
        for name, url in vaults.items()
    ]
    return Config(
        vaults=vault_configs,
        default_vault=default or list(vaults.keys())[0],
        server=ServerConfig(port=8080, ip="0.0.0.0"),
    )


@pytest.fixture()
def personal_vault(tmp_path):
    config = _make_config({"personal": "https://ghp_x@github.com/u/p.git"})
    server.setup(config, vaults_root=tmp_path)
    return tmp_path / "personal"


@pytest.fixture()
def two_vaults(tmp_path):
    config = _make_config(
        {
            "personal": "https://ghp_x@github.com/u/p.git",
            "corporate": "https://ghp_y@github.com/o/c.git",
        },
        default="personal",
    )
    server.setup(config, vaults_root=tmp_path)
    return tmp_path


@pytest.fixture()
def local_vault(tmp_path):
    config = _make_config({"notes": "local"})
    server.setup(config, vaults_root=tmp_path)
    return tmp_path / "notes"


# --- 5.1 vault_list ---


def test_vault_list_returns_all_vaults(two_vaults):
    with (
        patch("obsidian_vault_mcp.server.git_sync.is_dirty", return_value=False),
        patch("obsidian_vault_mcp.server.git_sync.ahead_behind", return_value=(0, 0)),
    ):
        result = server.vault_list()
    names = [v["name"] for v in result]
    assert "personal" in names
    assert "corporate" in names


def test_vault_list_remote_includes_ahead_behind(personal_vault):
    with (
        patch("obsidian_vault_mcp.server.git_sync.is_dirty", return_value=True),
        patch("obsidian_vault_mcp.server.git_sync.ahead_behind", return_value=(2, 1)),
    ):
        result = server.vault_list()
    entry = result[0]
    assert entry["dirty"] is True
    assert entry["ahead"] == 2
    assert entry["behind"] == 1


def test_vault_list_local_no_ahead_behind(local_vault):
    with patch("obsidian_vault_mcp.server.git_sync.is_dirty", return_value=False):
        result = server.vault_list()
    entry = result[0]
    assert entry["dirty"] is False
    assert "ahead" not in entry
    assert "behind" not in entry


# --- 5.2 note_create ---


def test_tool_note_create_success(personal_vault):
    personal_vault.mkdir(parents=True, exist_ok=True)
    result = server.note_create(path="note.md", content="Hello")
    assert "ok" in result.lower() or result == "ok"
    assert (personal_vault / "note.md").exists()


def test_tool_note_create_default_vault(personal_vault):
    personal_vault.mkdir(parents=True, exist_ok=True)
    server.note_create(path="default.md", content="Body")
    assert (personal_vault / "default.md").exists()


def test_tool_note_create_explicit_vault(two_vaults):
    (two_vaults / "corporate").mkdir(parents=True, exist_ok=True)
    server.note_create(path="corp.md", content="Body", vault="corporate")
    assert (two_vaults / "corporate" / "corp.md").exists()
    assert not (two_vaults / "personal" / "corp.md").exists()


# --- 5.3 note_read ---


def test_tool_note_read_returns_frontmatter_and_body(personal_vault):
    personal_vault.mkdir(parents=True, exist_ok=True)
    server.note_create(path="read-me.md", content="Read body")
    result = server.note_read(path="read-me.md")
    assert "Read body" in result
    assert "title" in result


def test_tool_note_read_missing_returns_error(personal_vault):
    personal_vault.mkdir(parents=True, exist_ok=True)
    result = server.note_read(path="ghost.md")
    assert "error" in result.lower() or "not found" in result.lower()


# --- 5.4 note_update ---


def test_tool_note_update_replace(personal_vault):
    personal_vault.mkdir(parents=True, exist_ok=True)
    server.note_create(path="u.md", content="Original")
    server.note_update(path="u.md", content="Replaced")
    result = server.note_read(path="u.md")
    assert "Replaced" in result
    assert "Original" not in result


def test_tool_note_update_append(personal_vault):
    personal_vault.mkdir(parents=True, exist_ok=True)
    server.note_create(path="u.md", content="Original")
    server.note_update(path="u.md", content="Appended", append=True)
    result = server.note_read(path="u.md")
    assert "Original" in result
    assert "Appended" in result


def test_tool_note_update_tags_only(personal_vault):
    personal_vault.mkdir(parents=True, exist_ok=True)
    server.note_create(path="u.md", content="Body")
    server.note_update(path="u.md", tags=["new-tag"])
    result = server.note_read(path="u.md")
    assert "new-tag" in result
    assert "Body" in result


def test_tool_note_update_append_no_content_returns_error(personal_vault):
    personal_vault.mkdir(parents=True, exist_ok=True)
    server.note_create(path="u.md", content="Body")
    result = server.note_update(path="u.md", append=True)
    assert "error" in result.lower()


# --- 5.5 note_delete ---


def test_tool_note_delete_success(personal_vault):
    personal_vault.mkdir(parents=True, exist_ok=True)
    server.note_create(path="del.md", content="Body")
    result = server.note_delete(path="del.md")
    assert not (personal_vault / "del.md").exists()
    assert "ok" in result.lower() or result == "ok"


def test_tool_note_delete_missing_returns_error(personal_vault):
    personal_vault.mkdir(parents=True, exist_ok=True)
    result = server.note_delete(path="ghost.md")
    assert "error" in result.lower() or "not found" in result.lower()


# --- 5.6 note_list ---


def test_tool_note_list_no_folder(personal_vault):
    personal_vault.mkdir(parents=True, exist_ok=True)
    server.note_create(path="a.md", content="A")
    server.note_create(path="b.md", content="B")
    result = server.note_list()
    assert "a.md" in result
    assert "b.md" in result


def test_tool_note_list_with_folder(personal_vault):
    personal_vault.mkdir(parents=True, exist_ok=True)
    server.note_create(path="Sessions/s1.md", content="S1")
    server.note_create(path="Notes/n1.md", content="N1")
    result = server.note_list(folder="Sessions")
    assert "s1.md" in result
    assert "n1.md" not in result


# --- 5.7 note_search ---


def test_tool_note_search_query_only(personal_vault):
    personal_vault.mkdir(parents=True, exist_ok=True)
    server.note_create(path="s.md", content="findme")
    result = server.note_search(query="findme")
    assert "s.md" in result


def test_tool_note_search_with_tags(personal_vault):
    personal_vault.mkdir(parents=True, exist_ok=True)
    server.note_create(path="tagged.md", content="findme", tags=["work"])
    server.note_create(path="other.md", content="findme")
    result = server.note_search(query="findme", tags=["work"])
    assert "tagged.md" in result
    assert "other.md" not in result


def test_tool_note_search_with_folder(personal_vault):
    personal_vault.mkdir(parents=True, exist_ok=True)
    server.note_create(path="Sessions/s.md", content="needle")
    server.note_create(path="Notes/n.md", content="needle")
    result = server.note_search(query="needle", folder="Sessions")
    assert "s.md" in result
    assert "Notes" not in result


# --- 5.8 vault_sync ---


def test_tool_vault_sync_dirty_remote(personal_vault):
    personal_vault.mkdir(parents=True, exist_ok=True)
    with (
        patch("obsidian_vault_mcp.server.git_sync.is_dirty", return_value=True),
        patch("obsidian_vault_mcp.server.git_sync.commit") as mock_commit,
        patch(
            "obsidian_vault_mcp.server.git_sync.pull_rebase",
            return_value=PullResult(conflict=False, files=[]),
        ),
        patch("obsidian_vault_mcp.server.git_sync.ahead_behind", return_value=(1, 0)),
        patch("obsidian_vault_mcp.server.git_sync.push") as mock_push,
    ):
        result = server.vault_sync()
    mock_commit.assert_called_once()
    mock_push.assert_called_once()
    assert result == "committed and pushed"


def test_tool_vault_sync_clean_remote_with_unpushed(personal_vault):
    personal_vault.mkdir(parents=True, exist_ok=True)
    with (
        patch("obsidian_vault_mcp.server.git_sync.is_dirty", return_value=False),
        patch("obsidian_vault_mcp.server.git_sync.commit") as mock_commit,
        patch(
            "obsidian_vault_mcp.server.git_sync.pull_rebase",
            return_value=PullResult(conflict=False, files=[]),
        ),
        patch("obsidian_vault_mcp.server.git_sync.ahead_behind", return_value=(1, 0)),
        patch("obsidian_vault_mcp.server.git_sync.push") as mock_push,
    ):
        result = server.vault_sync()
    mock_commit.assert_not_called()
    mock_push.assert_called_once()
    assert result == "nothing to commit, pushed 1 existing commit after rebase"


def test_tool_vault_sync_nothing_to_do_remote(personal_vault):
    personal_vault.mkdir(parents=True, exist_ok=True)
    with (
        patch("obsidian_vault_mcp.server.git_sync.is_dirty", return_value=False),
        patch("obsidian_vault_mcp.server.git_sync.commit") as mock_commit,
        patch(
            "obsidian_vault_mcp.server.git_sync.pull_rebase",
            return_value=PullResult(conflict=False, files=[]),
        ),
        patch("obsidian_vault_mcp.server.git_sync.ahead_behind", return_value=(0, 0)),
        patch("obsidian_vault_mcp.server.git_sync.push") as mock_push,
    ):
        result = server.vault_sync()
    mock_commit.assert_not_called()
    mock_push.assert_not_called()
    assert result == "nothing to commit or push"


def test_tool_vault_sync_dirty_local(local_vault):
    local_vault.mkdir(parents=True, exist_ok=True)
    with (
        patch("obsidian_vault_mcp.server.git_sync.is_dirty", return_value=True),
        patch("obsidian_vault_mcp.server.git_sync.commit") as mock_commit,
        patch("obsidian_vault_mcp.server.git_sync.push") as mock_push,
    ):
        result = server.vault_sync()
    mock_commit.assert_called_once()
    mock_push.assert_not_called()
    assert result == "committed (local only)"


def test_tool_vault_sync_clean_local(local_vault):
    local_vault.mkdir(parents=True, exist_ok=True)
    with (
        patch("obsidian_vault_mcp.server.git_sync.is_dirty", return_value=False),
        patch("obsidian_vault_mcp.server.git_sync.push") as mock_push,
    ):
        result = server.vault_sync()
    mock_push.assert_not_called()
    assert result == "nothing to commit or push"


def test_tool_vault_sync_custom_message(personal_vault):
    personal_vault.mkdir(parents=True, exist_ok=True)
    with (
        patch("obsidian_vault_mcp.server.git_sync.is_dirty", return_value=True),
        patch("obsidian_vault_mcp.server.git_sync.commit") as mock_commit,
        patch(
            "obsidian_vault_mcp.server.git_sync.pull_rebase",
            return_value=PullResult(conflict=False, files=[]),
        ),
        patch("obsidian_vault_mcp.server.git_sync.ahead_behind", return_value=(1, 0)),
        patch("obsidian_vault_mcp.server.git_sync.push"),
    ):
        server.vault_sync(message="my sync message")
    mock_commit.assert_called_once_with(personal_vault, "my sync message")


# --- 10.2 vault_sync pull-rebase ---


def test_vault_sync_pulls_before_push_remote(personal_vault):
    personal_vault.mkdir(parents=True, exist_ok=True)
    call_order = []

    def track_commit(*a, **k):
        call_order.append("commit")

    def track_pull(*a, **k):
        call_order.append("pull_rebase")
        return PullResult(conflict=False, files=[])

    def track_push(*a, **k):
        call_order.append("push")

    with (
        patch("obsidian_vault_mcp.server.git_sync.is_dirty", return_value=True),
        patch("obsidian_vault_mcp.server.git_sync.commit", side_effect=track_commit),
        patch("obsidian_vault_mcp.server.git_sync.pull_rebase", side_effect=track_pull),
        patch("obsidian_vault_mcp.server.git_sync.ahead_behind", return_value=(1, 0)),
        patch("obsidian_vault_mcp.server.git_sync.push", side_effect=track_push),
    ):
        server.vault_sync()
    assert call_order == ["commit", "pull_rebase", "push"]


def test_vault_sync_skips_pull_for_local(local_vault):
    local_vault.mkdir(parents=True, exist_ok=True)
    with (
        patch("obsidian_vault_mcp.server.git_sync.is_dirty", return_value=True),
        patch("obsidian_vault_mcp.server.git_sync.commit"),
        patch("obsidian_vault_mcp.server.git_sync.pull_rebase") as mock_pull,
    ):
        server.vault_sync()
    mock_pull.assert_not_called()


def test_vault_sync_rebase_conflict_aborts_and_reports(personal_vault):
    personal_vault.mkdir(parents=True, exist_ok=True)
    with (
        patch("obsidian_vault_mcp.server.git_sync.is_dirty", return_value=True),
        patch("obsidian_vault_mcp.server.git_sync.commit"),
        patch(
            "obsidian_vault_mcp.server.git_sync.pull_rebase",
            return_value=PullResult(conflict=True, files=["notes/foo.md", "AGENTS.md"]),
        ),
        patch("obsidian_vault_mcp.server.git_sync.push") as mock_push,
    ):
        result = server.vault_sync()
    mock_push.assert_not_called()
    assert "rebase conflict" in result
    assert "AGENTS.md" in result or "notes/foo.md" in result


def test_vault_sync_refreshes_conventions_when_agents_md_changed(personal_vault):
    personal_vault.mkdir(parents=True, exist_ok=True)
    (personal_vault / "AGENTS.md").write_text("new content from remote")
    conventions._cache["personal"] = "old cached content"
    with (
        patch("obsidian_vault_mcp.server.git_sync.is_dirty", return_value=False),
        patch(
            "obsidian_vault_mcp.server.git_sync.pull_rebase",
            return_value=PullResult(conflict=False, files=[]),
        ),
        patch("obsidian_vault_mcp.server.git_sync.ahead_behind", return_value=(0, 0)),
        patch("obsidian_vault_mcp.server.conventions.refresh") as mock_refresh,
    ):
        server.vault_sync()
    mock_refresh.assert_called_once_with("personal", personal_vault)


def test_vault_sync_no_refresh_when_agents_md_unchanged(personal_vault):
    personal_vault.mkdir(parents=True, exist_ok=True)
    (personal_vault / "AGENTS.md").write_text("same content")
    conventions._cache["personal"] = "same content"
    with (
        patch("obsidian_vault_mcp.server.git_sync.is_dirty", return_value=False),
        patch(
            "obsidian_vault_mcp.server.git_sync.pull_rebase",
            return_value=PullResult(conflict=False, files=[]),
        ),
        patch("obsidian_vault_mcp.server.git_sync.ahead_behind", return_value=(0, 0)),
        patch("obsidian_vault_mcp.server.conventions.refresh") as mock_refresh,
    ):
        server.vault_sync()
    mock_refresh.assert_not_called()


# --- 8.4 vault_conventions tool ---


def test_tool_vault_conventions_default_vault(personal_vault):
    personal_vault.mkdir(parents=True, exist_ok=True)
    conventions._cache["personal"] = "# Vault conventions"
    result = server.vault_conventions()
    assert "Vault conventions" in result


def test_tool_vault_conventions_explicit_vault(two_vaults):
    (two_vaults / "corporate").mkdir(parents=True, exist_ok=True)
    conventions._cache["corporate"] = "# Corporate rules"
    result = server.vault_conventions(vault="corporate")
    assert "Corporate rules" in result


def test_tool_vault_conventions_unknown_vault_returns_error(personal_vault):
    result = server.vault_conventions(vault="nonexistent")
    assert "error" in result.lower()


# --- 8.5 update_conventions tool ---


def test_tool_update_conventions_replaces_full_file(personal_vault):
    personal_vault.mkdir(parents=True, exist_ok=True)
    (personal_vault / "AGENTS.md").write_text("# Old content")
    conventions._cache["personal"] = "# Old content"
    with (
        patch("obsidian_vault_mcp.server.git_sync.commit"),
        patch(
            "obsidian_vault_mcp.server.git_sync.pull_rebase",
            return_value=PullResult(conflict=False, files=[]),
        ),
        patch("obsidian_vault_mcp.server.git_sync.push"),
    ):
        result = server.update_conventions(content="# New content")
    assert (personal_vault / "AGENTS.md").read_text() == "# New content"
    assert conventions._cache["personal"] == "# New content"
    assert "conventions updated" in result


def test_tool_update_conventions_replaces_section(personal_vault):
    personal_vault.mkdir(parents=True, exist_ok=True)
    original = "## Frontmatter\nold\n\n## Other\nother"
    (personal_vault / "AGENTS.md").write_text(original)
    conventions._cache["personal"] = original
    with (
        patch("obsidian_vault_mcp.server.git_sync.commit"),
        patch(
            "obsidian_vault_mcp.server.git_sync.pull_rebase",
            return_value=PullResult(conflict=False, files=[]),
        ),
        patch("obsidian_vault_mcp.server.git_sync.push"),
    ):
        server.update_conventions(content="new frontmatter", section="Frontmatter")
    updated = (personal_vault / "AGENTS.md").read_text()
    assert "new frontmatter" in updated
    assert "## Other" in updated
    assert "old" not in updated


def test_tool_update_conventions_missing_section_creates_it(personal_vault):
    personal_vault.mkdir(parents=True, exist_ok=True)
    original = "# Title\n## Existing\ncontent"
    (personal_vault / "AGENTS.md").write_text(original)
    conventions._cache["personal"] = original
    with (
        patch("obsidian_vault_mcp.server.git_sync.commit"),
        patch(
            "obsidian_vault_mcp.server.git_sync.pull_rebase",
            return_value=PullResult(conflict=False, files=[]),
        ),
        patch("obsidian_vault_mcp.server.git_sync.push"),
    ):
        server.update_conventions(content="brand new", section="NewSection")
    updated = (personal_vault / "AGENTS.md").read_text()
    assert "## NewSection" in updated
    assert "brand new" in updated
    assert "## Existing" in updated


def test_tool_update_conventions_refuses_other_paths(personal_vault):
    personal_vault.mkdir(parents=True, exist_ok=True)
    (personal_vault / "AGENTS.md").write_text("old")
    conventions._cache["personal"] = "old"
    with (
        patch("obsidian_vault_mcp.server.git_sync.commit"),
        patch(
            "obsidian_vault_mcp.server.git_sync.pull_rebase",
            return_value=PullResult(conflict=False, files=[]),
        ),
        patch("obsidian_vault_mcp.server.git_sync.push"),
    ):
        server.update_conventions(content="new")
    assert (personal_vault / "AGENTS.md").read_text() == "new"
    md_files = [f for f in personal_vault.glob("*.md") if f.name != "AGENTS.md"]
    assert md_files == []


def test_tool_update_conventions_pushes_immediately_remote(personal_vault):
    personal_vault.mkdir(parents=True, exist_ok=True)
    (personal_vault / "AGENTS.md").write_text("old")
    conventions._cache["personal"] = "old"
    call_order = []

    def track_commit(*a, **k):
        call_order.append("commit")

    def track_pull(*a, **k):
        call_order.append("pull")
        return PullResult(conflict=False, files=[])

    def track_push(*a, **k):
        call_order.append("push")

    with (
        patch("obsidian_vault_mcp.server.git_sync.commit", side_effect=track_commit),
        patch("obsidian_vault_mcp.server.git_sync.pull_rebase", side_effect=track_pull),
        patch("obsidian_vault_mcp.server.git_sync.push", side_effect=track_push),
    ):
        result = server.update_conventions(content="new")
    assert "commit" in call_order
    assert "pull" in call_order
    assert "push" in call_order
    assert (
        call_order.index("commit") < call_order.index("pull") < call_order.index("push")
    )
    assert "conventions updated" in result


def test_tool_update_conventions_skips_push_for_local(local_vault):
    local_vault.mkdir(parents=True, exist_ok=True)
    (local_vault / "AGENTS.md").write_text("old")
    conventions._cache["notes"] = "old"
    with (
        patch("obsidian_vault_mcp.server.git_sync.commit"),
        patch("obsidian_vault_mcp.server.git_sync.pull_rebase") as mock_pull,
        patch("obsidian_vault_mcp.server.git_sync.push") as mock_push,
    ):
        result = server.update_conventions(content="new", vault="notes")
    mock_pull.assert_not_called()
    mock_push.assert_not_called()
    assert "local only" in result


def test_tool_update_conventions_rebase_conflict_aborts(personal_vault):
    personal_vault.mkdir(parents=True, exist_ok=True)
    (personal_vault / "AGENTS.md").write_text("content")
    conventions._cache["personal"] = "content"
    with (
        patch("obsidian_vault_mcp.server.git_sync.commit"),
        patch(
            "obsidian_vault_mcp.server.git_sync.pull_rebase",
            return_value=PullResult(conflict=True, files=["AGENTS.md"]),
        ),
        patch("obsidian_vault_mcp.server.git_sync.push") as mock_push,
        patch("obsidian_vault_mcp.server.conventions.refresh") as mock_refresh,
    ):
        result = server.update_conventions(content="new")
    mock_push.assert_not_called()
    mock_refresh.assert_called_once()
    assert "conventions diverged" in result


def test_tool_update_conventions_cache_refreshed_after_success(personal_vault):
    personal_vault.mkdir(parents=True, exist_ok=True)
    (personal_vault / "AGENTS.md").write_text("old content")
    conventions._cache["personal"] = "old content"
    with (
        patch("obsidian_vault_mcp.server.git_sync.commit"),
        patch(
            "obsidian_vault_mcp.server.git_sync.pull_rebase",
            return_value=PullResult(conflict=False, files=[]),
        ),
        patch("obsidian_vault_mcp.server.git_sync.push"),
    ):
        server.update_conventions(content="pushed content")
    assert conventions._cache.get("personal") == "pushed content"


# --- 8.6.3 protected paths surface as MCP error responses ---


def test_tool_note_create_protected_returns_error(personal_vault):
    personal_vault.mkdir(parents=True, exist_ok=True)
    result = server.note_create(path="AGENTS.md", content="hack")
    assert "error" in result.lower() or "protected" in result.lower()


def test_tool_note_read_protected_returns_error(personal_vault):
    personal_vault.mkdir(parents=True, exist_ok=True)
    (personal_vault / "AGENTS.md").write_text("content")
    result = server.note_read(path="AGENTS.md")
    assert "error" in result.lower() or "protected" in result.lower()


def test_tool_note_update_protected_returns_error(personal_vault):
    personal_vault.mkdir(parents=True, exist_ok=True)
    result = server.note_update(path="AGENTS.md", content="hack")
    assert "error" in result.lower() or "protected" in result.lower()


def test_tool_note_delete_protected_returns_error(personal_vault):
    personal_vault.mkdir(parents=True, exist_ok=True)
    (personal_vault / "AGENTS.md").write_text("content")
    result = server.note_delete(path="AGENTS.md")
    assert "error" in result.lower() or "protected" in result.lower()


# --- 8.9 initialize.instructions ---


def test_initialize_instructions_contains_all_vault_conventions(tmp_path):
    conventions._cache["personal"] = "personal rules"
    conventions._cache["corporate"] = "corporate rules"
    config = _make_config(
        {
            "personal": "https://ghp_x@github.com/u/p.git",
            "corporate": "https://ghp_y@github.com/o/c.git",
        },
        default="personal",
    )
    server.setup(config, vaults_root=tmp_path)
    assert "## Vault: personal" in server.mcp.instructions
    assert "personal rules" in server.mcp.instructions
    assert "## Vault: corporate" in server.mcp.instructions
    assert "corporate rules" in server.mcp.instructions


def test_initialize_instructions_updated_after_update_conventions(tmp_path):
    (tmp_path / "personal").mkdir()
    (tmp_path / "personal" / "AGENTS.md").write_text("old instructions")
    conventions._cache["personal"] = "old instructions"
    config = _make_config({"personal": "https://ghp_x@github.com/u/p.git"})
    server.setup(config, vaults_root=tmp_path)
    assert "old instructions" in server.mcp.instructions

    with (
        patch("obsidian_vault_mcp.server.git_sync.commit"),
        patch(
            "obsidian_vault_mcp.server.git_sync.pull_rebase",
            return_value=PullResult(conflict=False, files=[]),
        ),
        patch("obsidian_vault_mcp.server.git_sync.push"),
    ):
        server.update_conventions(content="new instructions")
    assert "new instructions" in server.mcp.instructions


# --- 9.4 enforce_frontmatter wired through server ---


def test_server_passes_enforce_flag_to_vault(tmp_path):
    config = Config(
        vaults=[
            VaultConfig(
                name="personal", url="https://ghp_x@github.com/u/p.git", is_local=False
            )
        ],
        default_vault="personal",
        server=ServerConfig(port=8080, ip="0.0.0.0", enforce_frontmatter=False),
    )
    server.setup(config, vaults_root=tmp_path)
    (tmp_path / "personal").mkdir()
    server.note_create(path="note.md", content="body")
    content = (tmp_path / "personal" / "note.md").read_text()
    assert "title:" not in content
    assert "created:" not in content
