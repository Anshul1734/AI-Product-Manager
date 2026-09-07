# AI Product Manager

Turns a product problem into a plan a team can build: a product vision, a PRD, a
RICE-scored roadmap, a system architecture, and a delivery backlog — produced by
a graph of specialist agents, each grounded in a retrieval corpus of
product-management practice, and reviewed by an independent critic.

Every number in the output is computed rather than generated, and every artifact
is validated against a schema before it reaches you.

---

## What actually happens when you submit an idea

```
retrieve ──> planner ──┬─> analyst (PRD) ──> architect ──┐
   (RAG)               │                                  ├─> backlog ─> critic ─> refine?
                       └─> prioritizer (RICE) ────────────┘
```

`analyst` and `prioritizer` depend only on the vision, so they run concurrently.
`critic` and `refine` are gated on the requested depth. Nodes marked
non-critical can fail without losing the run — a failed review returns an
unreviewed plan rather than nothing.

| Agent | Produces | Tools it can call |
|---|---|---|
| **Planner** | Vision, jobs-to-be-done, non-goals, assumptions | `search_pm_knowledge`, `recall_similar_plans` |
| **Analyst** | PRD: personas, INVEST stories, Given/When/Then criteria, metrics | `search_pm_knowledge` |
| **Prioritizer** | RICE-scored, MoSCoW-labelled feature list | `score_features_rice` |
| **Architect** | Pattern choice, stack, endpoints, data model, decision records | `search_pm_knowledge` |
| **Ticket generator** | Epics → stories → tasks, walking-skeleton-first | — |
| **Critic** | 0–10 scores on completeness, consistency, specificity, feasibility | — |

The critic runs on a **different model family** from the agents that wrote the
plan, so a review is not one model grading its own homework.

---

## The agentic parts, concretely

**Real tool calling.** Agents use native function calling against a typed tool
registry ([`app/tools/`](backend/app/tools/)). Each runs a two-phase loop: a
research phase where tools are available, then an emit phase where they are
withdrawn and the model must produce the target schema. The phases are
separated because a model that has just made a successful tool call will keep
making them where the answer belongs.

**Schema-validated output with repair.** Every artifact is a Pydantic model
([`app/schemas/artifacts.py`](backend/app/schemas/artifacts.py)). On a
validation failure the specific field errors are fed back as a repair prompt.
Truncated JSON is salvaged by balancing open structures rather than discarded,
and a response cut off by the token ceiling gets a different repair message from
one that is merely wrong — telling a model to fix field errors when it actually
ran out of room just reproduces the overlong answer.

**Arithmetic that cannot drift.** RICE scores are computed in Python from
validated estimates and re-sorted server-side
([`app/tools/scoring.py`](backend/app/tools/scoring.py)). The model supplies
reach/impact/confidence/effort and a justification; it never does the division.
*(The previous version of this project generated RICE scores with
`random.randint`.)*

**Hybrid RAG.** BM25 lexical retrieval fused with dense vector retrieval via
Reciprocal Rank Fusion ([`app/rag/`](backend/app/rag/)). Lexical search catches
exact terminology (`RICE`, `3NF`, `idempotency key`) that embeddings blur; dense
search catches paraphrase. RRF combines the ranked lists without needing score
calibration between them, which is what makes it degrade gracefully when one
retriever is unavailable. Retrieved passages carry `[S#]` markers, and the
citations survive into the API response and the UI.

**Bounded reflection.** At `deep` depth the critic's per-artifact scores drive a
single refinement pass: only artifacts below the threshold are regenerated, and
only with that critic's imperative fix instructions. One pass, not a loop —
unbounded critique/regenerate cycles burn latency and oscillate between equally
mediocre versions.

**MCP, both directions.**
[`mcp_server/`](backend/mcp_server/) exposes the pipeline as MCP tools,
resources, and prompts so Claude Desktop or Claude Code can drive it directly.
[`app/tools/mcp_bridge.py`](backend/app/tools/mcp_bridge.py) goes the other way:
it attaches external MCP servers and adapts their tools into the same registry,
so the backlog agent can reach a real Linear or Jira instance.

**Observability.** Runs stream Server-Sent Events, so the UI shows which agent
is working, which tool it reached for, and where a schema repair was needed —
along with per-agent model, duration, and token cost.

---

## Quick start

Requires Python 3.11+, Node 18+, and a [Groq API key](https://console.groq.com/keys).

```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS / Linux
pip install -r requirements.txt

cp .env.example .env              # then set GROQ_API_KEY
python -m app.rag.ingest          # build the knowledge index (~160 KB, no API key needed)
uvicorn asgi:app --reload --port 8001
```

```bash
# Frontend, in a second terminal
cd frontend
npm install
npm start                         # http://localhost:3000
```

API docs at http://localhost:8001/docs.

### Model availability

Groq's catalogue differs per account. List what your key can reach:

```bash
curl -H "Authorization: Bearer $GROQ_API_KEY" \
     https://api.groq.com/openai/v1/models | jq '.data[].id'
```

Whatever you pick for `GROQ_MODEL` must support **both** native tool calling and
JSON mode. `GROQ_ALT_MODEL` need not — the client detects a model that rejects
`response_format` and falls back to schema-in-prompt for it.

### Optional: enable dense retrieval

Retrieval runs BM25-only out of the box, which needs no external service. To add
the dense half of the hybrid, set `OPENAI_API_KEY` or `JINA_API_KEY` in
`backend/.env` and rebuild the index:

```bash
python -m app.rag.ingest --with-vectors
```

---

## Rate limits shape the design

Groq's free tier allows **8,000 tokens per minute, per model**. That single fact
drives several decisions worth knowing about:

- Agents are spread across three models so a run draws on three separate
  budgets. Assigning consecutive agents to the same model is what causes stalls,
  so `quick` deliberately uses all three and finishes without pacing.
- A tokens-per-minute overage comes back as **HTTP 413 with
  `code: rate_limit_exceeded`**, not 429. Classifying on status code alone makes
  a transient condition look like a permanently malformed request; the client
  reads the error body instead ([`app/llm/client.py`](backend/app/llm/client.py)).
- Requests are paced client-side against a sliding 60-second window per model,
  reconciled against the provider's own `x-ratelimit-remaining-tokens` header
  ([`app/llm/ratelimit.py`](backend/app/llm/ratelimit.py)).
- Agents pass compact digests to each other rather than full JSON dumps
  ([`app/agents/digests.py`](backend/app/agents/digests.py)). A serialized PRD is
  ~3,000 tokens of punctuation-heavy JSON restating structure the next agent
  does not need.

On a paid tier, raise `GROQ_TPM_LIMIT` and `MAX_TOOL_ITERATIONS` — pacing
disappears and the agents get fuller tool loops.

| Depth | Agents | Review | Typical free-tier wall clock |
|---|---|---|---|
| `quick` | 4 | no | ~45–90s |
| `standard` | 6 | yes | ~2–4 min |
| `deep` | 6 + revision | yes, and acts on it | ~3–5 min |

---

## Deployment

**The API needs a persistent web service, not a serverless function.** A
Standard run exceeds the 60-second request cap on Vercel/Netlify functions.

A [`render.yaml`](render.yaml) blueprint deploys both services on Render's free
tier:

1. Push the repo, then in Render pick **New → Blueprint** and select it.
2. Set `GROQ_API_KEY` on `aipm-api`.
3. Set `REACT_APP_API_URL` on `aipm-web` to the API's URL, and `CORS_ORIGINS` on
   `aipm-api` to the web service's origin.

Render's free tier sleeps after 15 minutes idle, so the first request after a
pause pays a cold start.

Deploying the frontend to Vercel instead works fine — it is a static build.
[`vercel.json`](vercel.json) is configured for that, with the API routed to
`backend/asgi.py`; just note the 60-second ceiling applies to `standard` and
`deep` runs there.

---

## Layout

```
backend/
  asgi.py                  Single ASGI entrypoint for every target
  app/
    agents/                Six agents + the two-phase tool loop, digests, JSON repair
    orchestration/         DAG engine (concurrent layers, conditional nodes), pipeline, state
    llm/                   Groq client, typed errors, per-model token pacing
    rag/                   Chunking, embeddings, hybrid BM25+dense store, retriever
      knowledge/           12 curated PM/architecture documents (the corpus)
      index/               Committed index artifact — no build step at deploy
    tools/                 Tool registry, RAG/scoring/memory tools, MCP client bridge
    schemas/               Artifact models and API contracts
    memory/                BM25 recall over past plans
    routers/               generate, generate/stream (SSE), knowledge, memory, export, health
  mcp_server/              MCP server exposing the pipeline (see its README)
frontend/src/
  components/              Composer, live agent trace, tabbed results, knowledge explorer
  lib/api.ts               Typed client incl. SSE reader
```

---

## Notes on what this replaced

The earlier version of this project had a `LangGraph` orchestrator, an evaluator
agent, and a memory system that were never reachable: `requirements.txt` did not
list `langgraph`, `langchain`, or `google-generativeai`, and the agent classes
referenced undefined variables left over from an abandoned migration. What
actually served traffic was one prompt asking a model to role-play all four
agents and return a single JSON blob — with `random.randint` RICE scores and a
silent fallback that served hardcoded demo text whenever the API call failed,
which it always did, because the pinned model did not exist on the account.

The orchestration, retrieval, scoring, and review described above are what the
project now does.
