"""Lore MCP server — exposes the graph tools to LLM clients over stdio.

Each tool is a thin wrapper around `lore.graph`, sharing a single connection
for the lifetime of the process.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from lore.export import export_markdown as _export_markdown
from lore.graph import (
    add_edge as _add_edge,
)
from lore.graph import (
    add_node as _add_node,
)
from lore.graph import (
    audit as _audit,
)
from lore.graph import (
    delete_node as _delete_node,
)
from lore.graph import (
    find_variants as _find_variants,
)
from lore.graph import (
    get_node as _get_node,
)
from lore.graph import (
    list_edges as _list_edges,
)
from lore.graph import (
    list_nodes as _list_nodes,
)
from lore.graph import (
    open_db,
)
from lore.graph import (
    query as _query,
)
from lore.graph import (
    remove_edge as _remove_edge,
)
from lore.graph import (
    traverse as _traverse,
)
from lore.graph import (
    update_node as _update_node,
)


def build_server(db_path: str | Path) -> FastMCP:
    """Create a FastMCP server bound to the given database."""
    conn: sqlite3.Connection = open_db(db_path)
    mcp = FastMCP("lore")

    @mcp.tool()
    def lore_add_node(
        id: str,
        type: str,
        title: str,
        body: str | None = None,
        status: str = "active",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new node. Type must be one of: module, capability, flow,
        event, rule, form, entity, decision."""
        return _add_node(
            conn,
            node_id=id,
            type=type,
            title=title,
            body=body,
            status=status,
            metadata=metadata,
        )

    @mcp.tool()
    def lore_update_node(
        id: str,
        title: str | None = None,
        body: str | None = None,
        status: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Update fields on an existing node. Pass only the fields you want
        changed. Passing metadata replaces the entire metadata dict."""
        return _update_node(
            conn,
            id,
            title=title,
            body=body,
            status=status,
            metadata=metadata,
        )

    @mcp.tool()
    def lore_delete_node(id: str) -> dict[str, bool]:
        """Delete a node and all its edges."""
        return {"deleted": _delete_node(conn, id)}

    @mcp.tool()
    def lore_get_node(id: str, include_edges: bool = True) -> dict[str, Any]:
        """Fetch a node by id, optionally with its direct edges."""
        node = _get_node(conn, id)
        if node is None:
            return {"error": f"Node {id!r} not found"}
        result: dict[str, Any] = {"node": node}
        if include_edges:
            result["outgoing"] = _list_edges(conn, from_id=id)
            result["incoming"] = _list_edges(conn, to_id=id)
        return result

    @mcp.tool()
    def lore_add_edge(
        from_id: str,
        to_id: str,
        relation: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create an edge between two existing nodes. The relation must be
        valid for the node types (see PRD §4.4)."""
        return _add_edge(
            conn,
            from_id=from_id,
            to_id=to_id,
            relation=relation,
            metadata=metadata,
        )

    @mcp.tool()
    def lore_remove_edge(
        from_id: str, to_id: str, relation: str
    ) -> dict[str, bool]:
        """Remove a specific edge."""
        return {
            "removed": _remove_edge(
                conn, from_id=from_id, to_id=to_id, relation=relation
            )
        }

    @mcp.tool()
    def lore_query(text_or_id: str, depth: int = 1) -> dict[str, Any]:
        """Flexible search. Tries exact id, then title substring, then tag.
        Returns matched nodes plus their neighborhood up to `depth`."""
        return _query(conn, text_or_id, depth=depth)

    @mcp.tool()
    def lore_traverse(
        from_id: str,
        relations: list[str] | None = None,
        max_depth: int = 3,
    ) -> dict[str, Any]:
        """Walk the graph from a node, following only the listed relations
        (or all of them if None)."""
        return _traverse(
            conn, from_id, relations=relations, max_depth=max_depth
        )

    @mcp.tool()
    def lore_find_variants(capability_id: str) -> list[dict[str, Any]]:
        """List all flows that implement the given capability — answers
        'how many ways of doing X?'."""
        return _find_variants(conn, capability_id)

    @mcp.tool()
    def lore_list(
        type: str | None = None,
        status: str | None = None,
        tag: str | None = None,
    ) -> list[dict[str, Any]]:
        """List nodes, optionally filtered by type, status or tag."""
        return _list_nodes(conn, type=type, status=status, tag=tag)

    @mcp.tool()
    def lore_audit() -> dict[str, Any]:
        """Run structural checks: orphans, dangling edges, id hygiene, cycles."""
        return _audit(conn)

    @mcp.tool()
    def lore_export_markdown(out_dir: str) -> dict[str, Any]:
        """Export the graph as one markdown file per node."""
        written = _export_markdown(conn, out_dir)
        return {"count": len(written), "out_dir": str(out_dir)}

    return mcp


def run(db_path: str | Path) -> None:
    """Run the MCP server over stdio."""
    mcp = build_server(db_path)
    mcp.run()
