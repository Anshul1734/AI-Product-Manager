---
title: API Design Practices
doc_id: api-design
domain: architecture
tags: [architecture, api, rest, pagination, idempotency, versioning]
authority: practice
---

# API Design Practices

An API is a contract with a much longer lifespan than the code behind it, so the expensive mistakes are the ones that are hard to reverse: resource naming, pagination model, error shape, and versioning strategy. Everything else can be fixed additively. The practices below assume a JSON-over-HTTP API consumed by first-party clients and third-party integrators. The governing principles are: model resources as nouns and let HTTP verbs carry the operation; return status codes that let a client decide what to do without parsing prose; make every write safe to retry; paginate everything that returns a collection; and version only when you must break a contract. Where these principles conflict with convenience, follow the principle — inconsistent APIs cost integrators more than any single elegant endpoint saves them.

## REST resource naming

Resources are plural nouns; operations are HTTP verbs. Paths identify things, not actions.

Correct: `/v1/report-schedules`, `/v1/report-schedules/{id}`, `/v1/accounts/{account_id}/report-schedules`, `/v1/report-schedules/{id}/runs`.

Incorrect: `/v1/getReportSchedules`, `/v1/report-schedule/create`, `/v1/deleteSchedule?id=5`.

Conventions to apply consistently:

- **Plural collections, singular members.** `/orders` and `/orders/{id}`. Do not mix `/order` and `/orders`.
- **Kebab-case in paths, snake_case or camelCase in JSON bodies** — pick one body convention and never mix. `report-schedules` in the path, `next_run_at` in the payload.
- **Nest at most one level.** `/accounts/{id}/schedules` is fine; `/accounts/{id}/schedules/{id}/runs/{id}/logs` is not. Beyond one level of nesting, expose the deep resource at the top level with a filter: `/runs?schedule_id=abc`.
- **Nest only for true ownership.** If a child can exist independently or be re-parented, keep it top-level.
- **Filtering, sorting, and field selection go in the query string:** `?status=active&sort=-created_at&fields=id,name,next_run_at`. Use a leading `-` for descending sort.
- **Opaque, non-sequential IDs** in public APIs. Prefixed IDs like `sch_7Fk29dQ` are self-describing in logs and prevent enumeration; sequential integers leak volume and invite scraping.

Actions that are genuinely not CRUD get a sub-resource with a verb, used sparingly: `POST /v1/report-schedules/{id}/pause`, `POST /v1/invoices/{id}/void`. Prefer modeling state as a field (`PATCH {"status":"paused"}`) when the transition has no side effects beyond the state change; use the action endpoint when the transition triggers real work, requires distinct permissions, or has its own audit meaning.

## HTTP verbs and status codes

Verb semantics: **GET** reads and never mutates (safe, idempotent, cacheable). **POST** creates or triggers, and is not idempotent by default. **PUT** replaces a resource wholesale and is idempotent. **PATCH** partially updates and is not necessarily idempotent. **DELETE** removes and is idempotent.

Status codes that matter, with the exact condition for each:

| Code | Use when |
|---|---|
| 200 OK | Successful GET, PATCH, PUT, or a POST that returns a result but creates nothing |
| 201 Created | POST created a resource. Include a `Location` header with the new URL and the created object in the body |
| 202 Accepted | Work accepted for asynchronous processing. Return a job/run resource the client can poll |
| 204 No Content | Success with an intentionally empty body — typically DELETE, or a PUT where returning the object is pointless |
| 400 Bad Request | Malformed syntax: unparseable JSON, wrong content type, missing required query param |
| 401 Unauthorized | No credentials or invalid credentials. Means "not authenticated" |
| 403 Forbidden | Authenticated but not permitted. Means "not authorized" |
| 404 Not Found | Resource does not exist, or exists but the caller must not learn of its existence (cross-tenant access — return 404, not 403) |
| 409 Conflict | The request conflicts with current state: duplicate unique key, concurrent-edit version mismatch, deleting a resource with dependents, or state-machine violation such as pausing an already-paused schedule |
| 422 Unprocessable Entity | Syntactically valid but semantically invalid: `end_date` before `start_date`, 21 recipients when the max is 20, an invalid cron expression. Return per-field errors |
| 429 Too Many Requests | Rate limit exceeded. Must include `Retry-After` in seconds, plus `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` |
| 500 Internal Server Error | Unhandled server fault. Never leak stack traces; include a trace/request ID |
| 503 Service Unavailable | Dependency down or shedding load. Include `Retry-After` |

The distinction that trips teams most often is 400 versus 422: **400 means "I could not parse this," 422 means "I understood it and it is invalid."** Clients treat these differently — 400 is a bug in the integration, 422 is user-correctable input. Likewise, use 409 rather than 400 for uniqueness violations so clients can implement a fetch-then-merge path rather than surfacing a generic failure.

## Pagination strategies

Every collection endpoint must paginate from day one, with a default page size (commonly 25 or 50) and a hard maximum (commonly 100, never unbounded). Retrofitting pagination is a breaking change.

**Offset pagination** — `GET /v1/runs?limit=50&offset=100`.

- Pros: trivial to implement, supports jumping to page N, gives an exact total count, and maps directly to SQL `LIMIT/OFFSET`.
- Cons: results drift when rows are inserted or deleted between requests, so items get skipped or duplicated across pages. Performance degrades badly at depth because the database must scan and discard all skipped rows — `OFFSET 500000` reads half a million rows to return 50.
- Use for: admin tables under roughly 10,000 rows where users expect page numbers and a total.

**Cursor (keyset) pagination** — `GET /v1/runs?limit=50&cursor=eyJpZCI6InJ1bl84OTIiLCJ0cyI6MTcxfQ`.

- Pros: constant-time at any depth because it becomes `WHERE (created_at, id) < (:ts, :id) ORDER BY created_at DESC, id DESC LIMIT 50`, and it is stable under concurrent inserts.
- Cons — the central tradeoff: **you cannot jump to an arbitrary page and you cannot cheaply return a total count.** The client can only go forward (and backward, if you support a reverse cursor). This is the price of stability and depth performance, and it is why infinite-scroll and API feeds use cursors while paginated admin grids use offsets.
- Use for: any high-volume, append-heavy, or externally consumed collection — event logs, activity feeds, webhook deliveries, transaction history.

Cursor implementation rules: the cursor must encode a **unique, monotonic tiebreaker** alongside the sort key (a timestamp alone collides and silently drops rows — always pair it with the primary key), it should be an opaque base64 token so you can change its internals without breaking clients, and it should be validated and rejected with 400 if tampered with. Response envelope for cursors: `{"data": [...], "next_cursor": "…", "has_more": true}` and omit `total` — offering an approximate total invites clients to depend on it.

## Idempotency keys for POST

POST is not idempotent, so a client that times out cannot know whether its request succeeded. Without protection, retrying creates duplicate charges, duplicate orders, and duplicate emails. The fix is a client-supplied idempotency key, the pattern Stripe popularized.

Contract:

1. The client generates a UUIDv4 per logical operation and sends it as the `Idempotency-Key` header. The key belongs to the *intent*, not to the retry — all retries of the same operation reuse the same key.
2. The server, inside a transaction, attempts to insert `(tenant_id, endpoint, idempotency_key)` into a unique-indexed `idempotency_records` table along with a hash of the request body.
3. **New key:** process the request, then store the response status and body against the key. Return the real response.
4. **Existing key, completed:** return the stored response verbatim, ideally with a header such as `Idempotency-Replayed: true`. Do not re-execute.
5. **Existing key, in flight:** return 409 Conflict with a message telling the client to retry after a short delay.
6. **Existing key, different request body hash:** return 422 (or 400) with a clear message — reusing a key for a different payload is a client bug and must fail loudly rather than silently returning the wrong resource.
7. Expire records after a fixed retention window; 24 hours is a common choice, and it must exceed the client's maximum retry window.

Scope keys per tenant and per endpoint so one tenant cannot collide with or probe another's keys. Apply idempotency to every POST with side effects — payments, sends, provisioning, external API calls — and skip it only for pure reads or genuinely repeatable writes. Note that PUT and DELETE are already idempotent by definition and do not need keys, and that idempotency is not the same as concurrency control: for concurrent *edits* use `If-Match` with an ETag or a `version` column and return 409 on mismatch.

## API versioning approaches

Version only to break a contract. Additive changes — a new optional field, a new endpoint, a new enum value that clients must already tolerate — should never bump a version.

Three approaches:

- **URL path versioning** (`/v1/…`, `/v2/…`). Most common and most operationally friendly: trivially visible in logs, easy to route at the gateway, easy for integrators to reason about. Downside: a coarse, whole-API version, so a v2 forces migration of clients unaffected by the breaking change. Recommended default for most products.
- **Header versioning** (`Accept: application/vnd.acme.v2+json` or `API-Version: 2026-03-01`). Keeps URLs stable and permits fine-grained, date-based versions; Stripe's model pins each account to the version it signed up with and transforms requests and responses between versions. Powerful, and expensive — it requires a transformation layer and a compatibility test matrix. Choose this only if you have many long-lived third-party integrators and the engineering capacity to maintain the transforms.
- **Query-parameter versioning** (`?version=2`). Easy to add, easy to forget, easy to cache incorrectly. Avoid for public APIs.

Rules regardless of approach:

1. **Support at most two major versions concurrently**, and publish a deprecation window before removal — 6 months minimum for internal consumers, 12 months for public APIs.
2. **Signal deprecation in-band** with `Deprecation` and `Sunset` headers plus a `Link` to the migration guide, so integrators discover it without reading a changelog.
3. **Never change the meaning of an existing field.** Adding a value to an enum is a breaking change for clients with strict deserialization; document enum extensibility from the start and instruct clients to treat unknown values as a default case.
4. **Measure before sunsetting.** Track requests per version per client so you can contact the specific integrators still on v1 rather than guessing.

## Error response envelope

Use one error envelope across every endpoint and status code. Clients build error handling once, and support can trace any failure from the response alone.

```json
{
  "error": {
    "type": "validation_error",
    "code": "recipient_limit_exceeded",
    "message": "Maximum 20 recipients per schedule.",
    "status": 422,
    "request_id": "req_01HN4K2P9XQ",
    "doc_url": "https://api.acme.com/docs/errors/recipient_limit_exceeded",
    "details": [
      {
        "field": "recipients",
        "code": "too_many_items",
        "message": "Received 21 recipients; maximum is 20.",
        "limit": 20,
        "received": 21
      }
    ]
  }
}
```

Field responsibilities: `type` is a coarse machine class (`validation_error`, `authentication_error`, `permission_error`, `not_found`, `conflict`, `rate_limit_error`, `api_error`) that lets a client branch with a switch. `code` is a stable, specific, machine-readable string that must never change once published — this is the field integrators write logic against, so treat it as part of the contract. `message` is human-readable, safe to display, and never contains stack traces, SQL, or internal hostnames. `request_id` is echoed from the request and appears in your logs, making support tickets resolvable in one lookup. `details` is an array so multi-field validation returns every problem at once rather than forcing the client through a fix-one-resubmit loop.

Rules: always return the envelope, including for 500s (with a generic message plus the request ID); return HTTP status codes and the envelope together rather than returning 200 with an error body, which breaks every HTTP client's error handling and all intermediary caching; and keep error codes documented in a single table with the recommended client action for each. RFC 9457 `application/problem+json` is a reasonable standards-based alternative with the same intent — pick one and be consistent.

## When GraphQL or gRPC beats REST

REST over JSON is the right default: universally understood, cacheable via HTTP semantics, debuggable with curl, and requiring no client tooling. Deviate for specific reasons.

**Choose GraphQL when:** many heterogeneous clients (web, iOS, Android, partner apps) need different field subsets from the same graph; a single screen would otherwise require 4-10 REST round trips; the data is genuinely graph-shaped with deep, varied traversals; and clients iterate faster than the backend can ship endpoints. Costs to accept: HTTP caching largely stops working (single POST endpoint) and must be replaced with persisted queries plus a CDN-level scheme; N+1 resolution requires DataLoader-style batching; you must add query depth and complexity limits or a malicious query will consume the database; authorization must be enforced per field rather than per endpoint; and observability tooling needs GraphQL-aware instrumentation because every request is a 200 to `/graphql`. Do not adopt GraphQL for a single first-party web client and one backend team — the overhead exceeds the benefit.

**Choose gRPC when:** the traffic is internal service-to-service, high-volume, and latency-sensitive; you want generated clients and enforced schemas from a `.proto` contract; you need bidirectional or server streaming; or payloads are large enough that Protobuf's compactness matters. Typical gains over JSON/REST are roughly 2-5x smaller payloads and meaningfully lower serialization CPU. Costs: not natively callable from browsers (needs grpc-web plus a proxy), harder to debug by hand, and it requires schema-registry and code-generation discipline in CI.

Decision heuristics: internal high-throughput service-to-service traffic → gRPC. Public and partner-facing APIs → REST, because integrators already know it and can debug it. Many client platforms with divergent data needs → GraphQL for the client-facing gateway, REST or gRPC behind it. Mixed architectures are normal and correct — gRPC internally with a REST edge gateway is a common and defensible topology.
