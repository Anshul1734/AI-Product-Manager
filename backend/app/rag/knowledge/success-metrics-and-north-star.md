---
title: Success Metrics, North Star, and HEART
doc_id: success-metrics-and-north-star
domain: metrics
tags: [metrics, north-star, heart, guardrails, measurement]
authority: framework
---

# Success Metrics, North Star, and HEART

Metrics exist to make a team's beliefs about value falsifiable and to detect when shipping stops working. A metrics system needs four layers: one North Star that expresses delivered customer value, a small set of input metrics that the team can actually move, guardrail metrics that catch damage the North Star hides, and per-initiative targets written with a baseline, a target, a timeframe, and a measurement method. Teams fail at metrics in three predictable ways — choosing a vanity North Star (registered users, page views) that rises while the business decays, tracking 40 metrics so none of them drive a decision, and writing targets like "improve engagement" that cannot be evaluated after launch. This document covers North Star selection, HEART paired with Goals-Signals-Metrics, leading versus lagging indicators, counter-metrics, and the format for a measurable target.

## North Star metric selection criteria

A North Star metric is the single measure that best represents the value customers receive from the product, and which the company believes predicts long-term revenue. Good examples by product type: Airbnb — nights booked; Slack — messages sent within teams of 3+; Spotify — time spent listening; Zoom — weekly hosted meeting minutes; a B2B analytics tool — weekly reports delivered to a human recipient.

Five selection criteria, all of which must hold:

1. **Expresses customer value received, not company value extracted.** Revenue is a result, not a North Star; "nights booked" is value delivered.
2. **Movable by the product team.** If the metric only responds to pricing or enterprise sales, it is a business KPI, not a product North Star.
3. **Leading, not trailing.** It should change before revenue changes, giving the team time to react.
4. **Sensitive but not jumpy.** It should move measurably within one to two quarters of good product work, and not swing 30% on a marketing campaign.
5. **Decomposable into 3-5 input metrics** the team can own directly. This is the criterion most often skipped, and without it the North Star is undirectable.

Test the candidate with the retention correlation check: cohort users by the metric and confirm that high-metric cohorts retain materially better — a useful bar is ≥1.5x 90-day retention versus low-metric cohorts. If retention does not differ, the metric is not measuring value.

Rejected candidates and why: registered users (counts intent, not value), DAU alone (a dark pattern can raise it while satisfaction falls), page views (rewards inefficiency — more views can mean users cannot find things), NPS (a sentiment survey with sample bias, useful as a supporting signal but too slow and noisy to steer a roadmap). Aim for a North Star with a **usage qualifier** that encodes quality: "weekly reports delivered to a human recipient" excludes bot traffic and abandoned schedules in a way that "reports generated" does not.

## HEART framework with Goals-Signals-Metrics

HEART, from Google's research team, gives five categories to ensure a metric set covers user experience rather than only volume:

- **Happiness** — attitudinal satisfaction. Measured by in-product surveys, CSAT, task-level "was this helpful," or SUS scores.
- **Engagement** — depth and frequency of voluntary interaction per user. Actions per active user per week, session depth. Never total volume, which conflates growth with engagement.
- **Adoption** — new users taking up the product or a new feature within a defined window. "Percentage of eligible accounts that create their first schedule within 14 days."
- **Retention** — users returning over a period. Cohort-based: week-4 or day-30 retention, or logo/seat retention in B2B.
- **Task success** — efficiency and effectiveness of a specific task. Completion rate, time on task, error rate.

HEART is only useful when paired with **Goals-Signals-Metrics (GSM)**, which is the mechanism that converts a category into a number:

- **Goal:** what success means in words for this category.
- **Signal:** the observable user behavior that would indicate movement toward the goal.
- **Metric:** the precise, instrumented number derived from the signal, with its definition.

Worked GSM for the Task success row of a report-scheduling feature: **Goal** — analysts get their numbers without manual work. **Signal** — a user creates a schedule and it delivers successfully, and their manual export count drops. **Metric** — "percentage of created schedules with ≥3 consecutive successful deliveries within 21 days (target 85%)" plus "median manual exports per scheduling account per month (baseline 4.2, target <1.0)."

Two practical rules: you do not need all five HEART rows for every feature — pick the 2-3 categories the feature actually targets and leave the others blank rather than inventing metrics. And cap the total tracked set at roughly 5-8 metrics per initiative; beyond that no one reads the dashboard.

## Leading versus lagging indicators

**Lagging indicators** confirm outcomes after they are largely determined: revenue, churn, annual retention, NPS, expansion ARR. They are trustworthy and slow — a churn number for a cohort is only complete months after the product change that caused it.

**Leading indicators** move early and predict the lagging metric: activation rate within 7 days, time-to-first-value, week-1 feature adoption, support-ticket rate per 100 accounts, percentage of accounts reaching a habit threshold.

The discipline is to pair every lagging metric with 2-3 leading indicators that have a demonstrated statistical relationship to it, and then to steer weekly on the leading ones. Concretely, if 90-day logo churn is the lagging metric, the leading set might be "percentage of new accounts that complete setup within 7 days," "percentage reaching 3 active users within 30 days," and "median days to first delivered report." Validate the link before trusting it: cohort the data and check that accounts crossing the leading threshold churn materially less (for example, 2.1% versus 6.8% quarterly).

Timing expectations to plan around: leading indicators respond in 1-4 weeks after a launch, mid-funnel metrics like 30-day retention in 1-2 months, and lagging metrics like annual net revenue retention in 6-12 months. This is why judging a launch on revenue at week two is meaningless and why a team with only lagging metrics cannot iterate — the feedback arrives after the next three decisions have already been made.

The trap to avoid is a leading indicator with no causal validation, which becomes a proxy the team optimizes while the lagging metric stays flat. Re-verify the correlation every two or three quarters; product changes can break the relationship, and the classic failure is continuing to chase an activation step that has stopped predicting retention.

## Counter-metrics and guardrails

A counter-metric (or guardrail) is a metric you commit to *not* degrading, chosen specifically to catch the cheapest way to game the primary metric. Every primary metric needs at least one, defined before launch with a fixed tolerance.

Standard pairings:

| Primary metric | Gaming risk | Guardrail |
|---|---|---|
| Notifications-driven DAU | Notification spam | Unsubscribe rate, notification-disable rate, 30-day retention |
| Signup conversion | Low-intent signups | Day-7 activation rate of new signups |
| Time in app | Confusing UX inflates time | Task completion rate, task time |
| Reports generated | Bot and abandoned runs | Reports opened by a human within 48h |
| Support ticket deflection | Users give up instead of resolving | CSAT on deflected sessions, repeat-contact rate within 7 days |
| Feature adoption | Forced onboarding tours | Feature retention at week 4, opt-out rate |
| Page load speed via lazy loading | Content never loads | Error rate, content-visible-at-p95 |

Also hold a standing set of platform guardrails on every launch regardless of the feature: p95 latency of the affected endpoints, error rate, support contacts per 1,000 accounts, infrastructure cost per active account, and a core-flow conversion rate.

State each guardrail with a numeric tolerance and a decision rule, because a guardrail without a threshold is a comment. For example: "p95 report-list latency must not exceed 900ms (baseline 780ms, tolerance +15%); breach at any ramp stage halts the rollout and reverts the flag." And: "unsubscribe rate must stay below 0.8% weekly; between 0.8% and 1.2% we reduce frequency, above 1.2% we disable the campaign." Pre-committing the decision rule is what prevents the post-launch conversation where a 30% latency regression is rationalized as acceptable because the primary metric moved.

## Writing a measurable metric target

A metric target is measurable only if it states four things: **baseline → target → timeframe → measurement method.** Add a fifth, the guardrail, for anything user-facing. Anything missing one of these cannot be evaluated after launch and will be argued about instead.

Bad: "Increase adoption of scheduled reports."

Good: **"Increase the share of Growth-plan accounts with ≥1 active report schedule from 0% (baseline, feature does not exist) to 25% within 60 days of GA, measured as `count(distinct account_id in report_schedules where status='active') / count(distinct active Growth accounts)` in the weekly product dashboard, with the guardrail that email unsubscribe rate stays below 0.8% weekly and p95 report-list latency stays under 900ms."**

Component requirements:

1. **Baseline** — the current value with the date and the source. If none exists, say so explicitly and state how you will establish it (a pre-launch measurement window of at least 2-4 weeks for anything with weekly seasonality).
2. **Target** — an absolute number or a percentage change with the direction. Justify it from a comparable: a prior similar launch, a competitor benchmark, or an experiment result. Unjustified targets are guesses and get quietly abandoned.
3. **Timeframe** — a date or a days-from-launch window. Must exceed the metric's natural cycle: a weekly-usage metric needs at least 4 weeks, a retention metric at least a full retention period.
4. **Measurement method** — the exact query, event name, or dashboard, plus the denominator. Ambiguous denominators (all accounts versus eligible accounts versus active accounts) are the most common source of post-launch metric disputes; write the denominator explicitly.
5. **Guardrails** — the metrics that must not degrade, with tolerances and a decision rule.

Two rules that keep the system honest: instrument and verify the events **before** launch, in staging, because a target measured by an event that fires incorrectly is worse than no target; and write the decision in advance — "if we hit 25% we invest in phase 2; if we land between 10% and 25% we run onboarding experiments; below 10% we stop and interview 10 non-adopters." A target with no pre-committed decision attached produces a dashboard nobody acts on.
