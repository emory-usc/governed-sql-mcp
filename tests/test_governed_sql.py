"""Tests for Governor SQL MCP."""

import sqlite3

from governed_sql_mcp import db, query


def conn():
    c = db.connect(":memory:")
    db.seed(c)
    return c


def test_seed_is_deterministic():
    a = conn()
    b = conn()
    ra = a.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
    rb = b.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
    assert ra == rb == 24


def test_admin_sees_everything():
    c = conn()
    res = query.read_records(c, "v_customers", "admin")
    assert res["visible_count"] == res["total_count"] == 12
    assert res["withheld_count"] == 0


def test_manager_sees_subset():
    c = conn()
    res = query.read_records(c, "v_customers", "manager:mgr-01")
    assert 0 < res["visible_count"] < 12
    assert res["withheld_count"] == 12 - res["visible_count"]


def test_anonymous_fails_closed():
    c = conn()
    res = query.read_records(c, "v_customers", "anonymous")
    assert res["visible_count"] == 0
    assert res["withheld_count"] == 12


def test_account_number_not_published():
    c = conn()
    res = query.read_records(c, "v_accounts", "admin")
    for row in res["rows"]:
        assert "account_number" not in row


def test_aggregate_respects_scope():
    c = conn()
    admin = query.aggregate_records(c, "v_balances_by_region", "admin")
    anon = query.aggregate_records(c, "v_balances_by_region", "anonymous")
    assert admin["visible_count"] == 6
    assert anon["visible_count"] == 0


def test_read_only_surface_has_no_write():
    # There is no write verb: the module exposes only describe/read/aggregate.
    public = [n for n in dir(query) if not n.startswith("_")]
    assert "describe_entities" in public
    assert "read_records" in public
    assert "aggregate_records" in public
    for forbidden in ("insert", "update", "delete", "execute", "write"):
        assert not any(forbidden in n.lower() for n in public)
