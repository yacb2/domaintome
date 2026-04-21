"""Node CRUD tests."""

from __future__ import annotations

import sqlite3

import pytest

from lore.graph import add_node, delete_node, get_node, update_node
from lore.graph.schema import SchemaError


def test_add_and_get_node(conn):
    node = add_node(
        conn,
        node_id="payments",
        type="module",
        title="Payments",
        body="The payments module.",
        metadata={"tags": ["billing"]},
    )
    assert node["id"] == "payments"
    assert node["type"] == "module"
    assert node["status"] == "active"
    assert node["metadata"] == {"tags": ["billing"]}

    fetched = get_node(conn, "payments")
    assert fetched == node


def test_add_duplicate_raises(conn):
    add_node(conn, node_id="payments", type="module", title="Payments")
    with pytest.raises(sqlite3.IntegrityError):
        add_node(conn, node_id="payments", type="module", title="Dup")


def test_add_rejects_invalid_id(conn):
    with pytest.raises(SchemaError):
        add_node(conn, node_id="Payments", type="module", title="Bad")


def test_add_rejects_invalid_type(conn):
    with pytest.raises(SchemaError):
        add_node(conn, node_id="x", type="service", title="x")


def test_add_rejects_empty_title(conn):
    with pytest.raises(SchemaError):
        add_node(conn, node_id="x", type="module", title="  ")


def test_update_node_fields(conn):
    add_node(conn, node_id="x", type="flow", title="Old")
    before = get_node(conn, "x")
    updated = update_node(conn, "x", title="New", status="deprecated")
    assert updated["title"] == "New"
    assert updated["status"] == "deprecated"
    assert updated["updated_at"] >= before["updated_at"]


def test_update_node_missing(conn):
    with pytest.raises(SchemaError):
        update_node(conn, "ghost", title="x")


def test_update_metadata_replaces(conn):
    add_node(conn, node_id="x", type="flow", title="X", metadata={"tags": ["a"]})
    updated = update_node(conn, "x", metadata={"tags": ["b"], "owner": "ayoel"})
    assert updated["metadata"] == {"tags": ["b"], "owner": "ayoel"}


def test_delete_node(conn):
    add_node(conn, node_id="x", type="flow", title="X")
    assert delete_node(conn, "x") is True
    assert get_node(conn, "x") is None
    assert delete_node(conn, "x") is False


def test_get_missing_returns_none(conn):
    assert get_node(conn, "ghost") is None
