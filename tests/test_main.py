from unittest.mock import patch
from obsidian_vault_mcp.__main__ import main


# helpers — minimal env for a single local vault so load_config() succeeds
_ENV = {
    "VAULT_TEST_REPO": "local",
    "VAULT_DEFAULT": "test",
}


# --- 6.1 Transport flag ---


def test_transport_streamable_http(monkeypatch, tmp_path):
    for k, v in _ENV.items():
        monkeypatch.setenv(k, v)
    with (
        patch("obsidian_vault_mcp.__main__.git_sync.init_local_vault"),
        patch("obsidian_vault_mcp.__main__.conventions.load"),
        patch("obsidian_vault_mcp.__main__.server.setup"),
        patch("obsidian_vault_mcp.__main__.server.mcp.run") as mock_run,
    ):
        main(["--transport", "streamable-http"], vaults_root=tmp_path)
    mock_run.assert_called_once()
    assert (
        mock_run.call_args.kwargs.get("transport") == "streamable-http"
        or mock_run.call_args.args[0] == "streamable-http"
    )


def test_transport_stdio(monkeypatch, tmp_path):
    for k, v in _ENV.items():
        monkeypatch.setenv(k, v)
    with (
        patch("obsidian_vault_mcp.__main__.git_sync.init_local_vault"),
        patch("obsidian_vault_mcp.__main__.conventions.load"),
        patch("obsidian_vault_mcp.__main__.server.setup"),
        patch("obsidian_vault_mcp.__main__.server.mcp.run") as mock_run,
    ):
        main(["--transport", "stdio"], vaults_root=tmp_path)
    mock_run.assert_called_once()
    assert (
        mock_run.call_args.kwargs.get("transport") == "stdio"
        or mock_run.call_args.args[0] == "stdio"
    )


def test_transport_default_is_streamable_http(monkeypatch, tmp_path):
    for k, v in _ENV.items():
        monkeypatch.setenv(k, v)
    with (
        patch("obsidian_vault_mcp.__main__.git_sync.init_local_vault"),
        patch("obsidian_vault_mcp.__main__.conventions.load"),
        patch("obsidian_vault_mcp.__main__.server.setup"),
        patch("obsidian_vault_mcp.__main__.server.mcp.run") as mock_run,
    ):
        main([], vaults_root=tmp_path)
    transport = mock_run.call_args.kwargs.get("transport") or mock_run.call_args.args[0]
    assert transport == "streamable-http"


# --- 6.2 Server bind config ---


def test_port_from_env(monkeypatch, tmp_path):
    for k, v in _ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("SERVER_PORT", "9090")
    with (
        patch("obsidian_vault_mcp.__main__.git_sync.init_local_vault"),
        patch("obsidian_vault_mcp.__main__.conventions.load"),
        patch("obsidian_vault_mcp.__main__.server.mcp.run"),
    ):
        main([], vaults_root=tmp_path)
    from obsidian_vault_mcp import server

    assert server.mcp.settings.port == 9090


def test_ip_from_env(monkeypatch, tmp_path):
    for k, v in _ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("SERVER_IP", "127.0.0.1")
    with (
        patch("obsidian_vault_mcp.__main__.git_sync.init_local_vault"),
        patch("obsidian_vault_mcp.__main__.conventions.load"),
        patch("obsidian_vault_mcp.__main__.server.mcp.run"),
    ):
        main([], vaults_root=tmp_path)
    from obsidian_vault_mcp import server

    assert server.mcp.settings.host == "127.0.0.1"


# --- 6.3 Startup sequence ---


def test_vaults_initialised_before_server_starts(monkeypatch, tmp_path):
    for k, v in _ENV.items():
        monkeypatch.setenv(k, v)
    call_order = []
    with (
        patch(
            "obsidian_vault_mcp.__main__.git_sync.init_local_vault",
            side_effect=lambda *a, **k: call_order.append("init"),
        ),
        patch("obsidian_vault_mcp.__main__.conventions.load"),
        patch("obsidian_vault_mcp.__main__.server.setup"),
        patch(
            "obsidian_vault_mcp.__main__.server.mcp.run",
            side_effect=lambda *a, **k: call_order.append("run"),
        ),
    ):
        main([], vaults_root=tmp_path)
    assert call_order.index("init") < call_order.index("run")


def test_all_configured_vaults_initialised(monkeypatch, tmp_path):
    monkeypatch.setenv("VAULT_PERSONAL_REPO", "https://ghp_x@github.com/u/p.git")
    monkeypatch.setenv("VAULT_NOTES_REPO", "local")
    monkeypatch.setenv("VAULT_DEFAULT", "personal")
    with (
        patch("obsidian_vault_mcp.__main__.git_sync.init_vault") as mock_remote,
        patch("obsidian_vault_mcp.__main__.git_sync.init_local_vault") as mock_local,
        patch("obsidian_vault_mcp.__main__.conventions.load"),
        patch("obsidian_vault_mcp.__main__.server.setup"),
        patch("obsidian_vault_mcp.__main__.server.mcp.run"),
    ):
        main([], vaults_root=tmp_path)
    mock_remote.assert_called_once()
    mock_local.assert_called_once()


# --- 8.8 Startup seeding + cache priming ---


def test_startup_seeds_missing_agents_md(monkeypatch, tmp_path):
    for k, v in _ENV.items():
        monkeypatch.setenv(k, v)
    vault_path = tmp_path / "test"
    vault_path.mkdir()
    with (
        patch("obsidian_vault_mcp.__main__.git_sync.init_local_vault"),
        patch("obsidian_vault_mcp.git_sync.commit_file"),
        patch("obsidian_vault_mcp.__main__.server.mcp.run"),
    ):
        main([], vaults_root=tmp_path)
    assert (vault_path / "AGENTS.md").exists()


def test_startup_loads_conventions_for_each_vault(monkeypatch, tmp_path):
    monkeypatch.setenv("VAULT_PERSONAL_REPO", "https://ghp_x@github.com/u/p.git")
    monkeypatch.setenv("VAULT_NOTES_REPO", "local")
    monkeypatch.setenv("VAULT_DEFAULT", "personal")
    with (
        patch("obsidian_vault_mcp.__main__.git_sync.init_vault"),
        patch("obsidian_vault_mcp.__main__.git_sync.init_local_vault"),
        patch("obsidian_vault_mcp.__main__.conventions.load") as mock_load,
        patch("obsidian_vault_mcp.__main__.server.setup"),
        patch("obsidian_vault_mcp.__main__.server.mcp.run"),
    ):
        main([], vaults_root=tmp_path)
    assert mock_load.call_count == 2
