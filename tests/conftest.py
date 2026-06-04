import pytest
from obsidian_vault_mcp import conventions


@pytest.fixture(autouse=True)
def clear_conventions_cache():
    conventions._cache.clear()
    yield
    conventions._cache.clear()
