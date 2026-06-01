from unittest.mock import patch
import pytest
from obsidian_vault_mcp.config import Config, VaultConfig, ServerConfig
from obsidian_vault_mcp import server


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
        patch("obsidian_vault_mcp.server.git_sync.ahead_behind", return_value=(1, 0)),
        patch("obsidian_vault_mcp.server.git_sync.push") as mock_push,
    ):
        result = server.vault_sync()
    mock_commit.assert_not_called()
    mock_push.assert_called_once()
    assert result == "nothing to commit, pushed 1 existing commit"


def test_tool_vault_sync_nothing_to_do_remote(personal_vault):
    personal_vault.mkdir(parents=True, exist_ok=True)
    with (
        patch("obsidian_vault_mcp.server.git_sync.is_dirty", return_value=False),
        patch("obsidian_vault_mcp.server.git_sync.commit") as mock_commit,
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
        patch("obsidian_vault_mcp.server.git_sync.ahead_behind", return_value=(1, 0)),
        patch("obsidian_vault_mcp.server.git_sync.push"),
    ):
        server.vault_sync(message="my sync message")
    mock_commit.assert_called_once_with(personal_vault, "my sync message")
