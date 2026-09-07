---
title: MoSCoW and Kano Prioritization Models
doc_id: moscow-and-kano
domain: prioritization
tags: [prioritization, moscow, kano, scoping, requirements]
authority: framework
---

# MoSCoW and Kano Prioritization Models

MoSCoW and Kano answer two different prioritization questions. MoSCoW (Must have, Should have, Could have, Won't have) is a scope-commitment model from DSDM: it decides what is in a fixed-date release and what is negotiable when the date is under threat. Kano is a satisfaction model from Noriaki Kano's 1984 research: it classifies features by how their presence and absence map to user satisfaction, which tells you where investment produces delight versus mere table stakes. Teams that use only MoSCoW ship complete but joyless releases; teams that use only Kano ship charming products that miss deadlines. Use Kano to decide what deserves to be built and MoSCoW to decide what ships in the next fixed window.

## MoSCoW categories and the 60% Must-have rule

MoSCoW assigns every candidate requirement in a release to exactly one of four buckets, with precise definitions:

- **Must have:** The release is worthless or non-compliant without it. Test: if it is dropped, would you cancel the release rather than ship? If the honest answer is no, it is a Should have. Legal, safety, and data-integrity items are genuine Musts.
- **Should have:** Painful to omit but there is a workaround, a manual process, or a tolerable degradation. The release still has value without it.
- **Could have:** Desirable, low cost to drop, minimal impact if absent. This is the deliberate contingency pool.
- **Won't have (this time):** Explicitly out of scope for this release, recorded so it is not silently reintroduced. Naming Won'ts is the highest-value part of MoSCoW because it kills scope ambiguity.

The core discipline is the effort budget: **Must-haves must total no more than 60% of the release's available effort.** The remaining 40% splits roughly 20% Should and 20% Could. If Musts consume 85% of capacity, the plan has no contingency, and the first estimate miss forces either a date slip or cutting something the team labeled non-negotiable. Enforce the rule in effort units, not item counts — six Musts at 2 weeks each is 12 weeks, and item counts hide that. When Musts exceed 60%, you have three options and no others: extend the date, add capacity, or renegotiate Musts down to Shoulds. Concretely, for a 10-week release with 4 engineers (40 engineer-weeks), Musts must fit in 24 engineer-weeks.

## Running a MoSCoW session

A MoSCoW session should be timeboxed to 90 minutes with the delivery team, the PM, and one accountable business stakeholder who can say no. Prepare by listing candidate requirements with a rough effort estimate on each — MoSCoW without effort numbers degenerates into a wish list.

The sequence that works: start by assigning **Won't haves** to shrink the field, then identify Musts, then default everything remaining to Could and promote to Should only with a stated reason. Starting from Must invites everything to be a Must; starting from Won't and Could forces justification to move up.

Two mechanics prevent the classic failure of Must-have inflation. First, apply the cancellation test out loud for each proposed Must: "if we ship without this, do we cancel the release?" Second, run the running-total tally on a visible board — as soon as the Must column crosses 60% of capacity, the next Must must displace an existing one. This converts an abstract argument into a trade.

Record for every Must the specific reason it is a Must (regulatory citation, contractual commitment, dependency that blocks other work, or "the product does not function"). Reasons like "the VP asked for it" are not reasons; escalate rather than encode them. Re-run the classification at each release boundary, not mid-sprint: MoSCoW derives its power from being a stable commitment within a window. Mid-window, the only legal move is to drop Coulds and then Shoulds, in that order, which is precisely what the 40% contingency exists for.

## Kano model categories

Kano classifies features by the relationship between how fully a feature is implemented and the satisfaction it produces. There are five categories:

- **Basic (Must-be / expected):** Absence causes strong dissatisfaction; presence produces no satisfaction at all. Login works, data is not lost, the page loads. Investment beyond "correct" yields zero satisfaction return. Target: meet the standard and stop.
- **Performance (One-dimensional / linear):** Satisfaction scales roughly linearly with how much you deliver. Speed, storage limits, number of integrations, price. This is where competitive comparison happens and where incremental investment pays proportionally.
- **Delight (Attractive / excitement):** Absence causes no dissatisfaction because users do not expect it; presence produces disproportionate satisfaction. Historically: undo-send, an unusually good onboarding import, a genuinely useful empty state.
- **Indifferent:** Users do not care whether it exists. Typically 20-40% of a candidate backlog lands here in real surveys. These are the items to cut, and finding them is often the biggest payoff of a Kano study.
- **Reverse:** Presence causes dissatisfaction for a segment — forced social features, aggressive gamification, mandatory onboarding tours, AI suggestions that cannot be turned off. Reverse features usually need a per-segment or opt-out treatment rather than removal.

The investment rule: fully fund Basics to threshold, compete on two or three Performance attributes, fund one or two Delights per release, cut Indifferents entirely, and make Reverse features optional.

## The Kano survey question pair

Kano categories are measured, not guessed, using a paired functional/dysfunctional question for each feature. Ask both questions about the same feature, with identical five-point answer options:

- **Functional (presence):** "If the product had scheduled report delivery by email, how would you feel?"
- **Dysfunctional (absence):** "If the product did NOT have scheduled report delivery by email, how would you feel?"

Answer options for both: (1) I like it, (2) I expect it, (3) I am neutral, (4) I can tolerate it, (5) I dislike it.

Map the answer pair to a category using the standard Kano evaluation table. The key cells: Like/Dislike = Performance; Like/Expect or Like/Neutral or Like/Tolerate = Delight; Expect/Dislike = Basic; Neutral/Neutral or Neutral/Tolerate = Indifferent; Dislike on the functional question = Reverse; Like/Like or Expect/Expect = Questionable (a sign the respondent misread — discard these responses; more than 5-10% questionable means the feature description was unclear).

Practical execution: keep the survey to 8-15 features (each requires two questions, so 15 features is 30 questions and near the fatigue limit), write feature descriptions as concrete user-facing benefits rather than internal names, and aim for n≥100 per segment for stable results, with n≥30 acceptable for directional reads. Report each feature by its modal category plus the percentage distribution — a feature that is Basic for 45% and Indifferent for 40% is a segmentation finding, not a tie. Optionally compute the self-stated importance question (1-9) alongside to break ties within a category.

## Kano decay: how Delight becomes Basic

Kano categories are not stable properties of features; they migrate downward over time as expectations reset. The canonical path is **Delight → Performance → Basic**, driven by competitor adoption and user habituation. Real examples: mobile check deposit was a Delight around 2010, a Performance attribute by 2014, and a Basic requirement by 2018; free HTTPS, autosave in document editors, and dark mode followed the same arc; fast keyword search in a consumer app was a differentiator in 2005 and is now invisible unless broken.

Two consequences for planning. First, **your Basics list grows every year without any product decision on your part**, and the maintenance cost of Basics compounds. Budget for it: a steady 15-25% of engineering capacity on quality, performance, and reliability is not overhead, it is Basic-tier defense against a rising floor. Second, **a Delight-only strategy has a shelf life**, typically 12-24 months in competitive software categories and shorter where a dominant competitor can copy fast. Plan a Delight pipeline rather than a Delight feature.

Re-run a Kano survey every 12-18 months, or immediately after a major competitor ships something in your category, and expect 20-30% of features to have shifted a category. The most expensive mistake is continuing to market and invest in a feature as a differentiator two years after it became a Basic — spend continues while satisfaction returns have gone to zero. The complementary error is under-funding a former Delight that has become Basic: users who no longer notice it when it works will churn when it breaks.

## Combining MoSCoW and Kano

Use Kano first, then MoSCoW, and let Kano categories set defaults for MoSCoW buckets rather than dictating them.

The mapping that works in practice:

| Kano category | Default MoSCoW bucket | Rationale |
|---|---|---|
| Basic (below threshold) | Must have | Absence makes the release unshippable |
| Basic (already at threshold) | Won't have | Additional investment returns nothing |
| Performance (top 2-3 competitive attributes) | Should have | Real value, but degradable in scope |
| Performance (secondary attributes) | Could have | Contingency pool |
| Delight (1-2 per release) | Should have | Protect one Delight from being cut first |
| Indifferent | Won't have | Cut outright |
| Reverse | Won't have, or Could have as opt-in | Never ship as default-on |

Two combination rules matter. First, **protect exactly one Delight as a Should have per release**, not a Could — Coulds are the first thing cut under pressure, so a Delight parked in Could will never ship, and a release of pure Basics and Performance moves no satisfaction needle. Second, **never make a Delight a Must have**: by Kano's definition its absence causes no dissatisfaction, so it cannot be release-blocking, and labeling it Must consumes the 60% budget that genuine Basics need.

Worked application: a 10-week release with 40 engineer-weeks of capacity. Kano identifies 3 sub-threshold Basics (20 engineer-weeks total, 50% — inside the 60% cap), 2 top Performance attributes (10 weeks), 1 Delight (4 weeks), and 6 Indifferents (dropped, freeing 14 weeks). Musts = 20 weeks, Shoulds = 14 weeks, Coulds = 6 weeks. If Basics overrun by two weeks, the Coulds absorb it and the date holds.
