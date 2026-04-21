"""MCP server smoke tests.

We don't drive the stdio loop here — we just verify the server builds with the
expected tools registered.
"""

from __future__ import annotations

import pytest

from lore.mcp import build_server


@pytest.mark.anyio
async def test_build_server_registers_tools(tmp_path):
    db = tmp_path / "lore.db"
    server = build_server(db)
    tools = await server.list_tools()
    names = {t.name for t in tools}
    expected = {
        "lore_add_node",
        "lore_update_node",
        "lore_delete_node",
        "lore_get_node",
        "lore_add_edge",
        "lore_remove_edge",
        "lore_query",
        "lore_traverse",
        "lore_find_variants",
        "lore_list",
        "lore_audit",
        "lore_export_markdown",
    }
    assert expected <= names


@pytest.fixture
def anyio_backend():
    return "asyncio"
