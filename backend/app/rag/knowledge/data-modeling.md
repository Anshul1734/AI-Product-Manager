---
title: Data Modeling and Storage Practices
doc_id: data-modeling
domain: data
tags: [data, database, normalization, indexing, multi-tenancy, migrations]
authority: practice
---

# Data Modeling and Storage Practices

A data model is the hardest thing in a system to change, because unlike code it has state that must be migrated while the product stays online. The practical consequence is asymmetric caution: be conservative about the shape of authoritative data and liberal about derived data, which can always be rebuilt. Default to a normalized relational schema in a single Postgres instance, add indexes from measured query plans rather than intuition, denormalize only against a specific measured read pattern, and treat tenant isolation and migration safety as design decisions made before the first row is written. The sections below cover normalization through 3NF and deliberate denormalization, store selection by access pattern, indexing strategy and its write cost, soft deletes and audit columns, multi-tenancy isolation models, and safely adding a NOT NULL column to a large table.

## Normalization through 3NF

Normalization eliminates redundancy so that each fact lives in exactly one place, which makes updates atomic and prevents contradictory data.

**First normal form (1NF):** every column holds a single atomic value; no repeating groups. A `phone_numbers` column containing `"555-0100, 555-0199"` violates 1NF; move it to a `phones` table. Note that a JSONB column is not automatically a 1NF violation if the whole document is genuinely opaque to queries, but the moment you filter or join on its interior, it is.

**Second normal form (2NF):** 1NF plus every non-key column depends on the *whole* primary key. Applies only to composite keys. In `order_items(order_id, product_id, quantity, product_name)`, `product_name` depends on `product_id` alone, not the full key, so it violates 2NF and belongs in `products`.

**Third normal form (3NF):** 2NF plus no transitive dependencies — non-key columns must not depend on other non-key columns. In `employees(id, dept_id, dept_name)`, `dept_name` depends on `dept_id`, not on `id`. Renaming a department then requires updating every employee row, and a partial failure leaves two names for one department. Fix by moving `dept_name` to `departments`.

The practical 3NF test: **can the same fact be written in two places and disagree?** If yes, you are below 3NF and you have an update-anomaly class of bug waiting.

3NF should be the starting point for all transactional, authoritative data — orders, accounts, permissions, ledger entries — because correctness there is worth more than read latency, and joins across properly indexed keys are cheap in a relational engine up to millions of rows. Higher forms (BCNF, 4NF, 5NF) matter rarely in application schemas; 3NF plus a well-chosen set of unique constraints covers the practical cases.

## Deliberate denormalization

Denormalize only against a measured problem, and only where you can state how the duplicated data is kept correct. Four legitimate cases:

1. **Read-path latency on a hot query.** A join across 5+ tables at p95 above the budget for a page loaded on every session. Example: storing `comment_count` on `posts` instead of `COUNT(*)` on 40M comments.
2. **Immutable historical snapshots.** An invoice line must record `product_name` and `unit_price` as they were at purchase time, because the product's current name and price are different facts. This is not really denormalization — it is correctly modeling a point-in-time fact.
3. **Cross-service data locality.** A service needs a small, slowly changing projection of another service's data and cannot make a synchronous call on the read path.
4. **Analytical aggregates.** Pre-computed daily rollups so dashboards do not scan the fact table.

Every denormalization requires a stated **consistency mechanism** and a **reconciliation job**: a database trigger, a transactional write in the same commit, an application-level event consumer, or a materialized view with a refresh schedule. Pick one and write it down. The failure mode is always the same — the duplicate drifts, and because nothing tells you, you find out from a customer. Ship a nightly reconciliation query that counts mismatches and alerts above a threshold; treat any nonzero count as a bug.

Two rules. Denormalize derived data, never authoritative data: `comment_count` can be rebuilt from `comments`, so a bug is recoverable; if the count *is* the truth, a bug is permanent data loss. And measure first — the common mistake is denormalizing a query that a single composite index would have made fast, paying permanent complexity for a problem an index solves in an afternoon.

## Choosing SQL, document, or key-value stores

Choose by access pattern, not by fashion. Default to relational, and justify every deviation with a specific pattern the relational store handles badly.

**Relational (Postgres, MySQL)** — choose when data has meaningful relationships, queries are varied or unknown in advance, you need multi-row ACID transactions, or you need constraints enforced by the database (uniqueness, foreign keys, checks). Postgres also covers a surprising amount of the "other" cases via JSONB with GIN indexes, full-text search, arrays, and LISTEN/NOTIFY. Practical capacity anchor: a single well-indexed Postgres instance comfortably serves tens of thousands of transactions per second and tables into the hundreds of millions of rows before sharding is the right conversation. Weakness: horizontal write scaling requires real work.

**Document (MongoDB, DynamoDB, Firestore)** — choose when the aggregate is always read and written whole, the schema genuinely varies per record (product catalogs with per-category attributes, third-party webhook payloads, CMS content), or you need single-digit-millisecond lookups by key at very high scale with a fixed access pattern. Weakness: cross-document consistency and ad-hoc queries. DynamoDB in particular requires you to know your access patterns up front because the partition-key and GSI design encodes them; adding an unanticipated query later can mean a table redesign.

**Key-value (Redis, Memcached, DynamoDB simple mode)** — choose for caching, sessions, rate-limit counters, ephemeral locks, leaderboards, and queues. Sub-millisecond reads, no query flexibility whatsoever. Weakness: it is not a system of record — treat anything in Redis as reconstructible unless you have configured and tested durability.

Two rules that prevent most storage mistakes: **one system of record per fact** — copies elsewhere are caches or projections and must be labeled as such; and prefer adding a JSONB column in Postgres to adding a second database, because polyglot persistence multiplies operational surface, backup and restore procedures, and consistency problems. Add a specialized store when a *measured* access pattern demands it — full-text relevance ranking, time-series compression, graph traversal deeper than 3 hops — not before.

## Indexing strategy

Index to serve measured queries. Read the actual `EXPLAIN ANALYZE` plan for your slowest endpoints and index what it scans.

**What to index:** every foreign key (Postgres does not create these automatically, and their absence makes joins and cascading deletes catastrophically slow); columns in `WHERE`, `JOIN`, and `ORDER BY` on frequent queries; columns with uniqueness constraints; and tenant discriminators such as `tenant_id`, which should lead almost every composite index in a shared-schema multi-tenant design.

**What not to index:** low-cardinality columns queried alone (a boolean `is_active` on a table where 95% of rows are active — the planner will sequential-scan anyway, and the index is pure write cost); columns never used in predicates; and wide text columns, which need a full-text or trigram index rather than a b-tree.

**Composite index column order** follows the ESR rule: **Equality columns first, then Sort columns, then Range columns.** A composite index on `(a, b, c)` can serve predicates on `a`, on `(a, b)`, and on `(a, b, c)`, but not on `b` alone — the leftmost-prefix rule. Worked example for `WHERE tenant_id = ? AND status = ? AND created_at > ? ORDER BY created_at DESC`: the correct index is `(tenant_id, status, created_at)`. Putting `created_at` before `status` forces a range scan over a much larger slice and then a filter; putting `status` first makes the index unusable for queries that specify only `tenant_id`. Order the equality columns by selectivity where you have a choice, most selective first.

**Write-amplification cost** is the reason not to index everything: every `INSERT`, `UPDATE` touching an indexed column, and `DELETE` must update every affected index. Each index typically adds roughly 5-15% to write latency, so a table with 10 indexes can be 2x slower to write than the same table with 2, plus the storage cost (often 10-30% of table size per index) and the memory pressure of keeping more index pages hot. Practical ceiling: **keep it under 5-6 indexes per hot transactional table.** Audit with `pg_stat_user_indexes` and drop any index with near-zero `idx_scan` after a full business cycle — unused indexes are common and are pure cost. Prefer one well-ordered composite index over three single-column indexes, and use partial indexes (`WHERE deleted_at IS NULL`) and covering indexes (`INCLUDE`) to cut size and enable index-only scans.

## Soft deletes and audit columns

**Soft delete** marks a row inactive instead of removing it, using a nullable `deleted_at TIMESTAMPTZ` rather than an `is_deleted BOOLEAN` — the timestamp answers "when," supports retention policies, and enables partial indexes.

Use soft deletes when the row is referenced by historical records (an invoice pointing at a deleted product), when users expect undo or a trash view, when regulation or contract requires retention, or when accidental deletion is expensive. Use hard deletes when a legal erasure request applies (GDPR Article 17), for high-volume ephemeral data such as logs and sessions, and for join tables where a soft delete adds no value.

The costs are real and must be handled deliberately:

1. **Every query must filter.** A single forgotten `WHERE deleted_at IS NULL` leaks deleted data. Mitigate by exposing a view (`active_users`) that applies the filter and having application code read only the view, or by using an ORM default scope — and verify the default is applied in raw queries too.
2. **Unique constraints break.** A deleted user's email blocks re-registration. Fix with a partial unique index: `CREATE UNIQUE INDEX ON users (email) WHERE deleted_at IS NULL`.
3. **Tables grow without bound.** Add a purge job that hard-deletes rows soft-deleted more than N days ago (30-90 days is typical) and document the retention window.
4. **Cascades become manual.** Soft-deleting a parent does not soft-delete children; decide explicitly whether children are hidden by the parent's state or need their own marks.

**Audit columns** to include on essentially every table: `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`, `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()` maintained by a trigger rather than application code, `created_by` and `updated_by` as actor IDs, and `deleted_at` plus `deleted_by` where soft deletes apply. Store all timestamps in UTC as `TIMESTAMPTZ` and convert at the presentation layer; storing local times without offsets is an irreversible data-quality mistake. Where regulation requires a full change history, add a separate append-only `*_history` or event table capturing before/after values — audit columns record only the last change and cannot reconstruct a sequence.

## Multi-tenancy isolation models

Three models, in increasing isolation and cost.

**Shared schema with tenant_id.** All tenants share tables; every row carries `tenant_id`, and every query filters on it. Cheapest by far — one schema, one connection pool, one migration run — and scales to hundreds of thousands of tenants. Risk: a single missing `WHERE tenant_id = ?` is a cross-tenant data leak, the most serious bug class in SaaS. Mitigations that must be treated as mandatory: `tenant_id` as the leading column of the primary key or of every composite index; Postgres row-level security with `SET LOCAL app.tenant_id` per request so the database enforces isolation even if application code forgets; a repository layer that cannot construct a query without a tenant scope; and an automated test that asserts cross-tenant reads return 404. Weaknesses: noisy neighbors, no per-tenant restore, and per-tenant data-residency requirements cannot be met.

**Schema per tenant.** One database, one Postgres schema per tenant, identical tables in each. Better isolation and per-tenant backup and restore; queries cannot accidentally cross tenants once the `search_path` is set. Costs: migrations must run N times (at 2,000 tenants, a 30-second migration is 16 hours unless parallelized and batched); connection pooling gets complicated; and Postgres degrades in catalog performance somewhere in the low thousands of schemas. Practical ceiling: roughly 100-1,000 tenants.

**Database per tenant.** Full isolation, per-tenant sizing, per-tenant residency and encryption keys, trivial per-tenant restore and export. Costs are the highest — infrastructure per tenant, N migration targets, and real automation required for provisioning. Fits enterprise products with tens to low hundreds of high-value tenants, or regulated workloads.

Selection heuristics: self-serve or PLG with many small tenants → shared schema. Mid-market with tens to hundreds of tenants and moderate compliance needs → schema per tenant. Enterprise with contractual isolation, residency, or bring-your-own-key requirements → database per tenant. A hybrid is common and sensible: shared schema for the long tail, dedicated databases for the largest accounts. Decide before launch, because migrating between models later means rewriting the data-access layer and moving every row.

## Migration safety for adding a NOT NULL column

Adding a `NOT NULL` column with a default to a large table is the canonical way to take an outage. On Postgres before version 11, `ALTER TABLE ... ADD COLUMN x text NOT NULL DEFAULT 'y'` rewrites every row while holding an `ACCESS EXCLUSIVE` lock — on a 200M-row table that is minutes to hours of total unavailability for that table, and the lock queues behind and ahead of every other query.

Postgres 11+ makes adding a column with a *constant* default metadata-only and fast. But the safe pattern still applies whenever the default is **volatile or computed** (`now()`, `gen_random_uuid()`, a value derived from other columns), on MySQL versions without instant DDL, or when you must backfill values that are not a single constant.

The four-phase expand-and-contract pattern:

**Phase 1 — add nullable.** `ALTER TABLE orders ADD COLUMN channel text;` No default, no NOT NULL. Metadata-only, milliseconds. Deploy.

**Phase 2 — dual write.** Deploy application code that writes `channel` on every insert and update while tolerating NULL on read. Wait until this is fully rolled out; do not proceed while old instances are still serving.

**Phase 3 — backfill in batches.** Update in bounded chunks with a pause between them, never in one statement:

```sql
UPDATE orders SET channel = 'web'
WHERE channel IS NULL AND id IN (
  SELECT id FROM orders WHERE channel IS NULL LIMIT 5000
);
```

Loop until zero rows are affected. Batches of 1,000-10,000 rows with a 100-500ms sleep keep replication lag and lock contention low; monitor replica lag and dead-tuple growth and slow down if either climbs.

**Phase 4 — enforce.** Add the constraint without a full-table exclusive validation. On Postgres, add a `NOT VALID` check constraint, validate it concurrently, then set the column NOT NULL (12+ recognizes the validated check and skips the scan):

```sql
ALTER TABLE orders ADD CONSTRAINT orders_channel_not_null
  CHECK (channel IS NOT NULL) NOT VALID;
ALTER TABLE orders VALIDATE CONSTRAINT orders_channel_not_null;
ALTER TABLE orders ALTER COLUMN channel SET NOT NULL;
```

General migration safety rules: set `lock_timeout` (2-5 seconds) and `statement_timeout` on every DDL session so a migration fails fast instead of queueing behind a long query and blocking all traffic; always use `CREATE INDEX CONCURRENTLY` on large tables and be prepared to drop and retry an invalid index if it fails; never combine a schema change and a code change that depends on it in one deploy; make every migration reversible or explicitly document why it is not; and never rename or drop a column in the same release that stops using it — drop it a release later, after confirming no traffic references it.
