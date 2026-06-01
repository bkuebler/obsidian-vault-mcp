import os
from dataclasses import dataclass


@dataclass
class VaultConfig:
    name: str
    url: str
    is_local: bool


@dataclass
class ServerConfig:
    port: int
    ip: str


@dataclass
class Config:
    vaults: list[VaultConfig]
    default_vault: str | None
    server: ServerConfig


def load_config() -> Config:
    vaults = []
    for key, value in os.environ.items():
        if key.startswith("VAULT_") and key.endswith("_REPO"):
            name = key[len("VAULT_") : -len("_REPO")].lower()
            vaults.append(
                VaultConfig(
                    name=name,
                    url=value,
                    is_local=(value == "local"),
                )
            )

    default = os.environ.get("VAULT_DEFAULT")
    if default is None:
        if len(vaults) == 1:
            default = vaults[0].name
        elif len(vaults) > 1:
            raise ValueError(
                "VAULT_DEFAULT must be set when multiple vaults are configured"
            )

    server = ServerConfig(
        port=int(os.environ.get("SERVER_PORT", 8080)),
        ip=os.environ.get("SERVER_IP", "0.0.0.0"),
    )

    return Config(vaults=vaults, default_vault=default, server=server)
