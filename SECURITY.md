# Security Policy

## Reporting a vulnerability

Report security issues privately rather than opening a public issue. Include a
description, reproduction steps, and any proposed fix. Do not include real
customer data or credentials in any report.

## Security posture

- **Read-only by construction.** The MCP surface has exactly three tools —
  `describe_entities`, `read_records`, `aggregate_records` — and no write path
  exists anywhere in the code. Create, update, delete, and execute are absent,
  not merely denied.
- **The views are the security boundary.** Base tables are never exposed. The
  model can only see the columns a published view deliberately includes; the
  raw `account_number` column is not present in any view.
- **Fail-closed row-level security.** Unknown or missing claims resolve to an
  empty result, never somebody else's data. A misconfiguration yields zero
  rows, not a leak.
- **Honest disclosure.** Results report `visible_count`, `withheld_count`, and
  `total_count`, so a caller can distinguish "no data" from "data I cannot
  see."
- **Synthetic data only.** The seeded book is deterministic and generated from
  constants; no real customer data is involved.
- **No credentials.** SQLite in-memory by default; nothing to configure, no
  secret to store. A production deployment would swap the engine for SQL
  Server with `SESSION_CONTEXT`-driven security predicates (see
  `sql/03_rls.sql`) and add an auth layer in front of the server.

## Supported versions

Only the latest `main` branch is supported for security fixes.
