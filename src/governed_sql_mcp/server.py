"""MCP server — the delivery surface for governed-sql-mcp.

A thin layer over :mod:`governed_sql_mcp.query`. Tools are read-only and typed;
the caller's claim flows in through a context variable (set by an auth layer in
production, or defaulted to the dev caller locally). All governance — row-level
security, view boundaries, masking — lives in the query layer, so this module
stays trivial.
"""

from __future__ import annotations

import contextvars

from governed_sql_mcp import db, query

_CURRENT_CLAIM: contextvars.ContextVar[str] = contextvars.ContextVar(
    "governed_sql_claim", default="admin"
)


def set_caller(claim: str) -> None:
    """Set the caller claim for the current context (used by tests and auth layers)."""
    _CURRENT_CLAIM.set(claim)


def create_mcp():
    """Build the MCP server. ``mcp`` is imported lazily (the CLI runs without it)."""
    from mcp.server.mcpserver import MCPServer

    conn = db.connect(":memory:")
    db.seed(conn)

    mcp = MCPServer(name="governor-sql-mcp")

    @mcp.tool()
    def describe_entities() -> list[dict]:
        """Describe the published views and their columns.

        Base tables are never exposed; the views are the security boundary.
        """
        return query.describe_entities(conn)

    @mcp.tool()
    def read_records(entity: str) -> dict:
        """Read rows from a published view, scoped by the caller's row-level security.

        Returns visible/withheld/total counts so the caller can distinguish
        "no data" from "data you are not allowed to see".
        """
        return query.read_records(conn, entity, claim=_CURRENT_CLAIM.get())

    @mcp.tool()
    def aggregate_records(entity: str) -> dict:
        """Aggregate a published view, scoped by the caller's row-level security."""
        return query.aggregate_records(conn, entity, claim=_CURRENT_CLAIM.get())

    return mcp
