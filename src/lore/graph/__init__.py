"""Lore graph engine — SQLite-backed typed graph of nodes and edges."""

from lore.graph.db import connect, init_db, open_db
from lore.graph.edges import add_edge, list_edges, remove_edge
from lore.graph.nodes import add_node, delete_node, get_node, update_node
from lore.graph.queries import audit, find_variants, list_nodes, query, traverse
from lore.graph.schema import (
    ALLOWED_RELATIONS,
    GENERIC_ID_WORDS,
    NODE_TYPES,
    RELATIONS,
    is_relation_allowed,
)

__all__ = [
    "ALLOWED_RELATIONS",
    "GENERIC_ID_WORDS",
    "NODE_TYPES",
    "RELATIONS",
    "add_edge",
    "add_node",
    "audit",
    "connect",
    "delete_node",
    "find_variants",
    "get_node",
    "init_db",
    "is_relation_allowed",
    "open_db",
    "list_edges",
    "list_nodes",
    "query",
    "remove_edge",
    "traverse",
    "update_node",
]
