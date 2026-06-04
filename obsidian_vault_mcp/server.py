from pathlib import Path

from mcp.server.fastmcp import FastMCP

from obsidian_vault_mcp import conventions, git_sync
from obsidian_vault_mcp.config import Config, VaultConfig
from obsidian_vault_mcp.vault import Vault

mcp = FastMCP("obsidian-vault-mcp")

_vaults: dict[str, Vault] = {}
_vault_configs: dict[str, VaultConfig] = {}
_default: str | None = None


def setup(config: Config, vaults_root: Path = Path("/vaults")) -> None:
    global _vaults, _vault_configs, _default
    _vaults = {}
    _vault_configs = {}
    _default = config.default_vault
    for vc in config.vaults:
        _vaults[vc.name] = Vault(
            vaults_root / vc.name,
            enforce_frontmatter=config.server.enforce_frontmatter,
        )
        _vault_configs[vc.name] = vc
    mcp.settings.host = config.server.ip
    mcp.settings.port = config.server.port
    _rebuild_instructions()


def _rebuild_instructions() -> None:
    sections = []
    for name in _vaults:
        try:
            content = conventions.get(name)
            sections.append(f"## Vault: {name}\n{content}")
        except KeyError:
            pass
    mcp._mcp_server.instructions = "\n\n".join(sections)


def _get_vault(name: str | None) -> Vault:
    vault_name = name or _default
    if vault_name not in _vaults:
        raise ValueError(f"Unknown vault: {vault_name!r}")
    return _vaults[vault_name]


@mcp.tool()
def vault_list() -> list[dict]:
    entries = []
    for name, vault in _vaults.items():
        vc = _vault_configs[name]
        entry: dict = {"name": name, "dirty": git_sync.is_dirty(vault.root)}
        if not vc.is_local:
            ahead, behind = git_sync.ahead_behind(vault.root)
            entry["ahead"] = ahead
            entry["behind"] = behind
        entries.append(entry)
    return entries


@mcp.tool()
def vault_conventions(vault: str | None = None) -> str:
    try:
        vault_name = vault or _default
        if vault_name not in _vaults:
            return f"error: unknown vault {vault_name!r}"
        return conventions.get(vault_name)
    except KeyError:
        return f"error: no conventions loaded for vault {vault_name!r}"


@mcp.tool()
def update_conventions(
    content: str,
    vault: str | None = None,
    section: str | None = None,
) -> str:
    try:
        vault_name = vault or _default
        vault_obj = _get_vault(vault_name)
        agents_md = vault_obj.root / "AGENTS.md"
        if section is not None:
            current = (
                agents_md.read_text(encoding="utf-8") if agents_md.exists() else ""
            )
            new_text = conventions.replace_section(current, section, content)
        else:
            new_text = content
        agents_md.write_text(new_text, encoding="utf-8")
        conventions.refresh(vault_name, vault_obj.root)
        git_sync.commit(vault_obj.root, "chore: update conventions")
        _rebuild_instructions()
        return "ok"
    except (ValueError, OSError) as e:
        return f"error: {e}"


@mcp.tool()
def note_create(
    path: str,
    content: str,
    vault: str | None = None,
    tags: list[str] | None = None,
) -> str:
    try:
        _get_vault(vault).note_create(path, content, tags=tags)
        return "ok"
    except PermissionError as e:
        return f"error: {e}"


@mcp.tool()
def note_read(path: str, vault: str | None = None) -> str:
    try:
        metadata, body = _get_vault(vault).note_read(path)
        return f"---\n{_format_metadata(metadata)}\n---\n{body}"
    except (FileNotFoundError, PermissionError) as e:
        return f"error: {e}"


@mcp.tool()
def note_update(
    path: str,
    vault: str | None = None,
    content: str | None = None,
    append: bool = False,
    tags: list[str] | None = None,
) -> str:
    try:
        _get_vault(vault).note_update(path, content=content, append=append, tags=tags)
        return "ok"
    except (ValueError, FileNotFoundError, PermissionError) as e:
        return f"error: {e}"


@mcp.tool()
def note_delete(path: str, vault: str | None = None) -> str:
    try:
        _get_vault(vault).note_delete(path)
        return "ok"
    except (FileNotFoundError, PermissionError) as e:
        return f"error: {e}"


@mcp.tool()
def note_list(vault: str | None = None, folder: str | None = None) -> str:
    entries = _get_vault(vault).note_list(folder=folder)
    return "\n".join(f"{e['path']} — {e['title']}" for e in entries)


@mcp.tool()
def note_search(
    query: str,
    vault: str | None = None,
    tags: list[str] | None = None,
    folder: str | None = None,
) -> str:
    entries = _get_vault(vault).note_search(query, tags=tags, folder=folder)
    return "\n".join(f"{e['path']} — {e['title']}" for e in entries)


@mcp.tool()
def vault_sync(vault: str | None = None, message: str | None = None) -> str:
    vault_name = vault or _default
    vc = _vault_configs[vault_name]
    path = _vaults[vault_name].root

    dirty = git_sync.is_dirty(path)
    if dirty:
        git_sync.commit(path, message)

    if vc.is_local:
        return "committed (local only)" if dirty else "nothing to commit or push"

    ahead, _ = git_sync.ahead_behind(path)
    if ahead > 0:
        git_sync.push(path)
        if dirty:
            return "committed and pushed"
        return f"nothing to commit, pushed {ahead} existing commit"
    return "nothing to commit or push"


def _format_metadata(metadata: dict) -> str:
    lines = []
    for key, value in metadata.items():
        if isinstance(value, list):
            if value:
                lines.append(f"{key}:")
                lines.extend(f"  - {v}" for v in value)
            else:
                lines.append(f"{key}: []")
        else:
            lines.append(f"{key}: {value}")
    return "\n".join(lines)
