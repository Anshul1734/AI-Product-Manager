---
title: Problem Statements and Opportunity Sizing
doc_id: problem-statement-and-opportunity-sizing
domain: discovery
tags: [discovery, problem-statement, sizing, tam, counterfactual]
authority: practice
---

# Problem Statements and Opportunity Sizing

A product decision rests on two artifacts: a problem statement that is falsifiable, and an opportunity size that is arithmetically defensible. Most roadmap arguments go wrong because the problem statement smuggles in a solution ("users need a dashboard") and the size is a top-down market number with no traceable assumptions ("it's a $40B market"). Both errors are detectable in a five-minute review. A good problem statement names an affected population, an observed behavior, a quantified cost, and evidence, and it can be proven wrong by data. A good opportunity size is built bottom-up from unit economics, shows every assumption with its source, and survives an order-of-magnitude sanity check. This document covers how to write both, plus the severity-frequency matrix for triage and the counterfactual statement that keeps teams from building things nobody would miss.

## Testable problem statements versus solutions in disguise

A problem statement is testable when it asserts something about the world that data could contradict. Four components are required: **who** is affected (a countable population), **what** they do or fail to do (observable behavior), **what it costs** (quantified in time, money, errors, or churn), and **how we know** (evidence with a source).

A solution in disguise fails this test in one of four recognizable ways:

1. **Feature-as-need:** "Users need bulk editing." The word "need" attached to a UI capability. There is no cost, no population, no evidence.
2. **Absence-as-problem:** "We don't have SSO." Missing capability is not a problem; the problem is what its absence causes.
3. **Metric-as-problem:** "Conversion is 2.1%." A number without a mechanism. It states a symptom and implies no behavior to change.
4. **Aspiration-as-problem:** "We want to be the leading platform for X." A goal, not a problem.

Diagnostic questions that expose disguise: Could this statement be false, and what data would show that? Does it name a specific behavior someone performs today? Would three different teams propose three different solutions to it? If only one solution fits, the solution is already baked in and you have skipped the design space.

A well-formed statement leaves the solution genuinely open. "Enterprise admins re-key user lists by hand" admits SSO, SCIM provisioning, CSV import, a directory-sync integration, or an API — five candidate solutions with very different costs. That openness is the entire point.

## Bad to good problem statement rewrite

**Bad:** "Customers need a better reporting dashboard."

Every failure is present: no population, no behavior, no cost, no evidence, and the solution ("dashboard") is pre-selected.

**Good:** "Of 1,180 accounts on the Growth plan, 340 (29%) export raw CSVs more than 4 times per month and rebuild the same summary in a spreadsheet. Session recordings and 14 interviews show this takes 25-40 minutes per cycle, roughly 2.5 hours per account per month. These accounts churn at 4.1% monthly versus 2.3% for accounts that never export, and 'reporting takes too long' appears in 31 of 96 churn surveys from this segment over the last two quarters."

What the rewrite adds: a population (340 Growth accounts), an observed behavior (repeated CSV export plus manual rebuild), a quantified cost (2.5 hours/account/month, 1.8-point churn delta), and evidence with sources (analytics, 14 interviews, 96 churn surveys). It is falsifiable — if the churn delta disappears when controlling for account size, the statement is wrong.

Note what the good version still does not do: it does not say "build a dashboard." The stated problem admits scheduled email reports, saved views, a spreadsheet plugin, an API, or a warehouse sync. It also gives the team the numbers needed to size the opportunity and to set a success metric ("reduce manual rebuild cycles per account from 4.2/month to under 1.0 within one quarter of launch"). A statement you can turn directly into a metric target without adding new information is a statement that was written correctly.

## TAM, SAM, and SOM with a bottom-up calculation

Three nested sizes, each with a distinct definition:

- **TAM (Total Addressable Market):** annual revenue if every entity with the problem bought a full-priced solution from someone. Ignores competition and reachability.
- **SAM (Serviceable Addressable Market):** the TAM subset your product, pricing, geography, compliance posture, and channel can actually serve today.
- **SOM (Serviceable Obtainable Market):** the SAM share you can realistically win in a stated window, typically 3 years, given competitors and your go-to-market capacity.

Always build bottom-up: `market size = number of qualifying entities × units per entity × price per unit`. Top-down percentage-of-a-big-number reasoning ("1% of a $40B market") is not evidence and should be rejected in review.

Worked bottom-up example for a compliance-automation tool sold to US mid-market healthcare providers:

| Step | Assumption | Source | Value |
|---|---|---|---|
| Qualifying entities | US outpatient clinics with 20-500 staff | Census NAICS 6211 | 41,000 |
| Have the problem | Perform manual quarterly HIPAA audits | Survey, n=210, 68% | 27,900 |
| Units per entity | 1 org seat bundle | Pricing model | 1 |
| Annual price | $14,400/yr ($1,200/mo) | Current ACV | — |
| **TAM** | 27,900 × $14,400 | | **$402M** |
| SAM filter | Have an EHR we integrate with (Epic/Cerner/athena = 54%) | Vendor share data | 15,066 |
| **SAM** | 15,066 × $14,400 | | **$217M** |
| SOM filter | 3-year reachable share at current sales capacity: 6% | 4 AEs × 2.5 closes/mo × 36 mo ≈ 360 accounts + PLG ≈ 540 total | 900 |
| **SOM** | 900 × $14,400 | | **$13.0M ARR** |

Two review rules. First, every row cites a source; "estimated" without a source invalidates the row. Second, sanity-check SOM against capacity independently — 900 accounts over 3 years is 25/month, which must be consistent with the funnel and quota model, not just with the percentage.

## Severity by frequency matrix

Once several problems are stated, triage them on two axes: **severity** (cost per occurrence) and **frequency** (occurrences per user per period). The product is the annualized cost, and the quadrant tells you what kind of solution is warranted.

| | Low frequency (< 1/month) | High frequency (≥ 1/week) |
|---|---|---|
| **High severity** (>30 min, data loss, revenue at risk) | **Catastrophic-rare:** invest in prevention, recovery, and guarantees. Users tolerate friction here. Examples: failed migration, lost draft, billing error. | **Critical:** top of roadmap. Compounding cost, high churn correlation, strong willingness to pay. Fix first. |
| **Low severity** (< 5 min, cosmetic, recoverable) | **Ignore:** annualized cost is negligible. Do not build; log and close. | **Papercuts:** individually trivial, collectively the top driver of "the product feels bad." Batch 8-12 into a single quality release rather than prioritizing individually. |

Quantify rather than eyeball. Annualized cost per user = severity (minutes or dollars) × frequency (occurrences per year). Worked comparison: Problem A costs 35 minutes and occurs monthly = 7 hours/user/year. Problem B costs 90 seconds and occurs 8 times per week = 10.4 hours/user/year. Problem B is larger despite feeling smaller, and this arithmetic is why papercut batches often outrank a marquee feature.

Two adjustments. Weight by population — a critical problem affecting 3% of users may rank below a papercut affecting 80%. And weight the catastrophic-rare quadrant upward for trust-sensitive domains (payments, health, security), because a single data-loss event produces churn and reputational cost far above its time cost; a common rule is to treat any irreversible data-loss path as top-quartile regardless of frequency.

## Stating the counterfactual

The counterfactual is an explicit answer to: **what happens if we build nothing?** Every problem statement should carry one, in writing, before any solution is scoped. It is the single cheapest filter for low-value work.

Write it in three parts:

1. **Current workaround and its cost.** What do users do today, and what does it cost them? "They export CSVs and rebuild in Excel: 2.5 hours per account per month." If there is no workaround, that is a stronger signal — but verify it, because users almost always have one.
2. **Trajectory without intervention.** What happens over the next 2-4 quarters if nothing ships? "Export volume grew 22% quarter over quarter; the affected segment is our fastest-growing plan, so exposure roughly doubles in a year." Or, honestly: "nothing changes; users have coped for three years and will continue to."
3. **Who notices and when.** Which specific stakeholder feels the absence, and through what channel? "Two of our five largest accounts named it in their renewal QBR, with renewals in Q3."

The kill test: if the counterfactual reads "users continue to use the existing workaround, which is mildly annoying, and no revenue, retention, or compliance outcome changes," the correct decision is not to build. Recording that explicitly saves the team from re-litigating the idea every quarter.

The counterfactual also sets the success-metric baseline for free. "2.5 hours per account per month today, growing 22% QoQ" is the pre-launch baseline, and the target becomes a delta against it rather than an invented number. And it separates real urgency from manufactured urgency: a genuine deadline (a regulation effective date, a contractual commitment, a dependency freeze) appears in part 3 with a date attached, while manufactured urgency cannot produce one.
