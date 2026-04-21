"""Query and traversal tests."""

from __future__ import annotations

from lore.graph import (
    add_edge,
    add_node,
    audit,
    find_variants,
    list_nodes,
    query,
    traverse,
)


def test_list_nodes_by_type(seeded_conn):
    flows = list_nodes(seeded_conn, type="flow")
    ids = {n["id"] for n in flows}
    assert ids == {"payment-by-transfer", "payment-by-tpv"}


def test_list_nodes_by_status(seeded_conn):
    actives = list_nodes(seeded_conn, status="active")
    assert len(actives) >= 1
    deprecated = list_nodes(seeded_conn, status="deprecated")
    assert deprecated == []


def test_list_nodes_by_tag(conn):
    add_node(conn, node_id="a", type="flow", title="A", metadata={"tags": ["billing"]})
    add_node(conn, node_id="b", type="flow", title="B", metadata={"tags": ["core"]})
    billing = list_nodes(conn, tag="billing")
    assert [n["id"] for n in billing] == ["a"]


def test_query_by_exact_id(seeded_conn):
    result = query(seeded_conn, "payment-by-transfer", depth=0)
    ids = {n["id"] for n in result["nodes"]}
    assert "payment-by-transfer" in ids
    # depth=0 means only the matched node, no neighborhood
    assert len(ids) == 1


def test_query_by_title_fuzzy(seeded_conn):
    result = query(seeded_conn, "transfer", depth=0)
    ids = {n["id"] for n in result["nodes"]}
    assert "payment-by-transfer" in ids


def test_query_with_depth_expands_neighborhood(seeded_conn):
    result = query(seeded_conn, "payment-by-transfer", depth=1)
    ids = {n["id"] for n in result["nodes"]}
    # At depth 1 should include payments (part_of), payment-registration
    # (implements), payment-recorded (triggers)
    assert "payments" in ids
    assert "payment-registration" in ids
    assert "payment-recorded" in ids
    # Edges within the returned set are included
    assert len(result["edges"]) >= 3


def test_find_variants(seeded_conn):
    variants = find_variants(seeded_conn, "payment-registration")
    ids = {n["id"] for n in variants}
    assert ids == {"payment-by-transfer", "payment-by-tpv"}


def test_traverse_follow_specific_relations(seeded_conn):
    result = traverse(
        seeded_conn,
        "payment-by-transfer",
        relations=["triggers"],
        max_depth=3,
    )
    ids = {n["id"] for n in result["nodes"]}
    assert ids == {"payment-by-transfer", "payment-recorded"}


def test_traverse_all_relations(seeded_conn):
    result = traverse(seeded_conn, "payment-by-transfer", max_depth=1)
    ids = {n["id"] for n in result["nodes"]}
    # Should reach payments, payment-registration, payment-recorded via outgoing
    assert "payments" in ids
    assert "payment-registration" in ids
    assert "payment-recorded" in ids


def test_traverse_unknown_start(conn):
    result = traverse(conn, "ghost")
    assert result == {"nodes": [], "edges": []}


def test_audit_finds_orphans(conn):
    add_node(conn, node_id="lonely", type="decision", title="Lonely decision")
    report = audit(conn)
    assert "lonely" in report["orphans"]


def test_audit_detects_generic_id(conn):
    add_node(conn, node_id="overview", type="module", title="Generic")
    report = audit(conn)
    assert "overview" in report["generic_ids"]


def test_audit_detects_supersedes_cycle(conn):
    add_node(conn, node_id="a", type="flow", title="A")
    add_node(conn, node_id="b", type="flow", title="B")
    add_edge(conn, from_id="a", to_id="b", relation="supersedes")
    add_edge(conn, from_id="b", to_id="a", relation="supersedes")
    report = audit(conn)
    assert report["cycles_supersedes"], "should detect cycle"
