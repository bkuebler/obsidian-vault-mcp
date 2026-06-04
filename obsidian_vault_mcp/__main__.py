import argparse
import subprocess
from pathlib import Path

from obsidian_vault_mcp import conventions, git_sync, server
from obsidian_vault_mcp.config import load_config


def main(args: list[str] | None = None, vaults_root: Path = Path("/vaults")) -> None:
    parser = argparse.ArgumentParser(prog="obsidian-vault-mcp")
    parser.add_argument(
        "--transport",
        default="streamable-http",
        choices=["streamable-http", "stdio"],
    )
    parsed = parser.parse_args(args)

    config = load_config()

    for vc in config.vaults:
        vault_path = vaults_root / vc.name
        if vc.is_local:
            git_sync.init_local_vault(vault_path)
        else:
            git_sync.init_vault(vault_path, vc.url)
        was_missing = not (vault_path / "AGENTS.md").exists()
        conventions.load(vc.name, vault_path)
        was_seeded = was_missing and (vault_path / "AGENTS.md").exists()
        if was_seeded and not vc.is_local:
            try:
                git_sync.push(vault_path)
            except subprocess.CalledProcessError:
                git_sync.reset_hard(vault_path)
                conventions.refresh(vc.name, vault_path)

    server.setup(config, vaults_root=vaults_root)

    server.mcp.run(transport=parsed.transport)


if __name__ == "__main__":
    main()
