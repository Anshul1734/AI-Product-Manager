# AI Product Manager

Turns a product problem into a plan a team can build: a product vision, a PRD, a
RICE-scored roadmap, a system architecture, and a delivery backlog — produced by
a graph of specialist agents, each grounded in a retrieval corpus of
product-management practice **and in the documents you upload**, and reviewed
by an independent critic.

Every number in the output is computed rather than generated, and every artifact
is validated against a schema before it reaches you.

Upload your own material — research, interview notes, specs, constraints (PDF,
Word, Markdown, text) — and the agents build the plan on it: your documents are
stored in a vector database (Qdrant), retrieved alongside the curated corpus,
treated as facts about *your* product, and cited back to you by page or section.

---

## What actually happens when you submit an idea

Orchestrated on **LangGraph** (`StateGraph`, real thread-scoped checkpointing —
see [`app/orchestration/`](backend/app/orchestration/)):

```
START ─> retrieve ─> planner ─┬─> analyst ──> architect ─┐
                               │                           ├─> tickets ─> critic? ─> refine? ─> END
                               └─> prioritizer ────────────┘
```

Every `retrieve` — the shared one up front and the per-agent pre-grounding
before each node — searches two pools: the curated PM corpus, and the
documents uploaded to the caller's workspace (see
[Your own documents](#your-own-documents)).

`analyst` and `prioritizer` both depend only on the vision, so LangGraph runs
them in the same superstep. The fan-in is deliberately at `architect`, not at
`tickets`: `analyst` and `prioritizer` are each one hop from `planner`, so
joining there is depth-balanced. Joining two branches of *unequal* depth makes
LangGraph schedule the node once per arriving branch — the join would fire
early, with the second input still `None`. (Caught in testing: an initial join
at `tickets` ran that node twice, the first time before `architecture` existed.
`tests/test_orchestration.py` asserts every node runs exactly once per pass to
keep it that way.)

`critic` and `refine` are gated on the requested depth via conditional edges.
Non-critical nodes catch their own exceptions and return a partial state update
instead of raising — a failed review degrades the response to an unreviewed
plan rather than losing five artifacts that already succeeded. State channels
written by more than one branch (the trace, citations, token counts, errors)
declare LangGraph reducers, since a concurrent write with no reducer is a hard
`InvalidUpdateError`.

Every run is checkpointed by `thread_id` and inspectable afterwards via
`GET /api/v1/threads/{thread_id}` — which artifacts landed, which nodes ran,
where it left off.

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
research phase where tools are available, then an emit phase built from a
*fresh* context with tools withdrawn. The phases are separated for the same
reason the second one gets a fresh context rather than continuing the first: a
model that has just made a successful tool call keeps calling tools even after
they're withdrawn if the schema and a worked example are still sitting in its
context, and the provider hard-rejects that once `tool_choice` is `none`.
Findings from the research phase carry forward as plain text instead.

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

**Your own documents, in a vector database.** Uploads (PDF, DOCX, Markdown,
TXT, CSV, JSON) are parsed with provenance — a PDF passage cites its page, a
Word or markdown passage its heading — chunked, embedded, and stored in
[Qdrant](https://qdrant.tech) ([`app/rag/uploads.py`](backend/app/rag/uploads.py)).
Retrieval over them is hybrid too: dense search runs in Qdrant, BM25 runs over a
per-workspace cache. Each retrieval draws from both pools with **separate
passage counts and character budgets**, rather than one merged ranking: the
corpus says how to do product work well, the uploads say what is true about
*this* product, and a plan needs both, so neither may crowd the other out. The
uploads are searched with the idea itself rather than the corpus's
"best practice for…" phrasing, and agents are told that uploaded passages are
facts about the product that outrank general practice when they conflict.

Documents are scoped to a per-browser workspace id, so one visitor's uploads
never ground another's plans. There are no accounts, so the id is a bearer
token, not access control. Qdrant is called over its REST API with `httpx`
rather than through `qdrant-client`, which costs ~110 MB of resident memory on
import — a fifth of a free-tier instance.

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
along with per-agent model, duration, and token cost. For the full picture,
runs trace to **LangSmith** ([`app/core/observability.py`](backend/app/core/observability.py)):
LangGraph traces the graph nodes by itself, but the LLM, tool, retrieval and
embedding calls here go through the project's own `httpx` clients, which
LangSmith cannot see into — so each is wrapped with `@traceable`. See
[Observability with LangSmith](#observability-with-langsmith).

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

### Optional: enable document upload

Uploads need a Qdrant instance and an embedding key (`JINA_API_KEY` or
`OPENAI_API_KEY`). Without them everything else works and the UI says why
upload is off.

```bash
# Either a free cluster at https://cloud.qdrant.io (copy its URL + API key) ...
# ... or a local instance:
docker run -p 6333:6333 qdrant/qdrant
```

Then in `backend/.env`:

```
QDRANT_URL=http://localhost:6333        # or your https://….cloud.qdrant.io:6333
QDRANT_API_KEY=                         # required for Qdrant Cloud
JINA_API_KEY=jina_...
```

The collection and its payload indexes are created on first upload. Test the
whole flow offline (fake Qdrant, fake embeddings):
`cd backend && PYTHONPATH=. python tests/test_uploads.py`.

---

## Your own documents

In the UI, drop files into **Your documents** (on the Plan and Knowledge pages).
Each one is parsed, split into passages, embedded and stored; from then on every
plan you generate and every knowledge search draws on it, and the **Sources**
tab marks those passages **Your document**.

| | |
|---|---|
| Formats | `.pdf` `.docx` `.md` `.txt` `.csv` `.tsv` `.json` `.rst` `.log` |
| Limits (configurable) | 10 MB per file, 50 documents per workspace, 400 passages per document |
| Provenance | PDF passages cite their page, Word/markdown passages their heading |
| Not supported | Scanned PDFs without a text layer (no OCR) — rejected with a message |

**Workspaces.** The browser generates a random workspace id on first visit and
keeps it in `localStorage`; documents are stored and retrieved under that id
only. There are no accounts, so the id is a bearer token rather than access
control, and clearing site data starts an empty library.

**API.** The same flow without the UI (`workspace_id`: 6–64 chars of
`A-Z a-z 0-9 _ -`):

```bash
# upload
curl -F "workspace_id=ws_demo123" -F "file=@research.pdf" http://localhost:8001/api/v1/documents
# list / delete
curl "http://localhost:8001/api/v1/documents?workspace_id=ws_demo123"
curl -X DELETE "http://localhost:8001/api/v1/documents/<doc_id>?workspace_id=ws_demo123"
# ground a plan or a search in them: add the same workspace_id
curl -X POST http://localhost:8001/api/v1/generate -H "Content-Type: application/json" \
     -d '{"idea": "…", "depth": "quick", "workspace_id": "ws_demo123"}'
```

---

## Observability with LangSmith

Every run becomes one trace tree:

```
product_plan                        graph run — tagged depth:quick|standard|deep (+ uploads)
  retrieve                          shared grounding
    retrieve [retriever]            passages, with source (corpus / upload), score, which retriever matched
      embed [embedding]             provider, model, count, dimensions
  planner                           graph node
    retrieve [retriever]            per-agent pre-grounding
    groq.chat · planner research 1  [llm] full prompt, response, tool calls, tokens, model actually used
    search_pm_knowledge [tool]      arguments and result
    groq.chat · planner emit        [llm] the JSON answer; "repair N" if a schema retry was needed
  analyst · prioritizer · architect · tickets · critic …
```

Uploads trace as `upload_document` (filename, size, passages — never the raw
file). LLM spans record `ls_model_name`, so a budget fallback to another model
shows up, and `thread_id` metadata groups a thread's runs in LangSmith's
Threads view.

**Enable it** — in `backend/.env` (or the service's environment):

```
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_...            # smith.langchain.com → Settings → API Keys
LANGSMITH_PROJECT=ai-product-manager-dev
# LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com   # EU accounts only
```

Restart the backend, generate a plan, and open **Projects →
ai-product-manager-dev** in LangSmith. `GET /api/v1/health` reports
`components.tracing`. Tracing is off unless both the flag and a key are set, and
the `@traceable` wrappers are pass-throughs when it is off.

The app reads `.env` through pydantic-settings, which does not export to the
process environment that LangSmith reads; `Settings.export_tracing_env()`
bridges the two at import.

**Privacy:** traces contain prompts and retrieved passages, including text from
users' uploaded documents. Enable it in production deliberately.

---

## Rate limits shape the design

Groq's free tier allows **8,000 tokens per minute *and* 200,000 tokens per day,
per model**. Both are real constraints in practice, not just a footnote — they
drove several decisions:

- Agents are spread across three models so a run draws on three separate
  per-minute budgets. Assigning consecutive agents to the same model is what
  causes stalls, so `quick` deliberately uses all three and finishes without
  pacing. When one model's budget — including its daily one — is spent, the
  client falls back to a sibling model rather than failing the run
  ([`app/llm/client.py`](backend/app/llm/client.py)).
- A tokens-per-minute overage comes back as **HTTP 413 with
  `code: rate_limit_exceeded`**, not 429, and per-day overages come back as
  **429** naming a `try again in Xm` window. Classifying on status code alone
  makes a transient condition look like a permanently malformed request; the
  client reads the error body instead, and surfaces the daily-vs-per-minute
  distinction to the caller rather than Groq's raw org-id-bearing message
  ([`app/routers/workflow.py`](backend/app/routers/workflow.py)).
- Requests are paced client-side against a sliding 60-second window per model,
  reconciled against the provider's own `x-ratelimit-remaining-tokens` header
  ([`app/llm/ratelimit.py`](backend/app/llm/ratelimit.py)). A provider
  `Retry-After` is honoured but capped — taking a multi-minute exhaustion delay
  at face value, across several retries, turns one request into a many-minute
  hang; a prompt, clear failure serves a caller better than an open-ended wait.
- Agents pass compact digests to each other rather than full JSON dumps
  ([`app/agents/digests.py`](backend/app/agents/digests.py)). A serialized PRD is
  ~3,000 tokens of punctuation-heavy JSON restating structure the next agent
  does not need.

On a paid tier, raise `GROQ_TPM_LIMIT` and `MAX_TOOL_ITERATIONS` — pacing
disappears and the agents get fuller tool loops.

| Depth | Agents | Review | Free-tier wall clock |
|---|---|---|---|
| `quick` | 4 | no | ~1–4 min (no schema repairs) to ~8 min (with one) |
| `standard` | 6 | yes | several minutes, more if a model's budget is mid-window |
| `deep` | 6 + revision | yes, and acts on it | standard plus one refine pass |

These are wide because they are real client observations, not marketing
numbers: a single schema repair on the free 8k/min tier can itself take
2–3 minutes once pacing is added in, and a bucket landing near-empty mid-run
adds a full pacing wait. A paid tier removes essentially all of this.

---

## Deployment

**The API needs a persistent web service, not a serverless function.** A
Standard run exceeds the 60-second request cap on Vercel/Netlify functions.

A [`render.yaml`](render.yaml) blueprint deploys both services on Render's free
tier:

1. Push the repo, then in Render pick **New → Blueprint** and select it.
2. Set the secrets below on `aipm-api` (Render dashboard → service →
   **Environment**). Values marked `sync: false` in the blueprint are never
   committed.
3. Set `REACT_APP_API_URL` on `aipm-web` to the API's URL, and `CORS_ORIGINS` on
   `aipm-api` to the web service's origin.

| `aipm-api` variable | Needed for | Where to get it |
|---|---|---|
| `GROQ_API_KEY` | everything | [console.groq.com/keys](https://console.groq.com/keys) |
| `JINA_API_KEY` | dense retrieval **and** document upload (embeds them) | [jina.ai/embeddings](https://jina.ai/embeddings/) |
| `QDRANT_URL` | document upload | Qdrant Cloud cluster URL, e.g. `https://xxxx.cloud.qdrant.io:6333` |
| `QDRANT_API_KEY` | document upload | Qdrant Cloud → cluster → API Keys |
| `QDRANT_COLLECTION` | document upload | set by the blueprint to `user_documents` |
| `LANGSMITH_API_KEY` | tracing (optional; off without it) | smith.langchain.com → Settings → API Keys |
| `CORS_ORIGINS` | the browser calling the API | your frontend's origin |

**Uploads need a hosted vector DB.** Render's free disk is wiped on every
restart and spin-down, so documents must live outside the instance — a free
[Qdrant Cloud](https://cloud.qdrant.io) cluster is enough. Use a different
`QDRANT_COLLECTION` locally (the `.env.example` suggests `user_documents_dev`)
so development uploads never mix with production. Without the Qdrant variables
the API still runs; the UI simply explains that upload is unavailable, and
`GET /api/v1/health` reports why under `components.uploads`.

**Adding uploads to an existing deployment:** a blueprint only prompts for
`sync: false` values when it is first created, so add `QDRANT_URL` and
`QDRANT_API_KEY` by hand in the `aipm-api` Environment tab, then redeploy. The
new Python dependencies (`python-multipart`, `pypdf`, `python-docx`) install
from `requirements.txt` on that build. The frontend needs no new variables.

Render's free tier sleeps after 15 minutes idle, so the first request after a
pause pays a cold start.

Deploying the frontend to Vercel instead works fine — it is a static build.
[`vercel.json`](vercel.json) is configured for that, with the API routed to
`backend/asgi.py`; just note the 60-second ceiling applies to `standard` and
`deep` runs there, and Vercel functions cap request bodies at about 4.5 MB,
which limits upload size if the API runs there.

---

## Layout

```
backend/
  asgi.py                  Single ASGI entrypoint for every target
  app/
    core/observability.py  LangSmith tracing: @traceable LLM/tool/retriever/embedding spans
    agents/                Six agents + the two-phase tool loop, digests, JSON repair
    orchestration/         LangGraph StateGraph: fan-out/fan-in, conditional edges, checkpointing
    llm/                   Groq client, typed errors, per-model token pacing
    rag/                   Chunking, embeddings, hybrid BM25+dense store, retriever
      uploads.py           User documents: parse, chunk, embed, Qdrant, workspace-scoped retrieval
      parsers.py           PDF / DOCX / markdown / text extraction with page/heading provenance
      knowledge/           12 curated PM/architecture documents (the corpus)
      index/               Committed index artifact — no build step at deploy
    tools/                 Tool registry, RAG/scoring/memory tools, MCP client bridge
    schemas/               Artifact models and API contracts
    memory/                BM25 recall over past plans
    routers/               generate, generate/stream (SSE), knowledge, documents, memory, export, health
  mcp_server/              MCP server exposing the pipeline (see its README)
frontend/src/
  components/              Composer, live agent trace, tabbed results, knowledge explorer, document library
  lib/api.ts               Typed client incl. SSE reader and multipart upload
  lib/workspace.ts         Per-browser workspace id that scopes uploaded documents
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
