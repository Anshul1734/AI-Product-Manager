---
title: PRD Structure and Review Standards
doc_id: prd-structure
domain: requirements
tags: [requirements, prd, documentation, non-goals, scope]
authority: practice
---

# PRD Structure and Review Standards

A PRD (Product Requirements Document) exists to make a product decision reviewable and to prevent the same questions from being re-answered in Slack for six weeks. It answers what problem we are solving, for whom, what success looks like, what is explicitly out of scope, and what we still do not know. It does not answer how the system will be built — that belongs in a design doc — and it does not enumerate implementation tasks — that belongs in tickets. A PRD is sized to its risk: a two-week enhancement warrants 1-2 pages, a quarter-long initiative warrants 4-6 pages, and anything over 8 pages is almost certainly mixing in design decisions that should have been extracted. The canonical section order below is deliberate: each section constrains the next, so writing them out of order produces documents that argue for a predetermined solution.

## Canonical PRD sections in order

The eight sections, in the order they must appear, because each one constrains the next:

1. **Context and problem.** Who is affected, what they do today, what it costs, and how we know. Quantified, with sources. This is the only section that may be longer than a page.
2. **Goals and non-goals.** Goals are outcomes, not features ("reduce time-to-first-report from 14 minutes to under 3"). Non-goals are explicit exclusions with reasons.
3. **Personas and primary user.** Which 1-3 personas this serves and which one wins when they conflict.
4. **Requirements.** What the system must do, expressed as user-visible behavior and constraints. Grouped by user flow, each item tagged P0/P1/P2, each traceable to a goal.
5. **Success metrics.** Each with baseline, target, timeframe, measurement method, and at least one guardrail metric.
6. **Scope and phasing.** What ships in phase 1 versus later, with the reasoning for the cut line and the launch/rollout plan (flag strategy, percentage ramp, migration).
7. **Open questions.** Unresolved decisions with an owner and a needed-by date on each. An empty open-questions section in a pre-build PRD is a red flag, not a sign of rigor.
8. **Risks and dependencies.** Technical, legal, operational, and organizational risks, each with likelihood, impact, and a named mitigation or trigger.

Ordering rules: never write Requirements before Goals and Non-goals, because requirements written first become the goals by default and the solution space is never examined. Every requirement must map to a goal — an unmappable requirement is either scope creep or a missing goal, and both cases need resolution before the PRD is reviewable.

## Non-goals: the highest-leverage section

Non-goals are the single most valuable section of a PRD and the most frequently omitted. A non-goal is an explicit statement that something a reasonable reader might expect is deliberately out of scope, with the reason. Their function is to make disagreement surface during review, when changing course is free, rather than in week five of implementation.

Write non-goals in the form **"We are not doing X, because Y."** Concrete examples:

- "We are not supporting custom SQL in v1, because 90% of exports in the last quarter matched one of six preset shapes and a query builder adds an estimated 6 engineer-weeks plus an ongoing query-cost surface."
- "We are not building mobile layouts, because 97% of sessions for this workflow are desktop and the affected persona works at a laptop during month-end close."
- "We are not migrating historical data older than 24 months, because the backfill is 40 hours of compute and only 3% of queries reach beyond 24 months."
- "We are not solving multi-currency, because it requires an FX-rate source and a finance review; tracked as a separate initiative for Q4."

Four rules. First, non-goals must be **plausible** — "we are not adding a blockchain" is noise; a good non-goal is something a stakeholder actually asked for or would assume is included. Second, each needs a **reason with a number or a dependency**, not a preference. Third, distinguish **"not now"** (with the tracking link) from **"not ever"** (with the strategic reason); conflating them creates false hope and repeated re-litigation. Fourth, aim for **5-10 non-goals** on a substantial PRD — fewer than 3 means the author has not stress-tested the scope.

The diagnostic value is high: if reviewers argue about a non-goal, you have found a genuine misalignment for the cost of one sentence. If a non-goal has to be reversed mid-build, that reversal is now a visible, discussable scope change rather than silent creep.

## Writing the requirements section

Requirements state user-visible behavior and constraints, not implementation. "The system must return search results within 500ms at p95 for result sets under 10,000 rows" is a requirement; "the system will use an Elasticsearch cluster" is a design decision and belongs in the design doc.

Structure requirements by user flow, in the order the user encounters them, and tag priority:

- **P0** — release-blocking; without it the release does not ship.
- **P1** — ships in the release but a defect here does not block launch; degradable.
- **P2** — ships if capacity allows; the contingency pool.

Include four categories that teams routinely omit, each of which becomes a production incident when missing:

1. **Empty, loading, and error states** for every new surface. Name the copy or link the design.
2. **Permissions and visibility.** Which roles can see and do what; what happens on downgrade.
3. **Limits and quotas.** Maximum rows, file size, rate, retention. State an actual number — "up to 50,000 rows per export; requests above that are rejected with a message directing users to the API."
4. **Non-functional constraints.** Latency at p50/p95, availability target, data-residency and compliance requirements, accessibility level (e.g. WCAG 2.1 AA), and browser/device support.

Each requirement should be independently testable and traceable. A practical format is a numbered table with columns: ID, requirement, priority, goal it serves, and open questions. The IDs matter — tickets and test cases reference them, and traceability from requirement to ticket to test is what lets you answer "is this actually done?" without a meeting. Avoid the words "support," "handle," "robust," and "seamless"; each hides an unspecified decision that engineering will resolve by guessing.

## PRD reviewability checklist

A PRD is reviewable when a competent reader who was not in any prior meeting can (a) disagree with a specific claim and (b) build the right thing from it. Run this checklist before circulating:

- [ ] The problem is quantified with a population, a cost, and a cited source (not "customers have asked").
- [ ] Every goal is an outcome with a number, not a feature name.
- [ ] There are at least 3 non-goals, each with a reason and each plausible.
- [ ] Every requirement maps to a stated goal; no orphans.
- [ ] Every requirement is testable — a QA engineer could write a pass/fail case from it without asking a question.
- [ ] Each success metric has baseline, target, timeframe, and measurement method.
- [ ] At least one guardrail/counter-metric is defined for the primary metric.
- [ ] Empty, loading, error, and permission-denied states are specified for every new surface.
- [ ] Limits and quotas have actual numbers.
- [ ] Non-functional requirements state latency percentiles, availability, accessibility level, and browser support.
- [ ] Phasing has a stated cut line with reasoning, and a rollout mechanism (flag, ramp percentages, kill switch).
- [ ] Every open question has a named owner and a needed-by date.
- [ ] Each risk has likelihood, impact, and a mitigation or trigger.
- [ ] No implementation choices (database, framework, service topology) appear anywhere.
- [ ] A reader can identify the primary persona and what happens when personas conflict.

Two review mechanics that raise quality more than any template change. Circulate for **asynchronous written comments 48 hours before any meeting**, and hold the meeting only on unresolved comments. And require an explicit **engineering feasibility pass** before sign-off — an engineer reads for hidden complexity and flags requirements whose cost is 5-10x what the PM likely assumes, which is where most schedule misses originate.

## PRD versus design doc versus ticket

Three documents, three audiences, three questions. Putting content in the wrong one is the most common documentation failure, and it costs real time because the wrong reviewers get pulled in.

| | PRD | Design doc (TDD/RFC) | Ticket |
|---|---|---|---|
| **Question** | What problem, for whom, what success? | How will we build it, and what did we reject? | What exactly do I do next? |
| **Owner** | PM | Tech lead / engineer | Engineer or PM |
| **Audience** | Eng, design, leadership, GTM, support | Engineers, architects, security | The person doing the work |
| **Lifespan** | Stable through the initiative | Stable through implementation, then archived | Days |
| **Contains** | Problem, goals, non-goals, requirements, metrics, phasing, risks | Architecture, data model, API contracts, alternatives considered, migration plan, failure modes, rollback | One story, acceptance criteria, test notes, links |
| **Length** | 1-6 pages | 2-10 pages | Under a page |

Concrete allocation for one feature, scheduled report delivery:

- **PRD:** "Users can have a saved report emailed on a recurring schedule. Success: 25% of the 340 heavy-export accounts create a schedule within 60 days; manual export volume in that segment drops 40%. Non-goal: no Slack or webhook delivery in v1."
- **Design doc:** "Schedules stored in `report_schedules` with a `next_run_at` index; a Celery beat job polls every 60s; idempotency via a `(schedule_id, run_date)` unique key; rejected alternative: cron-per-schedule, because it does not survive pod rescheduling."
- **Ticket:** "Add `POST /v1/report-schedules` accepting cron expression and recipient list; validate max 20 recipients; return 201 with the created object; 422 on invalid cron. AC in Gherkin."

The reliable test: if changing the content would change *what users experience*, it is PRD. If it would change *how the system works* without changing user-visible behavior, it is design doc. If it is a unit of work someone picks up this week, it is a ticket.
