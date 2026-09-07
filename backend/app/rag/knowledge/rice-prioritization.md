---
title: RICE Prioritization Framework
doc_id: rice-prioritization
domain: prioritization
tags: [prioritization, scoring, roadmap, rice, tradeoffs]
authority: framework
---

# RICE Prioritization Framework

RICE is a quantitative scoring model created at Intercom for ranking candidate features and initiatives on a single comparable axis. The RICE score is computed as `(Reach × Impact × Confidence) / Effort`. Reach is counted in users or events per time period, Impact is a bounded ordinal multiplier, Confidence is a percentage discount for evidence quality, and Effort is person-months. The output unit is "impact per person-month," which makes RICE a throughput-of-value metric rather than a value metric — a small feature that helps many users beats a large feature that helps a few. RICE is most useful when a team has 10-40 candidate items of comparable type and needs to defend an ordering to stakeholders. It is a poor fit for strategic bets, compliance work, and platform migrations, where the correct answer is not a function of near-term reach.

## Reach in RICE

Reach in RICE is the number of distinct people or events the initiative touches within a fixed, explicitly stated time window — almost always one quarter. Write it as "1,200 users per quarter," never as "lots of users" or a percentage. Source Reach from product analytics, not from intuition: count the users who currently hit the funnel step, screen, or API endpoint the change affects. If the feature targets a new behavior with no existing traffic, derive Reach from the nearest observable proxy and label it as such — for example, "3,400 accounts opened the billing page last quarter; we estimate 40% would use scheduled invoicing, so Reach = 1,360."

Three rules keep Reach honest. First, use the same time window for every item in the comparison set; mixing monthly and quarterly Reach silently inflates items by 3x. Second, count only users who reach the change, not total registered users — a setting buried three clicks deep in an admin panel used by 5% of accounts has a Reach of 5% of accounts, not 100%. Third, for internal tooling, Reach is the number of task executions per quarter (e.g., "support agents handle 8,000 refund tickets per quarter"), because the value scales with events rather than headcount.

The dominant RICE failure mode is inflated Reach: teams substitute total addressable users for actually-affected users. A Reach number that is not traceable to a query, dashboard, or documented funnel step should be treated as unverified and the item's Confidence dropped to 50% or below.

## Impact scale in RICE

Impact in RICE is a bounded multiplier capturing how much the initiative moves the target outcome per person reached. The standard scale is fixed and must not be extended:

| Impact | Multiplier | Meaning |
|---|---|---|
| Massive | 3 | Transforms the core workflow for reached users |
| High | 2 | Clear, obvious improvement users would name unprompted |
| Medium | 1 | Noticeable improvement, the default assumption |
| Low | 0.5 | Marginal; users would not mention it |
| Minimal | 0.25 | Barely perceptible; polish |

The scale is deliberately coarse because Impact is an estimate, and a five-point ordinal scale communicates that uncertainty better than a 1-100 score. Anchor Impact to a named metric before assigning it: "Impact = 2 because it removes the two-step CSV export that we believe drives the 18% drop-off at the reporting step." If the team cannot name the metric the Impact acts on, the item is not ready to score.

Two disciplines matter. First, cap Impact at 3 — teams that allow 5 or 10 create an arms race where every pet project becomes "transformational." Second, resist assigning 3 to more than roughly 10% of a backlog; if a third of your items are massive, the scale has lost resolution and the ordering it produces is noise. When two items tie on Impact, break the tie with Confidence and Effort rather than inventing intermediate values like 2.5.

## Confidence in RICE

Confidence in RICE is a percentage that discounts the Reach and Impact estimates by the strength of the evidence behind them. It is a hedge against optimism, not a measure of how much the team likes the idea. Use three tiers and avoid values in between:

- **100% (high confidence):** Reach comes from instrumented analytics, and Impact is supported by a completed A/B test, a shipped comparable feature, or quantified user research (e.g., 30+ interviews or a survey with n>200).
- **80% (medium confidence):** Reach is from analytics but Impact is inferred from qualitative research, sales-loss data, or a strong analogous feature. This is the honest default for well-researched work.
- **50% (low confidence):** Either Reach or Impact is a guess, the feature creates a new behavior with no baseline, or the estimate rests on a single loud customer.

Anything below 50% should not be scored — it should be converted into a research spike or prototype whose only job is to raise Confidence. Write the spike as its own backlog item with a defined output.

The classic pathology is confidence theater: teams assign 80% or 100% by default because low numbers feel like admitting weakness, which collapses Confidence into a constant and removes it from the ranking entirely. Audit this by checking the distribution — a healthy backlog has a real spread across 50/80/100. Require every 100% to cite the specific artifact (dashboard link, experiment ID, research doc) in the scoring sheet; if the citation is missing, the value drops to 80%.

## Effort in RICE

Effort in RICE is total person-months of work across every discipline required to ship, including design, engineering, data, QA, and any material PM or go-to-market load. A feature needing 3 engineer-weeks, 1 designer-week, and 1 QA-week is 5 person-weeks, or roughly 1.25 person-months at 4 weeks per month. Round to halves (0.5, 1, 1.5, 2); precision beyond that is false.

Effort must include the work teams habitually omit: migrations and backfills, feature-flag plumbing, analytics instrumentation, documentation, support enablement, and the removal of the old path. A rule of thumb from delivery data: for user-facing features in a mature codebase, non-coding overhead runs 25-40% of coding effort, so add a 1.3x multiplier to a pure-engineering guess unless the omitted work is explicitly enumerated.

Ignoring Effort uncertainty is the third major RICE failure mode. Because Effort sits in the denominator, an error there distorts the score more than an equivalent error in Reach or Impact — halving Effort doubles the score. Mitigate this by scoring Effort at the pessimistic end of the team's range rather than the median, and by capping any single item at 3 person-months for scoring purposes. Items larger than 3 person-months should be decomposed into phases and each phase scored separately; otherwise a large item's score is dominated by unmodeled risk. When Effort is truly unknown, run a timeboxed 2-3 day spike before scoring.

## Worked RICE example

Three candidates for a B2B analytics product, one quarter, same team:

| Feature | Reach (users/qtr) | Impact | Confidence | Effort (person-months) | RICE score |
|---|---|---|---|---|---|
| Saved dashboard filters | 4,200 | 1 | 80% | 1.5 | 2,240 |
| SSO via SAML | 350 | 3 | 100% | 4.0 | 262 |
| CSV export scheduling | 1,360 | 2 | 50% | 2.0 | 680 |

The arithmetic: saved filters = (4,200 × 1 × 0.8) / 1.5 = 2,240. SAML SSO = (350 × 3 × 1.0) / 4.0 = 262. Scheduled export = (1,360 × 2 × 0.5) / 2.0 = 680.

The ranking is filters > scheduled export > SSO, and the example shows exactly where RICE must not be obeyed blindly. SAML SSO scores lowest because Reach counts only the 350 users at enterprise accounts, yet it may be a deal-blocker gating $2M of pipeline — value RICE cannot see. This is why RICE should rank items within a strategic bucket, with revenue-gating and compliance work handled as a separate, protected allocation (a common split is 60% RICE-ranked discretionary work, 25% strategic/gating commitments, 15% technical health).

Note also the leverage of Confidence on scheduled export: raising Confidence from 50% to 100% via five customer interviews would double its score to 1,360 and still leave it second. That tells you the research is not decision-changing and can be skipped — a useful secondary output of running the numbers.

## RICE failure modes and guardrails

RICE fails predictably in five ways, each with a specific guardrail.

1. **Inflated Reach.** Teams cite total users instead of affected users. Guardrail: require a query, dashboard link, or funnel step for every Reach number; unsourced Reach forces Confidence to 50%.
2. **Confidence theater.** Everything is scored 80-100%, neutralizing the term. Guardrail: audit the distribution quarterly and require a cited artifact for every 100%.
3. **Ignored Effort uncertainty.** Effort in the denominator makes optimism doubly damaging. Guardrail: score Effort pessimistically, cap scored items at 3 person-months, and decompose anything larger.
4. **Score laundering.** Stakeholders reverse-engineer inputs to reach a predetermined rank. Guardrail: have Reach and Impact set by different people than the requester, and freeze inputs before scores are computed and revealed.
5. **Category error.** Compliance, security, platform migrations, and strategic bets have low Reach and lose every time, so teams inflate their inputs to compete. Guardrail: exclude them from RICE and fund them from a separate budget line.

Two operating rules. Treat RICE scores as tiers, not a strict ordering: differences under roughly 20% are inside the noise floor and should be broken by sequencing logic, dependencies, or team context, not by decimal places. And re-score at most quarterly — RICE is a communication and forcing device for surfacing disagreement about Reach and Impact, and its main value is the argument it provokes, not the number it emits.
