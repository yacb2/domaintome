"""CLI smoke tests."""

from __future__ import annotations

from typer.testing import CliRunner

from lore.cli import app
from lore.graph import add_edge, add_node, open_db

runner = CliRunner()


def _seed(db_path):
    conn = open_db(db_path)
    add_node(conn, node_id="payments", type="module", title="Payments")
    add_node(conn, node_id="pay-cap", type="capability", title="Pay Cap")
    add_node(conn, node_id="pay-flow", type="flow", title="Pay Flow")
    add_edge(conn, from_id="pay-flow", to_id="pay-cap", relation="implements")
    add_edge(conn, from_id="pay-flow", to_id="payments", relation="part_of")
    add_edge(conn, from_id="pay-cap", to_id="payments", relation="part_of")
    conn.close()


def test_init_creates_db(tmp_path):
    db = tmp_path / "lore.db"
    result = runner.invoke(app, ["init", "--db", str(db)])
    assert result.exit_code == 0
    assert db.exists()


def test_init_fails_if_exists(tmp_path):
    db = tmp_path / "lore.db"
    runner.invoke(app, ["init", "--db", str(db)])
    result = runner.invoke(app, ["init", "--db", str(db)])
    assert result.exit_code == 1


def test_list_empty(tmp_path):
    db = tmp_path / "lore.db"
    open_db(db).close()
    result = runner.invoke(app, ["list", "--db", str(db)])
    assert result.exit_code == 0
    assert "(no nodes)" in result.output


def test_list_shows_nodes(tmp_path):
    db = tmp_path / "lore.db"
    _seed(db)
    result = runner.invoke(app, ["list", "--db", str(db)])
    assert "pay-flow" in result.output
    assert "payments" in result.output


def test_show_node(tmp_path):
    db = tmp_path / "lore.db"
    _seed(db)
    result = runner.invoke(app, ["show", "pay-flow", "--db", str(db)])
    assert result.exit_code == 0
    assert "Pay Flow" in result.output
    assert "implements" in result.output


def test_show_missing(tmp_path):
    db = tmp_path / "lore.db"
    open_db(db).close()
    result = runner.invoke(app, ["show", "ghost", "--db", str(db)])
    assert result.exit_code == 1


def test_query(tmp_path):
    db = tmp_path / "lore.db"
    _seed(db)
    result = runner.invoke(app, ["query", "Pay", "--db", str(db)])
    assert result.exit_code == 0
    assert "pay-flow" in result.output


def test_variants(tmp_path):
    db = tmp_path / "lore.db"
    _seed(db)
    result = runner.invoke(app, ["variants", "pay-cap", "--db", str(db)])
    assert result.exit_code == 0
    assert "pay-flow" in result.output


def test_audit_clean(tmp_path):
    db = tmp_path / "lore.db"
    _seed(db)
    result = runner.invoke(app, ["audit", "--db", str(db)])
    assert result.exit_code == 0
    assert "OK" in result.output


def test_export(tmp_path):
    db = tmp_path / "lore.db"
    _seed(db)
    out = tmp_path / "export"
    result = runner.invoke(app, ["export", "--db", str(db), "--out", str(out)])
    assert result.exit_code == 0
    assert (out / "flow" / "pay-flow.md").exists()
