"""Export the graph to one markdown file per node.

Output is regenerable; the canonical store remains SQLite. Markdown is meant
for PR review and portability.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from lore.graph.edges import list_edges
from lore.graph.queries import list_nodes


def _front_matter(node: dict, outgoing: list[dict]) -> str:
    lines = [
        "---",
        f"id: {node['id']}",
        f"type: {node['type']}",
        f'title: "{node["title"]}"',
        f"status: {node['status']}",
    ]
    # Group outgoing edges by relation
    grouped: dict[str, list[str]] = {}
    for e in outgoing:
        grouped.setdefault(e["relation"], []).append(e["to_id"])
    for relation in sorted(grouped):
        targets = ", ".join(grouped[relation])
        lines.append(f"{relation}: [{targets}]")
    if node.get("metadata"):
        tags = node["metadata"].get("tags")
        if tags:
            lines.append(f"tags: [{', '.join(tags)}]")
    lines.append("---")
    return "\n".join(lines)


def _render_node(node: dict, outgoing: list[dict]) -> str:
    fm = _front_matter(node, outgoing)
    body = node.get("body") or ""
    return f"{fm}\n\n# {node['title']}\n\n{body}".rstrip() + "\n"


def export_markdown(conn: sqlite3.Connection, out_dir: str | Path) -> list[Path]:
    """Write one `<type>/<id>.md` file per node. Returns the list of written
    paths."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for node in list_nodes(conn):
        outgoing = list_edges(conn, from_id=node["id"])
        type_dir = out / node["type"]
        type_dir.mkdir(exist_ok=True)
        path = type_dir / f"{node['id']}.md"
        path.write_text(_render_node(node, outgoing), encoding="utf-8")
        written.append(path)
    return written
