# Governed SQL MCP

[![CI](https://github.com/emory-usc/governed-sql-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/emory-usc/governed-sql-mcp/actions/workflows/ci.yml)

A governed, read-only MCP server over SQL. Stand it up from nothing, point an
AI agent at it, and the agent can only ever see what the caller is allowed to
see. Three things matter when you expose a database to a model, and all three
are enforced by construction:

- **Read-only by construction.** Exactly three tools — `describe_entities`,
  `read_records`, `aggregate_records` — and no write path exists anywhere in
  the code. Create, update, delete, and execute are absent, not merely denied.
- **The views are the security boundary.** Base tables are never exposed. The
  model can only see the columns a published view deliberately includes.
- **Per-user row-level security, fail-closed.** A caller's claim resolves to a
  predicate. An unresolved or absent claim sees zero rows — never everything.

The engine is SQLite (standard library), so it runs anywhere with no database
server and no credentials. The security model is documented in SQL terms
(`sql/03_rls.sql`) and maps directly onto SQL Server `SESSION_CONTEXT`
predicates in a real deployment.

## Quick start

```bash
pip install -e ".[mcp]"        # core runs with no dependencies; mcp extra adds the server
governed-sql verify            # row-level security demo (admin / manager / anonymous)
governed-sql run               # start the MCP server (streamable-http on :8000)
```

## Row-level security

| Caller claim | Rows visible |
|---|---|
| `admin` | all of them |
| `manager:mgr-01` | only that manager's customers |
| *(no claim)* | **zero** — fail closed |

## Using from LangChain / LangGraph

The server speaks standard MCP, so any MCP-capable client can consume it.
LangChain exposes it through `langchain-mcp-adapters`:

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient({
    "governed-sql": {
        "url": "http://localhost:8000/mcp",
        "transport": "streamable_http",
    }
})
tools = await client.get_tools()
# describe_entities / read_records / aggregate_records are now typed
# LangChain tools, each bound by the caller's row-level security.
```

## Deployment

- `Dockerfile` — multi-stage uv build, slim non-root runtime, healthcheck.
- `infra/main.bicep` — Container Apps with scale-to-zero (0–2 replicas),
  Log Analytics + App Insights, liveness probe. Compiles clean
  (`az bicep build`).
- `.github/workflows/deploy.yml` — GHCR build/push, Trivy scan (blocking on
  CRITICAL/HIGH), OIDC Bicep deploy on version tags.

## Security posture

See `SECURITY.md`. The short version: read-only surface, fail-closed RLS,
honest `withheld_count` disclosure, synthetic data, no credentials in the repo
or image.

## Structure

```
sql/                    schema, published views, documented RLS policy
src/governed_sql_mcp/   db / query / server / cli
infra/main.bicep        Container Apps deployment
tests/                  pytest suite (RLS, masking, read-only surface)
```
