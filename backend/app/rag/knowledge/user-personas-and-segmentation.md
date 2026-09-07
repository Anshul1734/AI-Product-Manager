---
title: User Personas and Segmentation
doc_id: user-personas-and-segmentation
domain: discovery
tags: [discovery, personas, segmentation, research, users]
authority: practice
---

# User Personas and Segmentation

A persona is a decision-making tool, not a marketing artifact. Its job is to settle recurring arguments — which workflow to optimize, what default to pick, which error message to write, what to cut — by making a specific user's context concrete enough that the answer becomes obvious. Personas fail when they collect demographics nobody uses ("Sarah, 34, enjoys yoga and podcasts") instead of behavior, workarounds, and constraints that change design decisions. The test for any persona field is blunt: name a product decision this field would change. If you cannot, delete the field. This document covers proto-personas versus research-backed personas, the fields that earn their place, behavioral versus demographic segmentation, and the persona-bloat anti-pattern with a hard cap.

## Proto-personas versus research-backed personas

**Proto-personas** are hypotheses built from what the team already believes — support tickets, sales calls, analytics, and internal experience — in a 2-4 hour workshop, with zero new research. They are legitimate and useful, on two conditions: every claim is labeled as an assumption, and the riskiest assumptions are listed as research questions. A proto-persona's real output is a prioritized list of what you do not know.

**Research-backed personas** are built from primary evidence: 8-15 interviews per hypothesized segment (saturation — the point where new interviews stop producing new pain points — typically arrives around interview 8-12), plus behavioral analytics to size each segment, plus optionally a survey (n≥150) to validate that segment boundaries hold at scale.

| Dimension | Proto-persona | Research-backed persona |
|---|---|---|
| Cost | 2-4 hours | 3-6 weeks |
| Evidence | Team belief, existing tickets/analytics | 8-15 interviews per segment + analytics + survey |
| Confidence label | "Assumption" | "Validated, n=12, Mar 2026" |
| Valid use | Early exploration, framing research, week-one alignment | Roadmap commitments, pricing, positioning |
| Refresh cadence | Every new initiative | Every 12-18 months, or after a major segment shift |

The operational rule: **never let a proto-persona quietly become a research-backed persona.** Put the evidence label directly in the document header — "PROTO — unvalidated, created 2026-02-11" or "VALIDATED — 12 interviews, analytics n=4,200, updated 2026-06-03." Personas that lose their provenance become organizational folklore that outlives the market they described, and teams then defend design decisions with a fictional person nobody has met.

## Fields a useful persona carries

A persona should fit on one page and carry only fields that change decisions. The required set:

- **Context / trigger:** when and where this person engages, and what prompts it. "Opens the tool Monday 8-10am and at month-end close; often interrupted, works on a 13-inch laptop in a shared office." Drives session-length assumptions, notification design, save/resume behavior, and information density.
- **Current workaround:** exactly what they do today, tool by tool. "Exports CSV, pivots in Excel, pastes a screenshot into Slack." This is the most valuable field in the document — it defines the real competitor and the migration path, and it is the field most often omitted.
- **Pain points with severity:** each pain rated by cost and frequency, e.g. "rebuilds the same pivot 4x/month, ~30 min each (12 hrs/quarter)" and "cannot tell whether data is stale — has sent wrong numbers to a VP twice." Unrated pain lists cannot be prioritized.
- **Success definition:** what "done well" means in this person's words, ideally quantified. "I can answer the VP's question in under 2 minutes without opening Excel."
- **Technical fluency:** concrete, not a label. "Writes Excel formulas and VLOOKUPs; will not write SQL; has never used an API; uses keyboard shortcuts heavily." Directly determines whether you ship a query builder or a set of preset views.
- **Authority and constraints:** what they can decide alone versus what needs approval; procurement, security review, or budget limits. Critical in B2B, where the user and the buyer differ.
- **Segment size:** how many real accounts or users this persona represents, with the source. A persona without a size cannot be traded off against another.

Fields to omit unless they demonstrably change a decision: age, gender, family status, hobbies, stock photo, invented backstory. Age matters if you are designing for accessibility thresholds; it does not matter because it makes the persona "feel real."

## Behavioral versus demographic segmentation

**Demographic and firmographic segmentation** groups users by attributes: age, region, job title, company size, industry, plan tier. It is easy to obtain and necessary for targeting, quota setting, and compliance scoping.

**Behavioral segmentation** groups users by what they do: features used, frequency, workflow shape, integration footprint, data volume, collaboration pattern. It is harder to obtain and far more predictive of product needs.

Behavioral segmentation wins for product decisions because behavior is causal to need while demographics are merely correlated. Two accounts both labeled "mid-market SaaS, 200 employees" can be a 3-seat team running one weekly report and a 40-seat team running 600 API calls a day; they need different products. Conversely, a 12-person agency and a 4,000-person bank can share the same behavioral segment — "runs the same reconciliation every month-end, exports to a spreadsheet, never uses the API" — and be served by one design.

Practical construction: pick 2-4 behavioral axes that are instrumented and observable, then cut the population and check whether the segments differ on retention, expansion, or support load. Useful axes are frequency of the core action (daily / weekly / monthly / dormant), breadth (number of distinct features used per month), depth (records or events processed), and collaboration (single-player versus multi-seat). A segmentation is worth keeping only if segments differ materially — a common threshold is a ≥1.5x gap in retention or ARPU between segments. If retention is flat across your cut, the cut is not real; try another axis.

Combine them in one direction only: define segments behaviorally, then describe each segment demographically so marketing and sales can find them. Never the reverse.

## Persona bloat anti-pattern

Persona bloat is the accumulation of personas until none of them constrains a decision. It follows a predictable path: a team starts with 3, adds one per stakeholder request, reaches 9-12, and then designs for the union of all of them — which is designing for nobody. The symptom is a feature set where every path is half-optimized and the primary workflow requires more clicks each release.

**The cap: 3-4 primary personas maximum, and exactly one designated primary.** The primary persona is the one whose experience you optimize when two personas conflict, and that conflict-resolution rule is the reason the designation exists. Secondary personas are served as long as serving them does not degrade the primary's experience. Anti-personas — users you explicitly choose not to serve — are worth naming; "solo freelancers on free plans" as an anti-persona kills a whole class of feature requests cheaply.

Rules to hold the cap:

1. **Merge on shared jobs, not shared job titles.** If two personas have the same trigger, workaround, and success definition, they are one persona with two titles.
2. **Require a size and a decision delta to add one.** A new persona must represent a named share of users and at least one product decision that would differ. Without both, it is a variation of an existing persona.
3. **Distinguish personas from roles.** Admin, member, and viewer are permission roles, not personas. Modeling roles as personas is the fastest route to bloat in B2B.
4. **Retire on a schedule.** Review the set every 12-18 months and delete any persona that has not been cited in a decision document in that period.

The failure the cap prevents is real and expensive: with 9 personas, "which one does this serve?" always has a yes answer, so the persona set stops filtering anything and the roadmap loses its only user-grounded constraint.
