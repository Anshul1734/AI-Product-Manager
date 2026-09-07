---
title: Architecture Patterns and Selection Criteria
doc_id: architecture-patterns
domain: architecture
tags: [architecture, microservices, monolith, serverless, event-driven]
authority: pattern
---

# Architecture Patterns and Selection Criteria

Architecture selection is a bet about organizational scale, not a technical taste question. The five patterns below — monolith, modular monolith, microservices, serverless, and event-driven — differ mainly in where they put boundaries and therefore in what kind of change is cheap. The dominant cost in a distributed system is not compute; it is the operational and cognitive overhead of network boundaries: partial failure, distributed tracing, schema evolution across services, data consistency, and per-service deployment infrastructure. That overhead is worth paying when independent team deployment becomes the binding constraint, and is pure waste before then. The core guidance in this document is deliberate and opinionated: **greenfield products with engineering teams under roughly 15 people should default to a modular monolith**, and services should be extracted only against the specific signals listed below.

## Monolith

A monolith is a single deployable unit containing all application code, typically talking to one database, with in-process function calls between all components.

**When it fits:** teams of 1-8 engineers; pre-product-market-fit products where the domain model changes weekly; internal tools; anything where the cost of a wrong boundary exceeds the cost of coupling. A monolith remains viable well past the point most teams abandon it — Shopify, Basecamp, and Stack Overflow have all run enormous monoliths successfully.

**Preconditions:** almost none. One CI pipeline, one deploy target, one database. This is the point — a monolith requires the least operational maturity of any pattern, needing no service mesh, no distributed tracing, and no per-service on-call.

**Failure modes:** without internal discipline, a monolith degrades into a big ball of mud — everything imports everything, tests take 40 minutes, and any change risks any feature. Coupled deploys mean one team's bad merge blocks everyone. Scaling is all-or-nothing: a CPU-heavy report generator forces you to scale the whole application. Build and test times grow superlinearly with code size and eventually dominate cycle time.

**Cost and latency profile:** the cheapest and fastest option. In-process calls cost nanoseconds versus 0.5-5ms per network hop. A single application server plus one managed database runs from tens to a few hundred dollars a month at low scale. Debugging is a single stack trace, and a local development environment is one process.

**Migration path:** a monolith with disciplined internal module boundaries *is* a modular monolith, which is why the modular version should be the starting point — retrofitting boundaries later is the expensive part.

## Modular monolith

A modular monolith is a single deployable unit with enforced internal module boundaries: each module owns its data tables, exposes an explicit public interface, and may not reach into another module's internals or tables. Communication is in-process calls through those interfaces, or an in-process event bus.

**When it fits:** this is the correct default for greenfield products and for teams under roughly 15 engineers. It buys the deployment and debugging simplicity of a monolith while preserving the option to extract services later, because the boundaries you would cut along already exist.

**Preconditions:** boundary enforcement must be mechanical, not cultural. Concretely: one schema or table-prefix per module with no cross-module foreign keys or joins; a lint or import-check rule in CI that fails builds on illegal imports (ArchUnit for Java, import-linter for Python, dependency-cruiser or ESLint boundaries for TypeScript, Go's internal packages); and a module ownership file. Without CI enforcement the boundaries erode within two quarters.

**Failure modes:** boundaries drawn along technical layers (controllers, services, repositories) instead of business capabilities (billing, identity, reporting) — layered "modules" provide none of the extraction benefit. Shared mutable database tables that quietly recouple modules. A single module accreting most of the logic because nobody owns the boundary decisions.

**Cost and latency profile:** identical to a monolith — in-process calls, one deploy, one database instance, one on-call rotation. The only added cost is the up-front design work of defining boundaries and the CI rules that enforce them, typically a few days of work.

**Practical guidance:** define modules around business capabilities, aim for 5-12 modules at the start, and treat each module's public interface as if it were already a network API — same-shaped requests and responses, no shared objects with internal state. That discipline makes later extraction a mechanical change rather than a rewrite.

## Microservices

Microservices decompose a system into independently deployable services, each owning its data, communicating over the network via HTTP/gRPC or asynchronous messaging.

**When it fits:** organizations above roughly 30-50 engineers where independent deployment has become the binding constraint on delivery speed; genuinely divergent scaling profiles (a video transcoder that needs GPUs alongside a CRUD API); strict isolation requirements such as a PCI or PHI boundary; and acquisitions or platforms with independent release cadences.

**Preconditions — all of them, not a subset:** automated CI/CD per service; centralized structured logging and distributed tracing (OpenTelemetry or equivalent); service-level SLOs and per-service on-call; infrastructure as code and a container orchestrator; a schema-evolution and contract-testing discipline; and a team topology where each service has exactly one owning team. Rule of thumb: you need at least one team of 4-8 engineers per 3-5 services, plus a platform team of 3+ once you exceed roughly 15 services. Adopting microservices without these preconditions produces a distributed monolith — the coupling of a monolith with the operational cost of distribution, which is the worst outcome available.

**Failure modes:** the distributed monolith (services that must be deployed together); chatty call graphs where one user request fans out to 15 synchronous hops, multiplying latency and making availability the product of many nines; distributed transactions across service boundaries, requiring sagas and compensating actions; shared databases that defeat the isolation; and cascading failures without circuit breakers, timeouts, and bulkheads.

**Cost and latency profile:** each synchronous hop adds roughly 0.5-5ms in-region plus serialization; a 5-hop chain turns a 20ms monolith request into 60-120ms. Infrastructure cost typically runs 2-4x a monolith at equivalent traffic because of per-service redundancy, sidecars, and observability pipelines. The dominant cost is engineering time on platform work, commonly 15-25% of total engineering capacity.

## Serverless

Serverless (FaaS plus managed backing services) runs code in ephemeral, event-triggered, per-request-billed compute — AWS Lambda, Cloud Functions, Cloud Run, Vercel Functions — with no server management.

**When it fits:** spiky or unpredictable traffic; event-driven glue and data pipelines; scheduled jobs; webhook receivers; low-traffic products where paying for idle servers is the main cost; and small teams with no operations capacity. Serverless is excellent for workloads with high variance and a low duty cycle.

**Preconditions:** stateless request handling; managed state elsewhere (DynamoDB, S3, a serverless Postgres or a pooled connection proxy); tolerance for cold starts; and an execution profile inside platform limits. Know the numbers: typical execution time limits of 15 minutes, payload limits around 6MB synchronous and 256KB asynchronous on Lambda, and cold starts of roughly 100-400ms for a small Node or Python function and 1-3+ seconds for a JVM or heavy dependency tree.

**Failure modes:** cold-start latency on user-facing paths; connection exhaustion against traditional relational databases because each concurrent invocation opens a connection (mitigate with RDS Proxy, PgBouncer, or a data API); vendor coupling that makes migration expensive; cost inversion at sustained high traffic, where always-on containers become cheaper; a hard 15-minute ceiling that forces long jobs into step functions or queues; and local development and integration testing that are materially harder than for a monolith.

**Cost and latency profile:** effectively zero cost at zero traffic; roughly $0.20 per million requests plus GB-second compute on major clouds. The crossover point where a container becomes cheaper is typically around 25-40% sustained CPU utilization — as a rough anchor, a service handling steady traffic above a few hundred requests per second is usually cheaper on always-on compute. Latency is fine at p50 for warm functions but cold starts show up at p95-p99, which is why user-facing interactive paths with a p95 latency budget under 200ms are a poor fit unless you pay for provisioned concurrency.

## Event-driven architecture

Event-driven architecture has components communicate by publishing immutable events to a broker (Kafka, Pulsar, SNS/SQS, RabbitMQ) that other components consume asynchronously, rather than by calling each other directly.

**When it fits:** workflows with multiple independent downstream consumers of the same fact (an `order.placed` event feeding fulfillment, billing, analytics, and email); temporal decoupling where the producer must not block on slow consumers; audit and replay requirements; and integration across systems with different availability. Event-driven communication also pairs naturally with microservices as the way to avoid synchronous fan-out.

**Preconditions:** a schema registry and an explicit event-versioning policy; idempotent consumers, because at-least-once delivery means duplicates are guaranteed, not hypothetical; dead-letter queues with a monitored redrive process; consumer-lag monitoring and alerting; and organizational tolerance for eventual consistency, including UI patterns that show pending states. Teams also need distributed tracing that propagates correlation IDs through the broker, or debugging becomes guesswork.

**Failure modes:** eventual-consistency bugs where a user writes and immediately reads stale data; event storms and unbounded retry loops; the "event as command" anti-pattern, where a supposed event is really a disguised RPC and reintroduces tight coupling; schema evolution breaking consumers silently; missing idempotency causing duplicate charges or duplicate emails; and debugging difficulty because there is no single call stack. Out-of-order delivery is the norm outside a single partition key, so consumers must be order-tolerant or partitioned by entity ID.

**Cost and latency profile:** end-to-end latency is typically 10-500ms depending on broker and batching, so the pattern is unsuitable for synchronous read paths. A managed Kafka cluster starts around a few hundred dollars a month; SQS is roughly $0.40 per million requests. Throughput scales very well — a modest Kafka cluster handles hundreds of thousands of events per second — but each new event type carries a persistent schema-governance cost.

## When to extract a service from a monolith

Extract a service only against concrete, observable signals. Any one of these justifies a candidate extraction; a vague desire for "scalability" does not.

1. **Deployment contention.** Two or more teams block each other on releases, or deploy frequency has fallen because the blast radius is too large. Measured signal: rollbacks caused by unrelated changes, or a queue of waiting merges.
2. **Divergent scaling profile.** One component consumes disproportionate resources or needs different hardware — GPU inference, memory-heavy report generation, a 100x-traffic public endpoint. Measured signal: you are scaling the whole fleet for one component's peak.
3. **Divergent availability or isolation requirement.** A component must survive when the rest is down (status page, webhook ingestion), or must sit inside a compliance boundary (PCI cardholder data, PHI).
4. **Different technology is genuinely required.** A workload needs a runtime the monolith cannot host — a Rust encoder, a Python ML stack in a Node shop. "We prefer Go" is not this signal.
5. **A stable, well-exercised module boundary.** The module has had a clean public interface for 3+ months, low change coupling with other modules, and its own tables with no cross-module joins. If the boundary is still moving, extraction locks in a wrong boundary at network cost.
6. **Independent team ownership exists.** There is a specific team of 4+ engineers who will own the service, its on-call, and its SLO. A service with no owning team becomes shared infrastructure nobody maintains.

Counter-signals that should stop an extraction: the boundary has changed in the last quarter; the proposed service would require synchronous calls back into the monolith on the same request path (a strong sign the boundary is wrong); the team has no distributed tracing or per-service CI; or the module's data cannot be separated without a distributed transaction. Preferred sequence: enforce the module boundary in the monolith first, run it that way for a quarter, then extract — and extract one service at a time, keeping the monolith as the system of record until the new service's SLOs hold.
