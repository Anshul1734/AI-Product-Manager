---
title: User Stories and Acceptance Criteria
doc_id: user-stories-and-acceptance-criteria
domain: requirements
tags: [requirements, user-stories, invest, gherkin, acceptance-criteria]
authority: practice
---

# User Stories and Acceptance Criteria

A user story is a placeholder for a conversation plus a commitment to a user-visible outcome; acceptance criteria are the falsifiable conditions that decide whether the story is done. Together they are the smallest useful unit of requirement. Stories fail in two directions: written too large, they hide unestimated risk and never finish inside a sprint; written as implementation tasks ("add index to orders table"), they lose the user outcome and the team ships technically complete work that solves nothing. Acceptance criteria fail when they are aspirational rather than testable — "the page should feel fast" cannot be passed or failed, so it will be declared passed. This document covers the story form, INVEST, Gherkin criteria with a worked example, splitting patterns, and the falsifiability rule.

## The user story form

The canonical three-part form:

**"As a [specific role], I want to [capability], so that [benefit]."**

Example: *"As a finance analyst preparing month-end close, I want to schedule a saved report to email me every weekday at 7am, so that the numbers are waiting before my 8am standup."*

Rules that separate a working story from a filled-in template:

1. **The role must be specific.** "As a user" is worthless — it appears in every story and constrains nothing. Use the persona or the role-in-context: "as a finance analyst preparing month-end close," "as an org admin onboarding a new hire."
2. **The capability must be user-visible.** If a user could not observe the result, it is a task, not a story. Technical work is legitimate but should be written as an enabler with its own acceptance criteria rather than forced into story form.
3. **The "so that" must be non-obvious and non-circular.** "So that I can schedule reports" restates the capability and adds nothing. A good benefit clause names an outcome that could motivate cutting or changing the capability — which is exactly its purpose: it tells the team what to preserve if the implementation has to change.
4. **One role, one capability, one benefit.** The word "and" in the capability clause is the most reliable signal that the story needs splitting.

Two supporting practices. Keep the story title short and outcome-shaped ("Schedule a saved report for daily email") because that is what appears in boards and standups. And keep the three C's in mind — Card (the short statement), Conversation (the shared understanding, which the card only points at), Confirmation (the acceptance criteria). A team that treats the card as the specification has skipped the two parts that carry the information.

## INVEST criteria

INVEST is the six-part quality check for a story, applied before it enters a sprint. Each letter has a concrete test:

- **Independent** — can be built and released without waiting on another story in the same sprint. Test: could this be the only story shipped this week? Dependency chains longer than two force sequencing and destroy flow. Where dependencies are unavoidable, merge the pair or invert the order so the dependent piece is smaller.
- **Negotiable** — describes an outcome, leaving implementation open. Test: could two engineers reasonably implement it differently and both satisfy the acceptance criteria? A story specifying the exact HTML is not negotiable and has smuggled design into requirements.
- **Valuable** — delivers observable value to a user or a paying customer, not just to the codebase. Test: can you write the release note? "Refactored the scheduler" has no release note.
- **Estimable** — the team can size it. Test: does the team converge within one Fibonacci step? Wide spread (2 vs 13) means missing information, not a difficult story; resolve with a spike, not an average.
- **Small** — completable by one or two people within a single sprint, ideally 1-3 days of work. Practical rule: nothing larger than roughly half a sprint for one pair; anything above 8 story points on a Fibonacci scale should be split.
- **Testable** — has falsifiable acceptance criteria. Test: could QA write pass/fail cases from it with no further questions?

Use INVEST as a gate at backlog refinement. The two letters that catch the most defects in practice are Small and Testable; the two most often waved through are Independent and Valuable. When a story fails Independent or Valuable, the usual root cause is that it was created by slicing horizontally by technical layer ("build the API," "build the UI") instead of vertically through the stack.

## Gherkin acceptance criteria with a worked example

Acceptance criteria in Given/When/Then (Gherkin) form make conditions executable and reviewable. Structure: **Given** the preconditions and state, **When** the trigger action, **Then** the observable outcome. One trigger per scenario; if you need a second "When," write a second scenario.

Worked example for the report-scheduling story:

```gherkin
Feature: Schedule a saved report for recurring email delivery

  Scenario: Analyst creates a weekday morning schedule
    Given I am signed in as a finance analyst with edit access to the saved report "Month-End Revenue"
    And no schedule exists for that report
    When I create a schedule for weekdays at 07:00 in America/New_York with recipients ["me@acme.com","cfo@acme.com"]
    Then the schedule is saved with status "active"
    And the next run time shown is the next weekday at 07:00 America/New_York
    And a confirmation email is sent to me within 60 seconds

  Scenario: Schedule delivers on time with an attachment
    Given an active weekday 07:00 schedule for "Month-End Revenue"
    When the scheduled time is reached
    Then each recipient receives one email within 5 minutes of 07:00 local time
    And the email contains a CSV attachment of at most 50,000 rows
    And the run is recorded in the schedule history with status "delivered"

  Scenario: Recipient limit is enforced
    Given I am creating a schedule
    When I submit 21 recipients
    Then the request is rejected with HTTP 422
    And the error message reads "Maximum 20 recipients per schedule"
    And no schedule is created

  Scenario: Report exceeds the attachment size limit
    Given an active schedule whose report now returns 120,000 rows
    When the scheduled run executes
    Then recipients receive an email containing a download link instead of an attachment
    And the run is recorded with status "delivered_as_link"

  Scenario: Viewer cannot schedule
    Given I am signed in with the "viewer" role
    When I open the saved report
    Then the "Schedule" action is not available
```

Note the properties that make these usable: every Then is observable (status value, HTTP code, exact message text, time bound), numbers are concrete (20 recipients, 50,000 rows, 5 minutes), and the set covers happy path, limit enforcement, degradation, and permissions. A story with only a happy-path scenario is not ready.

## Splitting large stories

When a story exceeds roughly 8 points or half a sprint, split it vertically — each slice must still deliver observable value end to end. Four reliable patterns, in the order to try them:

1. **By workflow step.** Take the sequence and ship the steps as separate stories. Scheduling splits into: create a schedule (no delivery yet, visible in a list) → deliver on schedule → view run history → edit/pause a schedule. Each step is independently useful and demoable.
2. **By data variation.** Ship one data type, format, or entity first. "Export as CSV" now, "export as XLSX and PDF" later. Or "email delivery" now, "Slack and webhook" later. Best when the variations share a pipeline and differ only at the edges.
3. **By CRUD operation.** Create, read, update, delete as separate stories. Create + read is almost always the valuable first slice; update and delete follow. Works well for admin and configuration surfaces, where read-only visibility often delivers most of the value.
4. **By happy path versus unhappy path.** Ship the success case with a blunt generic error, then handle specific failures — validation messages, retries, partial failures, quota exhaustion — as follow-ups. Use this only when the unhappy paths are recoverable and non-destructive; never defer error handling on a payment, deletion, or migration path.

Two more when the four above do not fit: **by acceptance criterion** (if a story has 9 criteria, the 3 that carry the value become story one) and **by effort spike** (extract the unknown into a timeboxed 2-3 day investigation so the remainder becomes estimable).

Anti-patterns to reject: splitting by technical layer ("backend story" / "frontend story"), which produces stories that fail Valuable and Independent and hide integration risk until the end; and splitting by role on the team ("designer's story"), which is a task breakdown, not a story split. If a slice cannot be demoed to a user, it is not a valid vertical split — merge it back and try a different pattern.

## The falsifiability rule for acceptance criteria

**Every acceptance criterion must be falsifiable: there must exist an observation that would prove it unmet.** A criterion that cannot fail cannot pass, and criteria that cannot fail are declared passed by default, which is how untested behavior reaches production.

Non-falsifiable criteria and their rewrites:

| Not falsifiable | Falsifiable rewrite |
|---|---|
| "The page loads quickly." | "The report list renders within 800ms at p95 for accounts with up to 500 saved reports, measured by RUM." |
| "Errors are handled gracefully." | "On a 5xx from the report service, the UI shows 'We couldn't load your reports — retry' with a retry button; the request is retried at most 3 times with exponential backoff; no unhandled exception reaches the console." |
| "The UI is intuitive." | "In moderated testing with 5 participants, at least 4 create a schedule without assistance in under 90 seconds." |
| "Data is secure." | "A user in org A receives HTTP 404 when requesting a schedule ID belonging to org B; the attempt is written to the audit log." |
| "It works on mobile." | "All actions are operable at 375px width in Safari iOS 17 and Chrome Android 121; tap targets are at least 44x44px." |
| "Performance is acceptable under load." | "With 10,000 concurrent active schedules, 99% of runs dispatch within 5 minutes of their scheduled time." |

The mechanical test: read the criterion and ask, *what exact observation would make me write "fail" in this row?* If you cannot name one in a sentence, rewrite it with a number, a percentile, an exact string, a status code, or a count of participants.

Three corollaries. First, subjective quality goals are legitimate but must be operationalized into a measurement — usability targets become task-success rates with a participant count. Second, a criterion covering a percentile needs the measurement method named, because p95 in a load test and p95 in real user monitoring are different claims. Third, negative criteria are as important as positive ones: state what must *not* happen ("no email is sent to unsubscribed recipients," "no schedule is created on validation failure"), since silent unwanted side effects are the defects that acceptance criteria most often miss.
