"""
Contract tests against the MCP SDK's public API.
These catch breaking changes in SDK upgrades and API mismatches we'd otherwise
only discover at runtime (as happened with FastMCP.run() host/port kwargs).
"""

import inspect
from mcp.server.fastmcp import FastMCP


def test_fastmcp_run_accepts_transport():
    sig = inspect.signature(FastMCP.run)
    sig.bind_partial(transport="streamable-http")


def test_fastmcp_run_does_not_accept_host_or_port():
    sig = inspect.signature(FastMCP.run)
    params = sig.parameters
    assert "host" not in params, "host moved into run() — update __main__.py"
    assert "port" not in params, "port moved into run() — update __main__.py"


def test_fastmcp_settings_has_host_and_port():
    instance = FastMCP("test")
    assert hasattr(instance.settings, "host"), "host not found on mcp.settings"
    assert hasattr(instance.settings, "port"), "port not found on mcp.settings"


def test_fastmcp_settings_host_is_writable():
    instance = FastMCP("test")
    instance.settings.host = "127.0.0.1"
    assert instance.settings.host == "127.0.0.1"


def test_fastmcp_settings_port_is_writable():
    instance = FastMCP("test")
    instance.settings.port = 9090
    assert instance.settings.port == 9090


def test_fastmcp_init_accepts_host_and_port():
    sig = inspect.signature(FastMCP.__init__)
    params = sig.parameters
    assert "host" in params, "host removed from FastMCP.__init__ — review server.py"
    assert "port" in params, "port removed from FastMCP.__init__ — review server.py"
