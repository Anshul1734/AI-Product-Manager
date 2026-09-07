---
title: Estimation and Delivery Planning
doc_id: estimation-and-delivery-planning
domain: delivery
tags: [delivery, estimation, story-points, forecasting, planning]
authority: practice
---

# Estimation and Delivery Planning

Estimation exists to support a decision — whether to commit to a date, what to cut, or whether to do the work at all — and any estimation effort beyond that purpose is waste. The reliable pattern is: size work relatively and coarsely, forecast from historical throughput rather than by summing estimates, sequence so that the riskiest integration happens first, and express dates as ranges with stated confidence. Teams get this wrong by converting points to hours (which reintroduces false precision), by treating the sum of estimates as a schedule (which ignores that estimates are systematically optimistic), and by giving single-point dates (which guarantees a miss because a single date has roughly 50% probability at best). The sections below cover points versus hours, Fibonacci and reference stories, the cone of uncertainty, throughput forecasting, walking-skeleton sequencing, buffer allocation, and points-to-calendar-time conversion.

## Story points versus ideal hours

**Story points** are a unitless relative measure of size combining complexity, effort, and uncertainty. Their value is threefold: they are faster to produce than time estimates, they aggregate meaningfully because individual errors cancel across a batch, and they avoid the commitment psychology of hours — nobody is held to "8 points" the way they are held to "16 hours."

**Ideal hours** (or ideal days) estimate uninterrupted working time for the task. They are more intuitive for new teams and necessary for contracts and agency work billed by time. Their fatal weakness is the focus-factor problem: an 8-hour workday yields roughly 4.5-6 hours of focused product work after standups, reviews, interrupts, and support, so an "8 ideal hour" task takes 1.5-2 calendar days. Teams that forget the conversion under-plan by 40-60%, and every schedule slips.

Practical guidance:

- **Use points for sprint and release planning**, because you forecast against historical velocity in the same unit and the focus factor is already baked into the observed velocity.
- **Use hours only inside a sprint for task breakdown**, where the horizon is short enough for the precision to be real.
- **Never publish a points-to-hours conversion rate.** The moment "1 point = 6 hours" is written down, points become hours with extra steps, estimates get audited against actuals, and the team inflates to protect itself.
- **Do not estimate individual points per person.** Points are a team property; the same story is a different size for a different team, and that is correct, not a defect.

A legitimate alternative worth considering for mature teams: **no estimates at all**, forecasting purely from throughput (stories completed per week) plus cycle-time distribution. This works when stories are consistently small — a good bar is 85% of stories finishing within 5 days — because story count then becomes a reasonable proxy for size and the estimation ceremony adds nothing.

## Fibonacci sizing with reference stories

Use a modified Fibonacci scale: **1, 2, 3, 5, 8, 13, 21**. The widening gaps are the point — they mirror the fact that estimate error grows with size, so the scale refuses to distinguish 13 from 14 when neither number is knowable. Add `?` for "needs a spike."

Anchor the scale with **reference stories**: 2-3 completed stories the team remembers, one per size at the low end.

| Points | Reference story | Typical duration for one pair |
|---|---|---|
| 1 | Add a validation message to an existing form field | Under half a day |
| 2 | Add a sortable column to an existing table | About a day |
| 3 | New read-only detail page from an existing endpoint | 1-2 days |
| 5 | New CRUD endpoint plus form, with validation and tests | 3-4 days |
| 8 | New feature spanning API, UI, and a schema change | Most of a sprint |
| 13 | Too large — split it | — |
| 21 | Epic — decompose into stories | — |

Rules that keep the scale useful:

1. **Estimate by comparison, not by decomposition.** "Is this bigger or smaller than the sortable-column story?" is the only question. Decomposing into hours and adding up defeats the purpose.
2. **Anything 13 or above must be split before it enters a sprint.** Empirically, stories above 8 points have the widest actual-versus-estimate spread and are the primary cause of sprint spillover.
3. **Re-anchor references every 2-3 months** and after any team composition change, because point inflation is real and silent — velocity that rises with no throughput change is inflation, not improvement.
4. **Treat wide disagreement as information.** If estimates come back 2, 3, and 13, the 13 knows something. Discuss, then re-vote. Averaging discards the most valuable signal in the room.
5. **Time-box estimation** to about 2 minutes per story. Longer discussion is design work; schedule it separately.

## The cone of uncertainty

The cone of uncertainty describes how estimate accuracy improves as a project progresses and unknowns resolve. Boehm's original data and subsequent studies give approximate multipliers on a best-guess estimate:

| Stage | Range on the true value |
|---|---|
| Initial concept / idea | 0.25x to 4x |
| Approved product definition (PRD signed off) | 0.5x to 2x |
| Requirements complete | 0.67x to 1.5x |
| Design complete | 0.8x to 1.25x |
| Implementation underway, first slice shipped | 0.9x to 1.1x |

Worked application: an initiative estimated at 8 weeks at the concept stage has a true range of 2 to 32 weeks. Quoting "8 weeks" at that stage is not an estimate, it is a coin flip with extra confidence. After a PRD with defined requirements and non-goals, the same estimate narrows to 4-16 weeks. After a design doc and a walking skeleton, 7-9 weeks.

Three operating rules follow. First, **quote ranges with the stage attached**: "8-16 weeks, at PRD-complete confidence; we can narrow to a 2-week band after a 1-week design spike." Second, **the cone narrows only through work** — time alone does not reduce uncertainty, so the way to get a tighter number is to build a thin slice, not to hold another estimation meeting. Third, **re-forecast at stage boundaries** and communicate the change; a team that quotes one number at concept and never revises it has chosen to be wrong publicly later rather than uncertain publicly now.

The most common misuse is stakeholders anchoring on the lower bound. Counter it by leading with the upper bound and the confidence level, and by attaching the decision to the range: "if the answer must be under 10 weeks, we cut the reporting phase now."

## Throughput-based forecasting

Do not forecast by summing estimates. Sums of optimistic estimates are optimistic, and they omit everything not in the backlog — defects, support, meetings, holidays, and the work discovered mid-build (typically 15-30% of final scope).

Forecast from measured history instead:

`weeks remaining = remaining backlog size / historical throughput per week`

Use a **rolling window of the last 6-10 completed iterations** and take a range rather than a mean. Worked example: a team completed 18, 24, 21, 30, 16, and 23 points in its last six two-week sprints. The pessimistic figure is 16/sprint, the median 21.5, the optimistic 30. For a 210-point remaining backlog: 210/16 = 13.1 sprints (26 weeks) worst case, 210/21.5 = 9.8 sprints (20 weeks) likely, 210/30 = 7 sprints (14 weeks) best case. Report "20-26 weeks, most likely 20-22," not "10 sprints."

Better still, forecast with a **Monte Carlo simulation** over the historical throughput distribution: sample completed-per-sprint values 10,000 times until the backlog is exhausted, then report percentiles. This yields statements like "85% likely to complete by 24 May" that are honest about the shape of the risk and are far more useful to a stakeholder than a mean. Tools do this in minutes from a spreadsheet of sprint outcomes; the discipline matters more than the tooling.

Also add a **scope-growth factor**. Measure it: compare the backlog size at kickoff to the size at completion over past initiatives. A factor of 1.2-1.4x is typical for well-defined work and 1.5-2x for exploratory work. Multiply the remaining backlog by the measured factor before dividing by throughput. And use **counts rather than points** when stories are consistently small — stories-per-week with a cycle-time distribution is more stable than velocity because it is not subject to point inflation.

## Walking skeleton first sequencing

A walking skeleton is the thinnest possible end-to-end slice that exercises every layer and integration point of the system in production — real request, real API, real database, real deploy pipeline, real observability — even if the functionality is trivial.

Example for report scheduling: a hardcoded schedule that sends one hardcoded email to one address, deployed behind a flag, with logging and a metric, by end of week one. It is not demoable to a customer, but it proves the scheduler runs in production, the email provider is authenticated, the deploy works, and the metrics land.

Sequence an epic in this order:

1. **Walking skeleton** — end-to-end through every layer and third-party dependency, with observability wired up. Target 5-10% of total effort.
2. **Riskiest integration or unknown next.** Third-party APIs, migrations, performance-critical paths, anything with a `?` estimate. Front-load these deliberately.
3. **Happy path for the primary persona**, thin but real.
4. **Breadth** — additional variations, formats, roles, edge cases.
5. **Polish and hardening** — error states, empty states, accessibility, rate limits.

The rationale is decision economics: risk-first sequencing surfaces schedule-breaking surprises in week 1-2 when the plan can still change, rather than in week 8 when it cannot. The alternative — building each layer completely before integrating (all backend, then all frontend) — hides integration risk until the end and produces the classic "90% done for six weeks" failure.

Two mechanics worth enforcing. Keep the skeleton **deployed to production behind a flag from day one**, because "works locally" is not evidence and the last mile is where the surprises live. And require every subsequent slice to keep the skeleton working, which makes the integration path a continuously verified asset rather than a one-time milestone.

## Buffer and risk allocation

Buffer is capacity deliberately left unassigned to absorb variance. Planning at 100% capacity guarantees a miss, because variance is one-directional in practice — work rarely finishes early enough to matter.

Allocation guidance per iteration, as a share of nominal capacity:

- **Feature work: 60-70%.** This is the plannable, committed portion.
- **Defects and support: 10-20%.** Measure your actual rate rather than guessing; teams with a mature product often need more.
- **Technical health: 10-15%.** Refactoring, dependency upgrades, test and pipeline maintenance. Skipping this borrows capacity from future iterations at a high interest rate.
- **Unplanned and interrupt: 10%.** Incidents, urgent requests, onboarding.

At the release level, add a **schedule buffer sized by uncertainty**, not a flat percentage: roughly 15-20% for well-understood work with no new integrations, 30-40% when the initiative includes a new third-party dependency, a data migration, or a new team, and 50%+ for genuinely novel work. Place the buffer at the *end of the release*, as a project-level buffer, rather than padding individual estimates. Padded individual estimates are invisible, get consumed silently by Parkinson's law, and destroy the team's ability to forecast because no estimate reflects real belief.

Reserve buffer for the specific named risks in the plan, and track consumption openly: "we have used 60% of the schedule buffer at 40% of elapsed time" is an early, actionable warning that no burndown chart provides. Two rules keep buffers honest: **never let a stakeholder negotiate the buffer away** — the correct response to "can you do it without buffer?" is "yes, at roughly 50% confidence instead of 85%, and here is what we would cut if we are wrong"; and **do not spend buffer on scope**. Buffer absorbs variance in committed work. Using it for new requests means the next surprise has nowhere to go, which is how a plan fails in a single week.

## Mapping story points to calendar time

Convert points to dates only through measured throughput, never through an assumed hourly rate. The formula:

`calendar weeks = (backlog points × scope-growth factor) / (points per week) `

where `points per week = historical points per iteration / weeks per iteration`, taken as a range from the last 6-10 iterations.

Worked example. A team of 5 (4 engineers, 1 designer) on two-week sprints has completed 18-30 points per sprint over six sprints, median 21.5, so 9-15 points per week with a median of about 10.75. An epic is estimated at 120 points, and past initiatives on this team have grown 1.3x from kickoff to completion, so plan against 156 points.

- Pessimistic: 156 / 9 = 17.3 weeks
- Median: 156 / 10.75 = 14.5 weeks
- Optimistic: 156 / 15 = 10.4 weeks

Then adjust for the calendar, which is where most conversions break: subtract holidays, planned PTO, on-call rotations, company events, and a hiring ramp. Two weeks of aggregate PTO plus one company offsite week across the quarter is roughly 1.5 weeks of lost throughput, pushing the median to about 16 weeks. **Communicate "16-19 weeks, 85% confidence by week 19," not "14.5 weeks."**

Three rules. **Adding people does not divide the time** — Brooks's law is real, and a new engineer typically costs net capacity for 4-8 weeks before contributing; a mid-project addition should be modeled as negative throughput for the first month. **Never convert points to time for a team without history**; use a comparable team's throughput as a placeholder, flag it explicitly as borrowed, and replace it with real data after 3 sprints. And **re-forecast every sprint** using the updated rolling window — a forecast made at kickoff and never revised is the single most common cause of a surprise slip, because the information needed to correct it existed weeks before anyone said anything.
