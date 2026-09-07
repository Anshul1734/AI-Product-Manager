---
title: Jobs To Be Done Framework
doc_id: jobs-to-be-done
domain: discovery
tags: [discovery, jtbd, research, customer-needs, outcomes]
authority: framework
---

# Jobs To Be Done Framework

Jobs To Be Done (JTBD) holds that customers do not buy products, they hire solutions to make progress in a specific circumstance. The unit of analysis is the job — the progress someone is trying to make — not the person, the demographic, or the product category. The framework has two main lineages: Clayton Christensen's demand-side variant, which emphasizes circumstance, causality, and switching behavior, and Tony Ulwick's Outcome-Driven Innovation, which decomposes jobs into measurable outcome statements you can survey and score. Both share the same practical payoff: a job is stable over decades while solutions churn, so a roadmap organized around jobs survives technology shifts that a roadmap organized around features does not. JTBD is strongest for identifying underserved needs and competitive substitutes; it is weakest for interface design and for pricing, where you still need usability research and willingness-to-pay work.

## Job statement syntax

A job statement in JTBD uses a fixed three-part syntax that forces circumstance, motivation, and outcome into the same sentence:

**"When [situation], I want to [motivation], so I can [expected outcome]."**

A concrete, well-formed example: *"When I get a customer escalation on Friday afternoon, I want to see every prior ticket and invoice for that account in one place, so I can respond with accurate context before the weekend."*

Rules for writing job statements that hold up:

1. **The situation must be a triggering circumstance, not a persona.** "When I get an escalation on Friday afternoon" is a situation; "As an account manager" is a role and belongs in a persona doc, not a job statement.
2. **The motivation must be solution-agnostic.** Write "see every prior ticket and invoice in one place," not "use a unified timeline widget." If a competitor's product name or your own UI could be substituted into the motivation clause, it is a feature request wearing a JTBD costume.
3. **The expected outcome must be observable.** "Respond with accurate context before the weekend" can be checked; "feel more confident" cannot be checked without an accompanying measure.
4. **Keep it at one level of abstraction.** A job statement that spans "plan my quarter" and "click the export button" is two jobs — one main job and one supporting task.

Test each statement by asking whether it would still have been true five years ago and will still be true five years from now. If technology change invalidates the sentence, it is a solution statement, not a job.

## Functional, emotional, and social job dimensions

Every JTBD has three dimensions, and products that only serve the functional dimension lose to products that serve all three.

- **Functional dimension:** the practical task to be accomplished. Measurable in time, error rate, cost, or completeness. Example: reconcile 400 transactions against a bank statement in under 20 minutes with zero unmatched rows.
- **Emotional dimension:** how the person wants to feel, or avoid feeling, while doing the job. Usually anxiety reduction rather than joy. Example: not fearing that a missed transaction will surface in an audit; wanting to feel in control before a board meeting.
- **Social dimension:** how the person wants to be perceived by others while doing the job. Example: appearing rigorous to the CFO; not being the person who sends the team a spreadsheet with broken formulas.

The emotional and social dimensions explain buying behavior that functional analysis cannot. A bookkeeper choosing software with a slower workflow but a clean audit trail is optimizing the social dimension (defensibility to an auditor) over the functional one (speed). In B2B, the social dimension is often decisive because the buyer's reputation is on the line — this is why enterprise buyers pay for reporting features they rarely read.

In practice, capture all three per job in a three-row table and check coverage: if your product roadmap addresses only functional gaps, expect flat satisfaction scores despite shipping. A useful heuristic from consumer research is that when functional parity exists across competitors, emotional and social dimensions account for the majority of preference. Interview for these dimensions by asking "what were you worried about?" and "who else saw the result of this?" rather than asking about feelings directly.

## Forces of progress

The forces of progress model explains why people switch — or fail to switch — solutions. Four forces act on any switching decision, two pushing toward change and two resisting it:

1. **Push of the situation:** dissatisfaction with the current state. "Our spreadsheet broke twice last quarter and we missed a filing deadline."
2. **Pull of the new solution:** the attraction of the imagined better state. "Their demo showed reconciliation finishing in one click."
3. **Anxiety about the new solution:** fear of the unknown — will migration lose data, will the team learn it, will it be worse. "What happens to five years of history?"
4. **Habit of the present:** inertia, sunk investment, existing workarounds that mostly work. "I already have macros that handle this."

Switching happens only when **Push + Pull > Anxiety + Habit**. This asymmetry has a hard product implication: most teams over-invest in Pull (more features, better demos) when the binding constraint is Anxiety or Habit. Reducing Anxiety is usually cheaper and more effective — concrete levers are free guided migration, an import tool that handles the customer's actual export format, a 30-day parallel-run mode, published rollback instructions, a named onboarding contact, and month-to-month billing instead of an annual lock-in.

Interview for the forces by reconstructing a timeline of a real switch: what happened first, when did you start looking, what almost stopped you, who else had to agree. The moment "I started looking" is the push trigger and is the single most valuable input for marketing and onboarding design. If interviews reveal high Push and high Pull but no switch, the roadmap item is not a feature — it is an anxiety-reduction mechanism.

## Deriving outcome statements

Outcome statements are the measurable, testable layer beneath a job. They follow Ulwick's syntax:

**[Direction of improvement] + [unit of measure] + [object of control] + [contextual clarifier]**

Examples: *"Minimize the time it takes to identify unmatched transactions when closing the month."* *"Reduce the likelihood of submitting a report with stale data before a board meeting."* *"Minimize the number of tools required to answer a customer's billing question."*

Every outcome statement starts with minimize, reduce, or increase, and names a unit — time, likelihood, number, frequency. That is what makes it surveyable. Derive outcome statements by mapping the job into 6-10 sequential steps (define, locate, prepare, confirm, execute, monitor, modify, conclude) and then eliciting 3-8 desired outcomes per step. A typical mature job map yields 50-150 outcome statements.

Prioritize outcomes with an opportunity score. Survey a representative sample (n≥150 for segment stability) on two 1-10 scales per outcome — importance and current satisfaction — then compute:

`Opportunity = Importance + max(Importance − Satisfaction, 0)`

Outcomes scoring above roughly 15 are underserved and represent the innovation targets; scores between 10 and 15 are appropriately served; below 10 are overserved and are candidates for cost reduction or removal. Worked example: an outcome with Importance 9.1 and Satisfaction 4.2 scores 9.1 + 4.9 = 14.0 (near-underserved), while Importance 9.4 with Satisfaction 3.1 scores 15.7 and is a clear target. The output is a ranked list of measurable gaps that survives reorganizations and can be handed directly to a PRD as success metrics.

## JTBD versus persona-based thinking

JTBD and personas answer different questions, and confusing them produces a specific class of bad roadmap.

Persona-based thinking segments by **who the user is** — role, demographics, firmographics, technical fluency, attitudes. It answers "who am I designing the interface and the message for." JTBD segments by **what progress the user is trying to make in a circumstance**. It answers "what should exist, and what are we actually competing with."

The practical differences:

| Dimension | Persona | JTBD |
|---|---|---|
| Unit of analysis | Person / segment | Job in a circumstance |
| Stability | Shifts with market and positioning | Stable for years or decades |
| Competitive set | Products in your category | Any solution hired for the job, including spreadsheets, agencies, and doing nothing |
| Best used for | UX, copy, targeting, support | Roadmap strategy, market definition, positioning |
| Failure mode | Demographic correlation mistaken for causation | Over-abstraction into unactionable jobs |

The causality point is the crux. "Marketing managers aged 30-45 at mid-market SaaS companies" is a correlation; it does not tell you why anyone bought. "When a campaign underperforms mid-flight and I have to explain it to my VP tomorrow, I want to isolate which channel broke, so I can arrive with a fix rather than a problem" tells you what to build and reveals that the real competitor is an analyst with a spreadsheet, not the other analytics vendor.

Use both, in order: JTBD to decide what to build and who you compete with, personas to decide how it should look and sound. The strongest artifact combines them — a persona document whose pain points are written as job and outcome statements. Note also that one person performs many jobs and one job is performed by many personas, so a strict one-to-one mapping between the two is always a modeling error.
