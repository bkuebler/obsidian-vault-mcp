import re
from importlib.resources import files
from pathlib import Path

from obsidian_vault_mcp import git_sync

_cache: dict[str, str] = {}


def load(vault_name: str, vault_path: Path) -> str:
    agents_md = vault_path / "AGENTS.md"
    if not agents_md.exists():
        default_content = (
            files("obsidian_vault_mcp")
            .joinpath("default_AGENTS.md")
            .read_text(encoding="utf-8")
        )
        agents_md.write_text(default_content, encoding="utf-8")
        git_sync.commit_file(vault_path, "AGENTS.md", "chore: seed AGENTS.md")
    content = agents_md.read_text(encoding="utf-8")
    _cache[vault_name] = content
    return content


def get(vault_name: str) -> str:
    return _cache[vault_name]


def refresh(vault_name: str, vault_path: Path) -> str:
    content = (vault_path / "AGENTS.md").read_text(encoding="utf-8")
    _cache[vault_name] = content
    return content


def replace_section(text: str, section: str, new_content: str) -> str:
    heading = f"## {section}"
    parts = re.split(r"(^## .+$)", text, flags=re.MULTILINE)
    for i in range(1, len(parts), 2):
        if parts[i].rstrip() == heading:
            parts[i + 1] = "\n" + new_content.rstrip() + "\n"
            return "".join(parts)
    return text.rstrip("\n") + f"\n\n{heading}\n{new_content.rstrip()}\n"
