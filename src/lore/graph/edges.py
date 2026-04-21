"""CRUD operations for graph edges."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any

from lore.graph.nodes import get_node
from lore.graph.schema import SchemaError, validate_edge_types


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    meta = d.pop("metadata_json", None)
    d["metadata"] = json.loads(meta) if meta else {}
    return d


def add_edge(
    conn: sqlite3.Connection,
    *,
    from_id: str,
    to_id: str,
    relation: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create an edge. Both nodes must exist and the relation must be allowed
    between their types."""
    from_node = get_node(conn, from_id)
    if from_node is None:
        raise SchemaError(f"Source node {from_id!r} not found")
    to_node = get_node(conn, to_id)
    if to_node is None:
        raise SchemaError(f"Target node {to_id!r} not found")

    validate_edge_types(relation, from_node["type"], to_node["type"])

    now = _now()
    meta_json = json.dumps(metadata) if metadata else None
    conn.execute(
        """
        INSERT INTO edges (from_id, to_id, relation, metadata_json, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (from_id, to_id, relation, meta_json, now),
    )
    conn.commit()
    return {
        "from_id": from_id,
        "to_id": to_id,
        "relation": relation,
        "metadata": metadata or {},
        "created_at": now,
    }


def remove_edge(
    conn: sqlite3.Connection,
    *,
    from_id: str,
    to_id: str,
    relation: str,
) -> bool:
    """Delete a specific edge. Returns True if a row was removed."""
    cur = conn.execute(
        "DELETE FROM edges WHERE from_id = ? AND to_id = ? AND relation = ?",
        (from_id, to_id, relation),
    )
    conn.commit()
    return cur.rowcount > 0


def list_edges(
    conn: sqlite3.Connection,
    *,
    from_id: str | None = None,
    to_id: str | None = None,
    relation: str | None = None,
) -> list[dict[str, Any]]:
    """List edges with optional filters."""
    clauses: list[str] = []
    values: list[Any] = []
    if from_id is not None:
        clauses.append("from_id = ?")
        values.append(from_id)
    if to_id is not None:
        clauses.append("to_id = ?")
        values.append(to_id)
    if relation is not None:
        clauses.append("relation = ?")
        values.append(relation)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = conn.execute(f"SELECT * FROM edges {where} ORDER BY created_at", values).fetchall()
    return [_row_to_dict(r) for r in rows]
