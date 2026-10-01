"""CLI for governed-sql-mcp: seed, verify, describe, read, aggregate."""

from __future__ import annotations

import argparse
import sys

from . import db
from . import query


def cmd_seed(conn) -> None:
    db.seed(conn)
    print("seeded deterministic book (6 regions, 12 customers, 24 accounts)")


def cmd_verify(conn) -> None:
    db.seed(conn)
    total_customers = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    total_accounts = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]

    admin = query.read_records(conn, "v_customers", "admin")
    mgr = query.read_records(conn, "v_customers", "manager:mgr-01")
    anon = query.read_records(conn, "v_customers", "anonymous")

    print(f"customers: {total_customers}  accounts: {total_accounts}")
    print(f"v_customers as admin:   {admin['visible_count']} visible / {admin['withheld_count']} withheld")
    print(f"v_customers as mgr-01:  {mgr['visible_count']} visible / {mgr['withheld_count']} withheld")
    print(f"v_customers as anon:    {anon['visible_count']} visible / {anon['withheld_count']} withheld")

    # fail-closed assertions
    assert anon["visible_count"] == 0, "anonymous must see zero rows"
    assert admin["visible_count"] == total_customers, "admin must see all rows"
    assert 0 < mgr["visible_count"] < total_customers, "manager must see a strict subset"
    print("row-level security: OK (fail-closed verified)")


def cmd_describe(conn) -> None:
    db.seed(conn)
    for e in query.describe_entities(conn):
        cols = ", ".join(c["name"] for c in e["columns"])
        print(f"{e['entity']}: {e['description']}")
        print(f"   columns: {cols}")


def cmd_read(conn, entity: str, claim: str) -> None:
    db.seed(conn)
    res = query.read_records(conn, entity, claim)
    print(
        f"{entity} as {claim}: {res['visible_count']} visible / "
        f"{res['withheld_count']} withheld of {res['total_count']}"
    )
    for row in res["rows"][:10]:
        print("   ", dict(row))


def cmd_aggregate(conn, entity: str, claim: str) -> None:
    db.seed(conn)
    res = query.aggregate_records(conn, entity, claim)
    print(
        f"{entity} as {claim}: {res['visible_count']} visible / "
        f"{res['withheld_count']} withheld of {res['total_count']}"
    )
    for row in res["rows"]:
        print("   ", dict(row))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="governed-sql")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("seed")
    sub.add_parser("verify")
    sub.add_parser("describe")

    run = sub.add_parser("run")
    run.add_argument(
        "--transport",
        default="streamable-http",
        choices=["streamable-http", "stdio"],
        help="MCP transport",
    )
    run.add_argument("--host", default="127.0.0.1", help="bind address (http transport)")
    run.add_argument("--port", type=int, default=8000, help="bind port (http transport)")

    r = sub.add_parser("read")
    r.add_argument("entity")
    r.add_argument("--as", dest="claim", default="anonymous")

    a = sub.add_parser("aggregate")
    a.add_argument("entity")
    a.add_argument("--as", dest="claim", default="anonymous")

    args = p.parse_args(argv)
    conn = db.connect(":memory:")
    try:
        if args.cmd == "seed":
            cmd_seed(conn)
        elif args.cmd == "run":
            conn.close()
            from governed_sql_mcp.server import create_mcp

            mcp = create_mcp()
            mcp.run(transport=args.transport, host=args.host, port=args.port)
        elif args.cmd == "verify":
            cmd_verify(conn)
        elif args.cmd == "describe":
            cmd_describe(conn)
        elif args.cmd == "read":
            cmd_read(conn, args.entity, args.claim)
        elif args.cmd == "aggregate":
            cmd_aggregate(conn, args.entity, args.claim)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
