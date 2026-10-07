# Verb: design

Plan the next phase before any experiment runs. Input: the four moves'
output; run them now when no review exists. Output: the plan template alone.

* Order: phase 1 is the crucial experiment, the cheapest run whose outcome
  kills a claim or the direction. Nothing irreversible (a cluster rental, a
  full implementation, a submission) precedes it. After it, in this order
  unless a dependency forces otherwise: the tolerance claim on the smallest
  current workload; the mechanism claim at scale on the trusted simulator,
  calibrated against the real run; the comparison against the strongest
  baseline in its own best configuration.
* Cost: every phase carries a cost in the envelope's units:
  accelerator-hours, rented money, people-weeks, simulator-hours. A phase
  whose cost exceeds the envelope takes the simulator or emulator row of the
  spine's instrument table, or names the collaborator it needs.
* Checkpoints: each phase names the test that shows it succeeded or failed
  and the decision its result unlocks. Cut a phase with no decision behind
  it.
* Venue: name the venue class the plan targets and the questions its
  reviewers ask (scale, baseline, generality, variance). The plan answers
  each or names it as out of scope on purpose.

<template for="plan">
## Target
<one sentence: what the finished work shows, in the pattern's own terms>

## Phases
| # | phase | claim | instrument | kill test | cost | unlocks |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | <the crucial experiment> | ... | ... | ... | ... | ... |

## Deferred
<irreversible commitments withheld, each with the phase whose result releases it>

## Out of scope
<what the plan does not attempt, and whether the envelope, the venue, or the claim rules it out>

## Ask
<the one question whose answer changes the plan, or the word none>
</template>

## Completion Checks

<checklist for="verb">
  <item>Phase 1 is the cheapest run that can kill a claim or the direction.</item>
  <item>Every phase has a claim, an instrument, a kill test, a cost, and a decision it unlocks.</item>
  <item>Every cost fits the envelope, or the phase names its simulator, emulator, or collaborator.</item>
  <item>Irreversible commitments sit under Deferred with a releasing phase.</item>
  <item>The venue's questions are each answered or named out of scope.</item>
</checklist>
