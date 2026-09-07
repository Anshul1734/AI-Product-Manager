# MCP server

Exposes the product-management agent pipeline over the Model Context Protocol,
so any MCP client can drive it directly instead of using the web UI.

This is the inbound half of the project's MCP support. The outbound half —
consuming *other* servers' tools — lives in
[`app/tools/mcp_bridge.py`](../app/tools/mcp_bridge.py).

## Install and run

```bash
cd backend
python -m venv .venv && .venv/Scripts/activate     # Windows
# source .venv/bin/activate                        # macOS / Linux
pip install -r requirements-dev.txt                # adds the `mcp` package
python -m app.rag.ingest                           # build the knowledge index
python -m mcp_server.server                        # serves over stdio
```

Requires `GROQ_API_KEY` in `backend/.env` for `generate_product_plan`. The
knowledge and scoring tools work without it.

## Register with a client

### Claude Desktop

Add to `claude_desktop_config.json`
(`%APPDATA%\Claude\` on Windows, `~/Library/Application Support/Claude/` on macOS):

```json
{
  "mcpServers": {
    "ai-product-manager": {
      "command": "E:\\Agentic PM\\backend\\.venv\\Scripts\\python.exe",
      "args": ["-m", "mcp_server.server"],
      "cwd": "E:\\Agentic PM\\backend"
    }
  }
}
```

Use the venv's Python directly rather than relying on an activated shell, and
absolute paths throughout — the client launches the process itself.

### Claude Code

```bash
cd backend
claude mcp add ai-product-manager -- .venv/Scripts/python.exe -m mcp_server.server
```

## What it exposes

### Tools

| Tool | Purpose |
|---|---|
| `generate_product_plan` | Runs the full agent graph. Returns a complete PRD in Markdown. Args: `idea`, `depth` (`quick`/`standard`/`deep`), `thread_id`. |
| `search_pm_knowledge` | Hybrid retrieval over the PM corpus. Args: `query`, `domain`, `k`. |
| `score_features_rice` | Exact RICE scoring and ranking, computed in Python. Args: `features[]`. |
| `recall_similar_plans` | Finds previously generated plans on related problems. |
| `list_knowledge_documents` | Lists the corpus with domains and resource URIs. |

### Resources

`pmkb://{doc_id}` — full text of a knowledge document, e.g.
`pmkb://rice-prioritization`. Discover ids via `list_knowledge_documents`.

### Prompts

- `product_discovery` — pressure-tests an idea before committing to a plan:
  checks whether it states a problem or just a solution, and identifies the
  cheapest assumption to invalidate first.
- `prd_review` — reviews an existing PRD against the retrieved standards and
  returns scores plus specific edits.

## Notes

`generate_product_plan` can take one to three minutes on Groq's free tier, since
a run makes six LLM calls against an 8,000 tokens-per-minute budget and the
client paces itself to stay inside it. Use `depth="quick"` for a faster result;
it skips prioritization and the review pass.

Not run in serverless deployments — `MCPBridge` skips stdio servers there
because a function cannot spawn a subprocess, and this package is excluded from
the deployment bundle via `.vercelignore`.
