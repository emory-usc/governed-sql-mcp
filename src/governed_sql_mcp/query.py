"""Read-only query layer with row-level security and account masking.

Exactly three verbs exist: describe, read, aggregate. There is no write path.
"""

from __future__ import annotations

import sqlite3

ENTITIES = {
    "v_customers": {"view": "v_customers", "rls_column": "manager_id"},
    "v_accounts": {"view": "v_accounts", "rls_column": None},
    "v_balances_by_region": {"view": "v_balances_by_region", "rls_column": None},
}

# account_number lives only in the base table; it is never published by a view.
# For masking we still expose a masked form on request, but read() never returns
# the raw value.
MASKED_COLUMNS = {"account_number"}


def _parse_claim(claim: str) -> tuple[str, str | None]:
    """Return (role, subject) from a claim string like 'manager:mgr-01'."""
    if not claim or claim == "anonymous":
        return "anonymous", None
    if claim == "admin":
        return "admin", None
    if claim.startswith("manager:"):
        return "manager", claim.split(":", 1)[1]
    return "anonymous", None


def _rls_predicate(entity: str, role: str, subject: str | None) -> str:
    """Fail-closed: unknown role -> 1=0 (sees nothing)."""
    if role == "admin":
        return "1=1"
    col = ENTITIES[entity]["rls_column"]
    if role == "manager" and col is not None and subject is not None:
        return f"{col} = ?"
    return "1=0"


def describe_entities(conn: sqlite3.Connection) -> list[dict]:
    out = []
    for name, meta in ENTITIES.items():
        cols = conn.execute(f"PRAGMA table_info({name})").fetchall()
        out.append(
            {
                "entity": name,
                "description": _description(name),
                "columns": [{"name": c["name"]} for c in cols],
            }
        )
    return out


def read_records(
    conn: sqlite3.Connection,
    entity: str,
    claim: str = "anonymous",
) -> dict:
    if entity not in ENTITIES:
        raise ValueError(f"unknown entity: {entity}")
    role, subject = _parse_claim(claim)
    predicate = _rls_predicate(entity, role, subject)
    view = ENTITIES[entity]["view"]

    total = conn.execute(f"SELECT COUNT(*) FROM {view}").fetchone()[0]
    params = (subject,) if "?" in predicate else ()
    if predicate == "1=0":
        rows: list[dict] = []
        visible = 0
    else:
        rows = [dict(r) for r in conn.execute(f"SELECT * FROM {view} WHERE {predicate}", params)]
        visible = len(rows)

    return {
        "entity": entity,
        "caller": claim,
        "visible_count": visible,
        "withheld_count": total - visible,
        "total_count": total,
        "rows": _mask(rows),
    }


def aggregate_records(
    conn: sqlite3.Connection,
    entity: str,
    claim: str = "anonymous",
) -> dict:
    if entity not in ENTITIES:
        raise ValueError(f"unknown entity: {entity}")
    role, subject = _parse_claim(claim)
    view = ENTITIES[entity]["view"]
    # Aggregates over customer-scoped data respect the same RLS contract.
    if role == "admin":
        rows = [dict(r) for r in conn.execute(f"SELECT * FROM {view} ORDER BY 1")]
        visible = len(rows)
        total = visible
    elif role == "manager" and subject is not None:
        rows = [
            dict(r)
            for r in conn.execute(
                f"""
                SELECT c.region AS region, SUM(a.balance) AS total_balance,
                       COUNT(a.id) AS account_count
                FROM accounts a JOIN customers c ON a.customer_id = c.id
                WHERE c.manager_id = ? GROUP BY c.region ORDER BY 1
                """,
                (subject,),
            )
        ]
        visible = len(rows)
        total = conn.execute("SELECT COUNT(DISTINCT region) FROM customers").fetchone()[0]
    else:
        rows, visible, total = [], 0, conn.execute(
            "SELECT COUNT(DISTINCT region) FROM customers"
        ).fetchone()[0]

    return {
        "entity": entity,
        "caller": claim,
        "visible_count": visible,
        "withheld_count": total - visible,
        "total_count": total,
        "rows": rows,
    }


def _mask(rows: list[dict]) -> list[dict]:
    for row in rows:
        for col in list(row.keys()):
            if col in MASKED_COLUMNS and row[col] is not None:
                row[col] = "****-" + str(row[col])[-4:]
    return rows


def _description(entity: str) -> str:
    return {
        "v_customers": "Customer records. account_number is never published.",
        "v_accounts": "Account records. account_number is never published.",
        "v_balances_by_region": "Total balance and account count by region.",
    }[entity]
