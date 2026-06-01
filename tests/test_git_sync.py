from unittest.mock import patch, MagicMock
from obsidian_vault_mcp.git_sync import (
    init_vault,
    init_local_vault,
    commit,
    push,
    is_dirty,
    ahead_behind,
)


# --- 2.1 Remote vault initialisation ---


def test_clone_when_dir_missing(tmp_path):
    vault_path = tmp_path / "personal"
    url = "https://ghp_xxx@github.com/user/personal.git"
    with patch("obsidian_vault_mcp.git_sync.subprocess.run") as mock_run:
        init_vault(vault_path, url)
        mock_run.assert_called_once_with(
            ["git", "clone", "--", url, str(vault_path)],
            check=True,
        )


def test_pull_rebase_when_dir_exists(tmp_path):
    vault_path = tmp_path / "personal"
    vault_path.mkdir()
    url = "https://ghp_xxx@github.com/user/personal.git"
    with patch("obsidian_vault_mcp.git_sync.subprocess.run") as mock_run:
        init_vault(vault_path, url)
        mock_run.assert_called_once_with(
            ["git", "-C", str(vault_path), "pull", "--rebase"],
            check=True,
        )


# --- 2.2 Local vault initialisation ---


def test_git_init_when_dir_missing(tmp_path):
    vault_path = tmp_path / "notes"
    with patch("obsidian_vault_mcp.git_sync.subprocess.run") as mock_run:
        init_local_vault(vault_path)
        mock_run.assert_called_once_with(
            ["git", "init", str(vault_path)],
            check=True,
        )


def test_noop_when_local_dir_exists(tmp_path):
    vault_path = tmp_path / "notes"
    vault_path.mkdir()
    with patch("obsidian_vault_mcp.git_sync.subprocess.run") as mock_run:
        init_local_vault(vault_path)
        mock_run.assert_not_called()


# --- 2.3 Commit ---


def test_commit_stages_and_commits(tmp_path):
    with patch("obsidian_vault_mcp.git_sync.subprocess.run") as mock_run:
        commit(tmp_path, "my commit message")
        assert mock_run.call_count == 2
        mock_run.assert_any_call(
            ["git", "-C", str(tmp_path), "add", "-A"],
            check=True,
        )
        mock_run.assert_any_call(
            ["git", "-C", str(tmp_path), "commit", "-m", "my commit message"],
            check=True,
        )


def test_commit_default_message(tmp_path):
    with patch("obsidian_vault_mcp.git_sync.subprocess.run") as mock_run:
        commit(tmp_path)
        commit_call = [c for c in mock_run.call_args_list if "commit" in c.args[0]][0]
        message = commit_call.args[0][-1]
        assert isinstance(message, str) and len(message) > 0


# --- 2.4 Push ---


def test_push_calls_git_push(tmp_path):
    with patch("obsidian_vault_mcp.git_sync.subprocess.run") as mock_run:
        push(tmp_path)
        mock_run.assert_called_once_with(
            ["git", "-C", str(tmp_path), "push"],
            check=True,
        )


# --- 2.5 Dirty check ---


def test_is_dirty_true(tmp_path):
    mock_result = MagicMock()
    mock_result.stdout = " M somefile.md\n"
    with patch("obsidian_vault_mcp.git_sync.subprocess.run", return_value=mock_result):
        assert is_dirty(tmp_path) is True


def test_is_dirty_false(tmp_path):
    mock_result = MagicMock()
    mock_result.stdout = ""
    with patch("obsidian_vault_mcp.git_sync.subprocess.run", return_value=mock_result):
        assert is_dirty(tmp_path) is False


# --- 2.6 Ahead/behind counts ---


def test_ahead_behind_parsed(tmp_path):
    mock_result = MagicMock()
    mock_result.stdout = "2\t1\n"
    with patch("obsidian_vault_mcp.git_sync.subprocess.run", return_value=mock_result):
        result = ahead_behind(tmp_path)
        assert result == (2, 1)


def test_ahead_behind_zero(tmp_path):
    mock_result = MagicMock()
    mock_result.stdout = "0\t0\n"
    with patch("obsidian_vault_mcp.git_sync.subprocess.run", return_value=mock_result):
        result = ahead_behind(tmp_path)
        assert result == (0, 0)
