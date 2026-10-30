"""Uploaded-document flow end to end, against an in-process fake of Qdrant's
REST API and a deterministic fake embedder: no network, no tokens spent.

    cd backend && PYTHONPATH=. python tests/test_uploads.py

The fake enforces Qdrant Cloud's strict mode (filters only on indexed payload
fields), so a missing payload index fails here rather than in production.
"""
import asyncio, hashlib, io, json, math, re, sys

import httpx
from fastapi.testclient import TestClient

from app.core.config.settings import settings
import app.rag.retriever as retriever_module
import app.rag.uploads as uploads_module
from app.rag.retriever import UPLOAD_LABEL
from app.rag.uploads import QdrantStore, UploadedDocuments, UploadError

API_KEY = "test-key"
failures = []


def check(condition, label):
    print(("  ok    " if condition else "  FAIL  ") + label)
    if not condition:
        failures.append(label)


# ------------------------------------------------------------------ fakes

class FakeQdrant:
    """Just enough of Qdrant's REST API: collections, indexes, points."""

    def __init__(self):
        self.collections = {}

    def _match(self, payload, flt, indexes):
        for cond in (flt or {}).get("must", []):
            if cond["key"] not in indexes:
                raise PermissionError(f"Index required but not found for \"{cond['key']}\"")
            if payload.get(cond["key"]) != cond["match"]["value"]:
                return False
        return True

    @staticmethod
    def _select(payload, selector):
        if selector is True:
            return payload
        return {key: payload[key] for key in selector if key in payload}

    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.headers.get("api-key") != API_KEY:
            return httpx.Response(401, json={"status": {"error": "Unauthorized"}})
        path = request.url.path
        body = json.loads(request.content) if request.content else {}
        parts = path.strip("/").split("/")
        if parts == ["collections"]:
            return httpx.Response(200, json={"result": {"collections": []}})
        name, rest = parts[1], parts[2:]
        col = self.collections.get(name)
        if col is None and not (request.method == "PUT" and not rest):
            return httpx.Response(404, json={"status": {"error": f"Collection `{name}` doesn't exist!"}})
        try:
            if not rest and request.method == "GET":
                return httpx.Response(200, json={"result": {"config": {"params": {"vectors": {"size": col["size"], "distance": "Cosine"}}}}})
            if not rest and request.method == "PUT":
                if col is not None:
                    return httpx.Response(409, json={"status": {"error": f"Wrong input: Collection `{name}` already exists!"}})
                self.collections[name] = {"size": body["vectors"]["size"], "points": {}, "indexes": set()}
                return httpx.Response(200, json={"result": True})
            if rest == ["index"]:
                col["indexes"].add(body["field_name"])
                return httpx.Response(200, json={"result": {"status": "completed"}})
            if rest == ["points"] and request.method == "PUT":
                for point in body["points"]:
                    if len(point["vector"]) != col["size"]:
                        return httpx.Response(400, json={"status": {"error": "Wrong input: Vector dimension error"}})
                    col["points"][point["id"]] = point
                return httpx.Response(200, json={"result": {"status": "completed"}})
            if rest == ["points", "query"]:
                hits = [
                    {"id": pid, "score": sum(a * b for a, b in zip(body["query"], p["vector"])),
                     "payload": self._select(p["payload"], body.get("with_payload", True))}
                    for pid, p in col["points"].items()
                    if self._match(p["payload"], body.get("filter"), col["indexes"])
                ]
                hits.sort(key=lambda hit: hit["score"], reverse=True)
                return httpx.Response(200, json={"result": {"points": hits[: body["limit"]]}})
            if rest == ["points", "scroll"]:
                ids = sorted(pid for pid, p in col["points"].items()
                             if self._match(p["payload"], body.get("filter"), col["indexes"]))
                if body.get("offset") is not None:
                    ids = [pid for pid in ids if pid >= body["offset"]]
                page, more = ids[: body["limit"]], ids[body["limit"]:]
                return httpx.Response(200, json={"result": {
                    "points": [{"id": pid, "payload": self._select(col["points"][pid]["payload"], body["with_payload"])} for pid in page],
                    "next_page_offset": more[0] if more else None}})
            if rest == ["points", "delete"]:
                for pid in [pid for pid, p in col["points"].items()
                            if self._match(p["payload"], body.get("filter"), col["indexes"])]:
                    del col["points"][pid]
                return httpx.Response(200, json={"result": {"status": "completed"}})
        except PermissionError as exc:
            return httpx.Response(400, json={"status": {"error": str(exc)}})
        return httpx.Response(404, json={"status": {"error": f"no route {request.method} {path}"}})


class FakeEmbeddings:
    """Hashed bag-of-words vectors: shared words -> higher cosine."""

    name = "fake"

    def __init__(self, dimensions=64):
        self.dimensions = dimensions

    @property
    def enabled(self):
        return True

    async def embed(self, texts, *, is_query=False):
        vectors = []
        for text in texts:
            vector = [0.0] * self.dimensions
            for word in re.findall(r"[a-z0-9]+", text.lower()):
                vector[int(hashlib.md5(word.encode()).hexdigest(), 16) % self.dimensions] += 1.0
            norm = math.sqrt(sum(v * v for v in vector)) or 1.0
            vectors.append([v / norm for v in vector])
        return vectors


# ------------------------------------------------------------- fixtures

MARKDOWN = b"""# Zephyrline research

## Churn interviews
Twelve warehouse managers told us Zephyrline churn is driven by manual pallet
reconciliation every Friday, which takes four hours and is error-prone.

## Constraints
The product must run on the existing Oracle 19c database. No new databases may
be introduced before the 2027 audit; integration happens through nightly CSV.
"""


def make_docx() -> bytes:
    import docx
    document = docx.Document()
    document.add_heading("Pricing decisions", level=1)
    document.add_paragraph("Enterprise tier is priced per warehouse at 400 dollars per month, "
                           "agreed with the Quillmark sales team in the March pricing review.")
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def make_pdf() -> bytes:
    """A two-page text PDF, assembled by hand with a correct xref table."""
    texts = ["Page one: the Harborview pilot covers three distribution centres in Ohio.",
             "Page two: pilot success means reconciliation time falls below thirty minutes."]
    objects = ["<< /Type /Catalog /Pages 2 0 R >>",
               "<< /Type /Pages /Kids [3 0 R 5 0 R] /Count 2 >>"]
    for index, text in enumerate(texts):
        stream = f"BT /F1 11 Tf 40 700 Td ({text}) Tj ET"
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {4 + index * 2} 0 R "
                       f"/Resources << /Font << /F1 {3 + len(texts) * 2} 0 R >> >> >>")
        objects.append(f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream")
    objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    out, offsets = b"%PDF-1.4\n", []
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n{obj}\nendobj\n".encode()
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += "".join(f"{offset:010d} 00000 n \n" for offset in offsets).encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return out


# ---------------------------------------------------------------- tests

def main():
    fake = FakeQdrant()
    embeddings = FakeEmbeddings()
    settings.UPLOADS_ENABLED = True
    settings.QDRANT_URL = "http://qdrant.test:6333"
    settings.QDRANT_API_KEY = API_KEY
    settings.QDRANT_COLLECTION = "test_uploads"
    settings.EMBEDDING_PROVIDER = "jina"
    settings.JINA_API_KEY = settings.JINA_API_KEY or "fake-key"
    transport = httpx.MockTransport(fake.handler)
    uploads_module._documents = UploadedDocuments(store=QdrantStore(transport=transport), provider=embeddings)
    retriever_module.get_embedding_provider = lambda: embeddings

    from app.main import app
    client = TestClient(app)
    ws, other = "ws_test_alpha", "ws_test_bravo"

    print("--- upload")
    response = client.get("/api/v1/documents", params={"workspace_id": ws})
    check(response.status_code == 200 and response.json()["data"]["enabled"] and response.json()["data"]["documents"] == [],
          "empty workspace lists no documents (before the collection exists)")

    def upload(name, data, workspace=ws):
        return client.post("/api/v1/documents", data={"workspace_id": workspace}, files={"file": (name, data)})

    md = upload("zephyrline-research.md", MARKDOWN)
    check(md.status_code == 200 and md.json()["data"]["document"]["chunk_count"] == 2, f"markdown indexed by heading: {md.json()}")
    check(fake.collections["test_uploads"]["indexes"] >= {"workspace_id", "doc_id", "sha256"}, "payload indexes created")
    again = upload("copy.md", MARKDOWN)
    check(again.status_code == 200 and again.json()["data"]["document"]["duplicate"], "identical re-upload is deduplicated")
    dx = upload("pricing.docx", make_docx())
    check(dx.status_code == 200, f"docx indexed: {dx.json()}")
    pdf = upload("harborview-pilot.pdf", make_pdf())
    check(pdf.status_code == 200 and pdf.json()["data"]["document"]["chunk_count"] == 2, f"pdf indexed per page: {pdf.json()}")
    headings = sorted(p["payload"]["heading"] for p in fake.collections["test_uploads"]["points"].values()
                      if p["payload"]["doc_id"] == pdf.json()["data"]["document"]["doc_id"])
    check(headings == ["Page 1", "Page 2"], f"pdf passages cite their page: {headings}")

    check(upload("tool.exe", b"MZ\x90\x00binary").status_code == 415, "unsupported type -> 415")
    check(upload("empty.txt", b"").status_code == 400, "empty file -> 400")
    check(upload("x.txt", b"hello world, this is enough text", workspace="bad id!").status_code == 422, "malformed workspace id -> 422")
    settings.UPLOAD_MAX_BYTES, saved = 50, settings.UPLOAD_MAX_BYTES
    check(upload("big.txt", b"x" * 51).status_code == 413, "oversized file -> 413")
    settings.UPLOAD_MAX_BYTES = saved

    listed = client.get("/api/v1/documents", params={"workspace_id": ws}).json()["data"]["documents"]
    check(len(listed) == 3, f"workspace lists 3 documents: {[d['filename'] for d in listed]}")
    check(client.get("/api/v1/documents", params={"workspace_id": other}).json()["data"]["documents"] == [],
          "other workspace sees none of them")

    print("--- retrieval")
    body = {"query": "Why do warehouse managers churn? Friday pallet reconciliation", "k": 3, "workspace_id": ws}
    search = client.post("/api/v1/knowledge/search", json=body).json()
    sources = [r["source"] for r in search["results"]]
    check(search["results"] and search["results"][0]["source"] == "upload"
          and "Churn" in search["results"][0]["heading"], f"own document ranks first: {[(r['title'], r['heading']) for r in search['results'][:2]]}")
    check("corpus" in sources and "uploads" in search["retrievers"], f"curated corpus still included: {sources} via {search['retrievers']}")
    hit = search["results"][0]
    check(hit["lexical_rank"] is not None and hit["dense_rank"] is not None, "upload hit found by both BM25 and dense")
    no_ws = client.post("/api/v1/knowledge/search", json={**body, "workspace_id": None}).json()
    check(all(r["source"] == "corpus" for r in no_ws["results"]), "no workspace -> curated corpus only")
    leak = client.post("/api/v1/knowledge/search", json={**body, "workspace_id": other}).json()
    check(all(r["source"] == "corpus" for r in leak["results"]), "other workspace cannot retrieve these uploads")

    print("--- pipeline")
    from app.orchestration.pipeline import ProductPlanPipeline
    from app.orchestration.state import Depth, initial_state
    pipeline = ProductPlanPipeline()
    state = initial_state("Pallet reconciliation tool for Zephyrline warehouse managers on Oracle", "t1", Depth.QUICK, ws)
    grounding, citations = asyncio.run(pipeline._grounding_for("architect", state))
    check(UPLOAD_LABEL in grounding and any(c.source == "upload" for c in citations),
          f"architect grounding includes uploads: {[(c.source, c.title) for c in citations]}")
    check("Oracle 19c" in grounding, "architect sees the database constraint")
    check(any(c.source == "corpus" for c in citations), "architect still gets curated architecture guidance")

    payload = asyncio.run(_stubbed_run(state["idea"], ws))
    retrieval = payload["meta"]["retrieval"]
    check(retrieval["uploaded_sources_cited"] > 0 and any(c["source"] == "upload" for c in payload["citations"]),
          f"full run cites uploaded sources ({retrieval['uploaded_sources_cited']})")
    payload_plain = asyncio.run(_stubbed_run(state["idea"], None))
    check(payload_plain["meta"]["retrieval"]["uploaded_sources_cited"] == 0, "run without workspace cites no uploads")

    print("--- delete and safety")
    doc_id = md.json()["data"]["document"]["doc_id"]
    check(client.delete(f"/api/v1/documents/{doc_id}", params={"workspace_id": other}).status_code == 404,
          "cannot delete from another workspace")
    check(client.delete(f"/api/v1/documents/{doc_id}", params={"workspace_id": ws}).status_code == 200, "delete own document")
    check(client.delete(f"/api/v1/documents/{doc_id}", params={"workspace_id": ws}).status_code == 404, "second delete -> 404")
    check(len(client.get("/api/v1/documents", params={"workspace_id": ws}).json()["data"]["documents"]) == 2, "2 documents remain")
    after = client.post("/api/v1/knowledge/search", json=body).json()
    check(all(r["doc_id"] != doc_id for r in after["results"]), "deleted document no longer retrieved")

    mismatched = UploadedDocuments(store=QdrantStore(transport=transport), provider=FakeEmbeddings(dimensions=32))
    try:
        asyncio.run(mismatched.add(ws, "new.txt", b"a different embedding model wrote this text"))
        check(False, "dimension mismatch is refused")
    except UploadError as exc:
        check(exc.status_code == 409, f"dimension mismatch is refused: {exc}")

    settings.QDRANT_URL = None
    status = client.get("/api/v1/documents", params={"workspace_id": ws}).json()["data"]
    check(not status["enabled"] and "QDRANT_URL" in status["reason"], "unconfigured -> explains why")
    check(upload("x.txt", b"enough text to be a document").status_code == 503, "upload when unconfigured -> 503")
    unconfigured = client.post("/api/v1/knowledge/search", json=body)
    check(unconfigured.status_code == 200, "search still works with uploads unconfigured")

    print("\nRESULT:", "ALL PASS" if not failures else f"{len(failures)} FAILURE(S)")
    sys.exit(1 if failures else 0)


async def _stubbed_run(idea, workspace_id):
    """A real graph run with every agent stubbed: retrieval and grounding are
    real, LLM calls are not. Stubs return no citations of their own, so every
    citation in the payload came from retrieval."""
    from app.agents.base import AgentRunResult
    from app.llm.client import Usage
    from app.orchestration.pipeline import ProductPlanPipeline
    from app.orchestration.state import Depth
    from app.schemas.artifacts import ProductVision, PRD, SystemArchitecture, Tickets

    outputs = {
        "planner": ProductVision.model_validate({
            "product_name": "Reconcile", "problem_statement": "x" * 60, "value_proposition": "y" * 30,
            "target_users": ["Ops"], "core_goals": ["Cut time"], "key_features_high_level": ["Import", "Match"]}),
        "analyst": PRD.model_validate({
            "problem_statement": "x" * 60, "target_users": ["Ops"],
            "user_personas": [{"name": "Priya", "description": "d", "pain_points": ["p"]}],
            "user_stories": [{"title": "t", "as_a": "a", "i_want_to": "b", "so_that": "c"}] * 3,
            "success_metrics": [{"name": "m", "description": "d", "target": "1->2"},
                                {"name": "n", "description": "d", "target": "3->4"}]}),
        "architect": SystemArchitecture.model_validate({
            "system_design": "z" * 60, "tech_stack": {"backend": "FastAPI"}, "architecture_components": ["API", "Worker"],
            "api_endpoints": [{"name": "l", "method": "GET", "endpoint": "/a", "description": "d"},
                              {"name": "c", "method": "POST", "endpoint": "/a", "description": "d"}],
            "database_schema": [{"table_name": "t", "fields": [{"name": "id", "type": "uuid"}]}]}),
        "ticket_generator": Tickets.model_validate({"epics": [{"epic_name": "E1", "stories": [
            {"story_title": "s", "acceptance_criteria": ["ac"], "tasks": [{"title": "t"}]}]}]}),
    }
    pipeline = ProductPlanPipeline()
    for name, agent in pipeline.agents.items():
        if name in outputs:
            async def run(llm, registry, _out=outputs[name], **kwargs):
                return AgentRunResult(output=_out, usage=Usage(1, 1))
            agent.run = run
    return await pipeline.run(idea, depth=Depth.QUICK, workspace_id=workspace_id)


if __name__ == "__main__":
    main()
