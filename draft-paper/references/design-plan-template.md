# Design plan

Stage 1 deliverable for `design` and for `build` from a shaped idea, one
section per heading below. The human approves it before any experiment runs.

## Scenario sketch

Name the actors, the scale, the workload, the present failure, and the
quantitative setting in concrete terms. Apply the practitioner-recognition
test: a practitioner in the area reads the sketch and recognizes the setting
as real. If they would not, make the scenario concrete enough to plan
experiments around.

<examples for="scenario-sketch">
  <example>
    <before>modern datacenters</before>
    <after>a 128-GPU training job's all-reduce on a 4-spine fabric where one spine degrades 30%</after>
  </example>
</examples>

## Contradiction

Frame the work as a contradiction, mismatch, deployment gap, or unexplained
observation (evidence section 1 in `award-assessment`). Name the two things
that should agree and do not.

## Problem statement

Answer in plain language, without jargon: what you are trying to do; how it
is done today and where the limits are; what is new about your approach and
why it will succeed; who cares and what difference it makes if it works.
These four answers become the introduction arc.

## Falsifiable claims

State with each claim what would prove it wrong. A claim without its
falsifier does not enter the plan.

## Worked numerical example

Walk the core mechanism with concrete numbers before any prose about it:
inputs, per-step values, outputs. If the numbers cannot be worked, the
mechanism is not understood well enough to plan experiments around.

## Experiment plan

Per experiment: what runs, the baseline it kills, the metric that decides,
the compute budget, and the failure criterion (the result that sends the
plan back for revision).

## Prospective evidence ledger

Map every falsifiable claim to the artifact path its experiment will write.
A `design` run notes each as a `to-run` claim before requesting the `plan`
gate and renders this section from `check`; a `build` run notes them in
stage 2.

## Award assessment

Blocking weaknesses, lead differentiators, and evidence gaps, per
`award-assessment`.
