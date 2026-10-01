"""SQLite-backed store: connect, init schema/views, and deterministic seed."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = Path(__file__).resolve().parent.parent.parent / "sql" / "01_schema.sql"
VIEWS = Path(__file__).resolve().parent.parent.parent / "sql" / "02_views.sql"

# Deterministic synthetic book: 6 regions, 12 customers, 24 accounts.
REGIONS = ["north", "south", "east", "west", "central", "midwest"]
MANAGERS = ["mgr-01", "mgr-02"]


def connect(path: str = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA.read_text())
    conn.executescript(VIEWS.read_text())
    conn.commit()


def seed(conn: sqlite3.Connection) -> None:
    init(conn)
    customers = []
    accounts = []
    cust_idx = 0
    acct_idx = 0
    for ri, region in enumerate(REGIONS):
        manager = MANAGERS[ri % len(MANAGERS)]
        for local in range(2):  # two customers per region
            cust_idx += 1
            cid = f"cust-{cust_idx:03d}"
            name = f"Customer {cust_idx:03d}"
            customers.append((cid, name, region, manager))
            for k in range(2):  # two accounts per customer
                acct_idx += 1
                aid = f"acct-{acct_idx:06d}"
                balance = 10000 + (cust_idx * 733) % 90000
                account_number = f"{acct_idx:010d}"
                accounts.append(
                    (aid, cid, "savings" if k == 0 else "checking", float(balance), account_number)
                )
    conn.executemany(
        "INSERT INTO customers (id, name, region, manager_id) VALUES (?, ?, ?, ?)",
        customers,
    )
    conn.executemany(
        "INSERT INTO accounts (id, customer_id, account_type, balance, account_number) "
        "VALUES (?, ?, ?, ?, ?)",
        accounts,
    )
    conn.commit()
