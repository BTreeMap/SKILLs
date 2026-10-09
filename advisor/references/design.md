# Verb: design

Plan next phase before any experiment runs. Input: four moves' output; run
them now when no review exists. Output: plan template alone.

* Order: phase 1 is crucial experiment, cheapest run whose outcome kills
  claim or direction. Nothing irreversible (cluster rental, full
  implementation, submission) precedes it. After it, in this order unless
  dependency forces otherwise: tolerance claim on smallest current workload;
  mechanism claim at scale on trusted simulator, calibrated against real
  run; comparison against strongest baseline in its own best configuration.
* Cost: every phase carries cost in envelope's units: accelerator-hours,
  rented money, people-weeks, simulator-hours. Phase whose cost exceeds
  envelope takes simulator or emulator row of spine's instrument table, or
  names collaborator it needs.
* Checkpoints: each phase names test showing it succeeded or failed, and
  decision its result unlocks. Cut phase with no decision behind it.
* Venue: name venue class plan targets and questions its reviewers ask
  (scale, baseline, generality, variance). Plan answers each or names it out
  of scope on purpose.

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
  <item>Phase 1 is cheapest run that can kill claim or direction.</item>
  <item>Every phase has claim, instrument, kill test, cost, decision it unlocks.</item>
  <item>Every cost fits envelope, or phase names its simulator, emulator, or collaborator.</item>
  <item>Irreversible commitments under Deferred with releasing phase.</item>
  <item>Venue's questions each answered or named out of scope.</item>
</checklist>
