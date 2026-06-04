import pytest
from obsidian_vault_mcp.config import load_config


# --- 1.1 Vault discovery ---


def test_single_vault_parsed(monkeypatch):
    monkeypatch.setenv(
        "VAULT_PERSONAL_REPO", "https://ghp_xxx@github.com/user/personal.git"
    )
    monkeypatch.setenv("VAULT_DEFAULT", "personal")
    config = load_config()
    assert len(config.vaults) == 1
    assert config.vaults[0].name == "personal"
    assert config.vaults[0].url == "https://ghp_xxx@github.com/user/personal.git"


def test_multiple_vaults_parsed(monkeypatch):
    monkeypatch.setenv(
        "VAULT_PERSONAL_REPO", "https://ghp_xxx@github.com/user/personal.git"
    )
    monkeypatch.setenv(
        "VAULT_CORPORATE_REPO", "https://ghp_yyy@github.com/org/corporate.git"
    )
    monkeypatch.setenv("VAULT_DEFAULT", "personal")
    config = load_config()
    names = {v.name for v in config.vaults}
    assert names == {"personal", "corporate"}


def test_unrelated_env_vars_ignored(monkeypatch):
    monkeypatch.setenv(
        "VAULT_PERSONAL_REPO", "https://ghp_xxx@github.com/user/personal.git"
    )
    monkeypatch.setenv("VAULT_DEFAULT", "personal")
    monkeypatch.setenv("DATABASE_URL", "postgres://localhost/db")
    monkeypatch.setenv("PATH", "/usr/bin")
    config = load_config()
    assert len(config.vaults) == 1


def test_vault_name_lowercased(monkeypatch):
    monkeypatch.setenv(
        "VAULT_CORPORATE_REPO", "https://ghp_yyy@github.com/org/corporate.git"
    )
    monkeypatch.setenv("VAULT_DEFAULT", "corporate")
    config = load_config()
    assert config.vaults[0].name == "corporate"


# --- 1.2 Local vs remote detection ---


def test_local_vault_detected(monkeypatch):
    monkeypatch.setenv("VAULT_NOTES_REPO", "local")
    monkeypatch.setenv("VAULT_DEFAULT", "notes")
    config = load_config()
    assert config.vaults[0].is_local is True


def test_remote_vault_detected(monkeypatch):
    monkeypatch.setenv(
        "VAULT_PERSONAL_REPO", "https://ghp_xxx@github.com/user/personal.git"
    )
    monkeypatch.setenv("VAULT_DEFAULT", "personal")
    config = load_config()
    assert config.vaults[0].is_local is False


# --- 1.3 Default vault ---


def test_default_vault_set(monkeypatch):
    monkeypatch.setenv(
        "VAULT_PERSONAL_REPO", "https://ghp_xxx@github.com/user/personal.git"
    )
    monkeypatch.setenv(
        "VAULT_CORPORATE_REPO", "https://ghp_yyy@github.com/org/corporate.git"
    )
    monkeypatch.setenv("VAULT_DEFAULT", "personal")
    config = load_config()
    assert config.default_vault == "personal"


def test_default_vault_missing_raises(monkeypatch):
    monkeypatch.setenv(
        "VAULT_PERSONAL_REPO", "https://ghp_xxx@github.com/user/personal.git"
    )
    monkeypatch.setenv(
        "VAULT_CORPORATE_REPO", "https://ghp_yyy@github.com/org/corporate.git"
    )
    monkeypatch.delenv("VAULT_DEFAULT", raising=False)
    with pytest.raises(ValueError, match="VAULT_DEFAULT"):
        load_config()


def test_default_vault_implicit_single(monkeypatch):
    monkeypatch.setenv(
        "VAULT_PERSONAL_REPO", "https://ghp_xxx@github.com/user/personal.git"
    )
    monkeypatch.delenv("VAULT_DEFAULT", raising=False)
    config = load_config()
    assert config.default_vault == "personal"


# --- 1.4 Server config ---


def test_server_port_default(monkeypatch):
    monkeypatch.delenv("SERVER_PORT", raising=False)
    config = load_config()
    assert config.server.port == 8080


def test_server_port_override(monkeypatch):
    monkeypatch.setenv("SERVER_PORT", "9000")
    config = load_config()
    assert config.server.port == 9000


def test_server_ip_default(monkeypatch):
    monkeypatch.delenv("SERVER_IP", raising=False)
    config = load_config()
    assert config.server.ip == "0.0.0.0"


def test_server_ip_override(monkeypatch):
    monkeypatch.setenv("SERVER_IP", "127.0.0.1")
    config = load_config()
    assert config.server.ip == "127.0.0.1"


# --- 9.1 ENFORCE_FRONTMATTER flag ---


def test_enforce_frontmatter_default_true(monkeypatch):
    monkeypatch.delenv("ENFORCE_FRONTMATTER", raising=False)
    config = load_config()
    assert config.server.enforce_frontmatter is True


def test_enforce_frontmatter_false(monkeypatch):
    monkeypatch.setenv("ENFORCE_FRONTMATTER", "false")
    config = load_config()
    assert config.server.enforce_frontmatter is False


def test_enforce_frontmatter_true_explicit(monkeypatch):
    monkeypatch.setenv("ENFORCE_FRONTMATTER", "true")
    config = load_config()
    assert config.server.enforce_frontmatter is True


def test_enforce_frontmatter_case_insensitive(monkeypatch):
    for val in ("False", "FALSE", "0"):
        monkeypatch.setenv("ENFORCE_FRONTMATTER", val)
        assert load_config().server.enforce_frontmatter is False
    for val in ("True", "TRUE", "1"):
        monkeypatch.setenv("ENFORCE_FRONTMATTER", val)
        assert load_config().server.enforce_frontmatter is True
