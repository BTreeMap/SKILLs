# Design plan

Stage 1 deliverable for `design` and for `write` from shaped idea, one
section per heading below. Human accepts it before any experiment runs.

## Scenario sketch

Name actors, scale, workload, present failure, quantitative setting in
concrete terms. Practitioner-recognition test: practitioner in the area
reads sketch, recognizes setting as real. Would not: make scenario concrete
enough to plan experiments around.

**Example: scenario-sketch**

Before: modern datacenters

After: a 128-GPU training job's all-reduce on a 4-spine fabric where one
spine degrades 30%

## Contradiction

Frame work as contradiction, mismatch, deployment gap, or unexplained
observation (evidence section 1 in `award-assessment`). Name two things that
should agree and do not.

## Problem statement

Answer in plain language, no jargon: what you are trying to do; how it is
done today and where limits are; what is new about your approach and why it
will succeed; who cares and what difference it makes if it works. These four
answers become introduction arc.

## Falsifiable claims

State with each claim what would prove it wrong. Claim without falsifier
does not enter plan.

## Worked numerical example

Walk core mechanism with concrete numbers before any prose about it: inputs,
per-step values, outputs. Numbers cannot be worked: mechanism not understood
well enough to plan experiments around.

## Experiment plan

Per experiment: what runs, baseline it kills, metric that decides, compute
budget, failure criterion (result that sends plan back for revision).

## Prospective evidence ledger

Map every falsifiable claim to artifact path its experiment will write.
`design` run notes each as `to-run` claim before requesting `plan` gate,
renders this section from `check`; `write` run notes them in stage 2.

## Award assessment

Blocking weaknesses, lead differentiators, evidence gaps, per
`award-assessment`.
