from unittest.mock import patch
import pytest
from obsidian_vault_mcp import conventions


# --- 8.2 conventions.load ---


def test_load_returns_existing_agents_md(tmp_path):
    (tmp_path / "AGENTS.md").write_text("# My conventions", encoding="utf-8")
    with patch("obsidian_vault_mcp.conventions.git_sync"):
        result = conventions.load("myvault", tmp_path)
    assert result == "# My conventions"


def test_load_seeds_default_when_missing(tmp_path):
    with patch("obsidian_vault_mcp.conventions.git_sync"):
        result = conventions.load("myvault", tmp_path)
    assert (tmp_path / "AGENTS.md").exists()
    assert len(result) > 0


def test_seeded_file_is_committed(tmp_path):
    with patch("obsidian_vault_mcp.conventions.git_sync.commit_file") as mock_commit:
        conventions.load("myvault", tmp_path)
    mock_commit.assert_called_once_with(tmp_path, "AGENTS.md", "chore: seed AGENTS.md")


def test_seeded_content_matches_default_template(tmp_path):
    with patch("obsidian_vault_mcp.conventions.git_sync"):
        conventions.load("myvault", tmp_path)
    content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "Vault Conventions" in content


def test_no_commit_when_agents_md_exists(tmp_path):
    (tmp_path / "AGENTS.md").write_text("# existing", encoding="utf-8")
    with patch("obsidian_vault_mcp.conventions.git_sync.commit_file") as mock_commit:
        conventions.load("myvault", tmp_path)
    mock_commit.assert_not_called()


# --- 8.3 cache ---


def test_cache_returns_same_content_on_repeated_calls(tmp_path):
    (tmp_path / "AGENTS.md").write_text("cached content", encoding="utf-8")
    with patch("obsidian_vault_mcp.conventions.git_sync"):
        conventions.load("myvault", tmp_path)
    result = conventions.get("myvault")
    assert result == "cached content"


def test_refresh_rereads_from_disk(tmp_path):
    agents_md = tmp_path / "AGENTS.md"
    agents_md.write_text("original", encoding="utf-8")
    with patch("obsidian_vault_mcp.conventions.git_sync"):
        conventions.load("myvault", tmp_path)
    agents_md.write_text("updated", encoding="utf-8")
    conventions.refresh("myvault", tmp_path)
    assert conventions.get("myvault") == "updated"


def test_per_vault_cache_isolation(tmp_path):
    v1 = tmp_path / "v1"
    v2 = tmp_path / "v2"
    v1.mkdir()
    v2.mkdir()
    (v1 / "AGENTS.md").write_text("vault1 content", encoding="utf-8")
    (v2 / "AGENTS.md").write_text("vault2 content", encoding="utf-8")
    with patch("obsidian_vault_mcp.conventions.git_sync"):
        conventions.load("vault1", v1)
        conventions.load("vault2", v2)
    assert conventions.get("vault1") == "vault1 content"
    assert conventions.get("vault2") == "vault2 content"


def test_get_raises_for_uncached_vault():
    with pytest.raises(KeyError):
        conventions.get("never_loaded")


# --- replace_section ---


def test_replace_section_replaces_existing():
    text = "## Frontmatter\nold content\n\n## Other\nother stuff"
    result = conventions.replace_section(text, "Frontmatter", "new content")
    assert "new content" in result
    assert "old content" not in result
    assert "## Other" in result
    assert "other stuff" in result


def test_replace_section_appends_when_missing():
    text = "## Existing\nsome content"
    result = conventions.replace_section(text, "NewSection", "brand new")
    assert "## NewSection" in result
    assert "brand new" in result
    assert "## Existing" in result
    assert "some content" in result
