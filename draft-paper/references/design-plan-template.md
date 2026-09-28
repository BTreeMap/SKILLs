# Design Plan

Stage 1 deliverable for the `design` verb. The human approves this before
any experiment runs.

## Scenario sketch

Name the actors, the scale, the workload, the present failure, and the
quantitative setting in concrete terms. Vague: "modern datacenters."
Concrete: "a 128-GPU training job's all-reduce on a 4-spine fabric where one
spine degrades 30%." Apply the practitioner-recognition test: a practitioner
in the area reads this and recognizes the setting as real. If they would
not, the scenario is not concrete enough to plan experiments around.

## Contradiction

Frame as a contradiction, mismatch, deployment gap, or unexplained
observation (`award-patterns` 1). Name the two things that should agree and
do not.

## Falsifiable claims

Each claim states what would prove it wrong. No claim without its falsifier.

## Worked numerical example

Walk the core mechanism with concrete numbers before any prose about it:
inputs, per-step values, outputs. If the numbers cannot be worked, the
mechanism is not understood well enough to plan experiments around.

## Experiment plan

Per experiment: what runs, the baseline it kills, the metric that decides,
the compute budget, and the failure criterion (what result sends the plan
back for revision).

## Prospective evidence ledger

Every falsifiable claim mapped to a planned artifact path, all marked
TO-RUN. This is the stage-2 deliverable for `design`: the mapping, not
measured numbers.

## Award assessment

Blocking weaknesses, lead differentiators, evidence gaps, per
`award-assessment`.
