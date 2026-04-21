"""Higher-level queries over the graph: search, traversal, audit."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from lore.graph.nodes import _row_to_dict as _node_row_to_dict
from lore.graph.nodes import get_node
from lore.graph.schema import GENERIC_ID_WORDS, NODE_TYPES, is_valid_id


def _edge_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    meta = d.pop("metadata_json", None)
    d["metadata"] = json.loads(meta) if meta else {}
    return d


def list_nodes(
    conn: sqlite3.Connection,
    *,
    type: str | None = None,
    status: str | None = None,
    tag: str | None = None,
) -> list[dict[str, Any]]:
    """List nodes filtered by type, status, and/or a tag in metadata.tags."""
    clauses: list[str] = []
    values: list[Any] = []
    if type is not None:
        clauses.append("type = ?")
        values.append(type)
    if status is not None:
        clauses.append("status = ?")
        values.append(status)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = conn.execute(
        f"SELECT * FROM nodes {where} ORDER BY type, id", values
    ).fetchall()
    nodes = [_node_row_to_dict(r) for r in rows]
    if tag is not None:
        nodes = [n for n in nodes if tag in n.get("metadata", {}).get("tags", [])]
    return nodes


def query(
    conn: sqlite3.Connection,
    text_or_id: str,
    *,
    depth: int = 1,
) -> dict[str, Any]:
    """Flexible search.

    Resolution order:
    1. Exact id match.
    2. Case-insensitive substring match on title.
    3. Tag match (metadata.tags contains text_or_id).

    Returns a dict with `nodes` (matched nodes + neighborhood up to `depth`) and
    `edges` (all edges within the returned node set).
    """
    matched = _resolve_query(conn, text_or_id)
    seen_ids: set[str] = {n["id"] for n in matched}
    frontier = list(seen_ids)
    all_nodes = {n["id"]: n for n in matched}

    for _ in range(max(depth, 0)):
        if not frontier:
            break
        placeholders = ",".join("?" * len(frontier))
        rows = conn.execute(
            f"""
            SELECT * FROM nodes WHERE id IN (
                SELECT to_id FROM edges WHERE from_id IN ({placeholders})
                UNION
                SELECT from_id FROM edges WHERE to_id IN ({placeholders})
            )
            """,
            frontier + frontier,
        ).fetchall()
        next_frontier: list[str] = []
        for r in rows:
            node = _node_row_to_dict(r)
            if node["id"] not in seen_ids:
                seen_ids.add(node["id"])
                all_nodes[node["id"]] = node
                next_frontier.append(node["id"])
        frontier = next_frontier

    edges = _edges_within(conn, seen_ids)
    return {
        "nodes": sorted(all_nodes.values(), key=lambda n: (n["type"], n["id"])),
        "edges": edges,
    }


def _resolve_query(conn: sqlite3.Connection, text: str) -> list[dict[str, Any]]:
    exact = get_node(conn, text)
    if exact:
        return [exact]
    like = f"%{text}%"
    rows = conn.execute(
        "SELECT * FROM nodes WHERE LOWER(title) LIKE LOWER(?) ORDER BY type, id",
        (like,),
    ).fetchall()
    if rows:
        return [_node_row_to_dict(r) for r in rows]
    # Tag fallback
    all_nodes = conn.execute("SELECT * FROM nodes").fetchall()
    matches: list[dict[str, Any]] = []
    for r in all_nodes:
        node = _node_row_to_dict(r)
        if text in node.get("metadata", {}).get("tags", []):
            matches.append(node)
    return matches


def _edges_within(
    conn: sqlite3.Connection, node_ids: set[str]
) -> list[dict[str, Any]]:
    if not node_ids:
        return []
    placeholders = ",".join("?" * len(node_ids))
    ids = list(node_ids)
    rows = conn.execute(
        f"""
        SELECT * FROM edges
        WHERE from_id IN ({placeholders}) AND to_id IN ({placeholders})
        ORDER BY relation, from_id, to_id
        """,
        ids + ids,
    ).fetchall()
    return [_edge_row_to_dict(r) for r in rows]


def traverse(
    conn: sqlite3.Connection,
    from_id: str,
    *,
    relations: list[str] | None = None,
    max_depth: int = 3,
) -> dict[str, Any]:
    """Walk the graph from `from_id` following edges whose relation is in
    `relations` (or any relation if None). Returns nodes and edges reached,
    including the starting node."""
    start = get_node(conn, from_id)
    if start is None:
        return {"nodes": [], "edges": []}

    seen_ids: set[str] = {from_id}
    all_nodes: dict[str, dict[str, Any]] = {from_id: start}
    collected_edges: list[dict[str, Any]] = []
    frontier = [from_id]

    for _ in range(max(max_depth, 0)):
        if not frontier:
            break
        placeholders = ",".join("?" * len(frontier))
        edge_sql = f"SELECT * FROM edges WHERE from_id IN ({placeholders})"
        params: list[Any] = list(frontier)
        if relations:
            rel_placeholders = ",".join("?" * len(relations))
            edge_sql += f" AND relation IN ({rel_placeholders})"
            params.extend(relations)
        edge_rows = conn.execute(edge_sql, params).fetchall()

        next_frontier: list[str] = []
        for e in edge_rows:
            edge = _edge_row_to_dict(e)
            collected_edges.append(edge)
            if edge["to_id"] not in seen_ids:
                seen_ids.add(edge["to_id"])
                node = get_node(conn, edge["to_id"])
                if node:
                    all_nodes[edge["to_id"]] = node
                    next_frontier.append(edge["to_id"])
        frontier = next_frontier

    return {
        "nodes": sorted(all_nodes.values(), key=lambda n: (n["type"], n["id"])),
        "edges": collected_edges,
    }


def find_variants(
    conn: sqlite3.Connection, capability_id: str
) -> list[dict[str, Any]]:
    """Return all flows that `implements` the given capability."""
    rows = conn.execute(
        """
        SELECT n.* FROM nodes n
        JOIN edges e ON e.from_id = n.id
        WHERE e.relation = 'implements' AND e.to_id = ?
        ORDER BY n.id
        """,
        (capability_id,),
    ).fetchall()
    return [_node_row_to_dict(r) for r in rows]


def audit(conn: sqlite3.Connection) -> dict[str, Any]:
    """Run structural checks against the graph.

    Returns a dict with lists: `orphans`, `dangling_edges`, `invalid_ids`,
    `generic_ids`, `unknown_types`, `cycles_supersedes`.
    """
    findings: dict[str, list[Any]] = {
        "orphans": [],
        "dangling_edges": [],
        "invalid_ids": [],
        "generic_ids": [],
        "unknown_types": [],
        "cycles_supersedes": [],
    }

    all_nodes = conn.execute("SELECT id, type FROM nodes").fetchall()
    node_ids = {r["id"] for r in all_nodes}

    # Orphans: no incoming and no outgoing edges.
    for r in all_nodes:
        nid = r["id"]
        has_edge = conn.execute(
            "SELECT 1 FROM edges WHERE from_id = ? OR to_id = ? LIMIT 1",
            (nid, nid),
        ).fetchone()
        if not has_edge:
            findings["orphans"].append(nid)

    # Dangling edges: FK should prevent this, but scan defensively.
    for r in conn.execute("SELECT from_id, to_id, relation FROM edges").fetchall():
        if r["from_id"] not in node_ids or r["to_id"] not in node_ids:
            findings["dangling_edges"].append(dict(r))

    # ID hygiene.
    for r in all_nodes:
        nid = r["id"]
        if not is_valid_id(nid):
            findings["invalid_ids"].append(nid)
        if nid in GENERIC_ID_WORDS:
            findings["generic_ids"].append(nid)
        if r["type"] not in NODE_TYPES:
            findings["unknown_types"].append({"id": nid, "type": r["type"]})

    # Cycles in supersedes (a supersedes-chain forming a loop is illegal).
    findings["cycles_supersedes"] = _find_supersedes_cycles(conn)

    return findings


def _find_supersedes_cycles(conn: sqlite3.Connection) -> list[list[str]]:
    edges = conn.execute(
        "SELECT from_id, to_id FROM edges WHERE relation = 'supersedes'"
    ).fetchall()
    graph: dict[str, list[str]] = {}
    for e in edges:
        graph.setdefault(e["from_id"], []).append(e["to_id"])

    cycles: list[list[str]] = []
    visited: set[str] = set()

    def dfs(node: str, stack: list[str]) -> None:
        if node in stack:
            cycles.append(stack[stack.index(node):] + [node])
            return
        if node in visited:
            return
        visited.add(node)
        stack.append(node)
        for nxt in graph.get(node, []):
            dfs(nxt, stack)
        stack.pop()

    for start in list(graph.keys()):
        dfs(start, [])

    return cycles
