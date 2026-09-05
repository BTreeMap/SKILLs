# Verb: dispatch

Compose one brief, hand off one delegate, judge what comes back.

## 1. Settle the mode, then reach

Confirm against the spine's mode table that the work is not inline, and
state in one clause why not. Load `reach` when the delegate must follow a
named skill, and `harness` when delegating on a harness whose inheritance,
caps, or skill access you cannot state from memory.

## 2. Fill six fields

Every field is written as `Stated <value>` or `NotApplicable <reason>`.
Omission is never a spelling of "none": "no sibling agents, nothing off
limits" gets written out. This rule holds for every brief in this skill,
fanout bundles included.

| Field | Content |
| --- | --- |
| objective | One sentence naming the deliverable. |
| evidence | Resolved values and absolute paths the delegate cannot derive, plus the decision rules its judgments range over. |
| rules | The binding excerpt: a rule earns its place only if this task can break it. |
| bounds | The neighbouring agent's territory by name, files not to touch, and whether spawning is permitted (default: no). |
| contract | The exact return shape, with nothing before or after it. |
| budget | The tool-call or search cap, and what to return when it is hit. |

### evidence carries two kinds

A **value** the delegate cannot see, resolved by the lead. A **rule** the
delegate applies to evidence it already holds.

Measured: a list of options handed over without the selection rule produced
a wrong classification, confidently, and it flipped run to run. The same
delegate given the rule the evidence ranges over ("fix if a caller's
behavior changes, refactor if not") was correct and stable in 2 of 2 runs.
A rule that ranges over evidence the delegate lacks produces a confident
wrong answer, so resolve that evidence into a value instead.

Intent is never recoverable from the artifact. The caller owns why the work
is being done and states it here.

### rules: excerpt, never dump

Measured, n=3 per arm on one task: the full skill dumped into the prompt
broke its own 70-character subject rule in 2 of 3 runs and its own
no-preamble rule in 3 of 3, and its classification flipped between runs; a
six-rule excerpt broke neither rule in 3 of 3, at lower cost and zero tool
calls.

Cited mechanism: prompt-level compliance falls from 94% at one instruction
to 21% at ten, across ten models ("When Instructions Multiply", 2025);
reliability degrades with input length, and one distractor already hurts
(Chroma, "Context Rot", 2025). Four vendors cap the instruction bundle
independently.

### contract owns cost and shape

Of five measured arms, the one given a return contract returned exactly the
artifact at zero tool calls; the four without wrapped it in prose to strip.

## 3. Write the prose

Load `/caveman` and write the brief under it; then load `/humanize` and
sweep the draft. Both loads happen, whatever register the lead already
writes in: a hedge or a pleasantry is an instruction that binds nothing,
and every non-binding instruction competes with the binding ones for
compliance.

## 4. Hand it off

<template for="brief">
OBJECTIVE
<one sentence naming the deliverable>

EVIDENCE
<resolved values, absolute paths, and the decision rules>

RULES
<the binding excerpt, one rule per line>

BOUNDS
<neighbouring territory by name, or the words "no sibling agents">
<files not to touch, or the words "nothing off limits">
Spawning: no.
<what the harness itself injects, so it is not reported as injection>

CONTRACT
Return exactly:
<the shape, field by field, nothing before or after it>

BUDGET
<cap>. On hitting it, return what is settled and name what is open.
</template>

## 5. On return

Judge it under `review` before acting on it.

## Completion Checks

<checklist for="verb">
  <item>All six fields are present, each either stated or marked not applicable with its reason.</item>
  <item>Every judgment the delegate must make has either its evidence resolved or its decision rule stated.</item>
  <item>The rules field is an excerpt of what this task can break, not a pasted document.</item>
  <item>The contract names one return shape and forbids anything around it.</item>
  <item>Spawn permission is stated explicitly.</item>
  <item>The brief carries no hedge, pleasantry, or instruction that binds nothing.</item>
</checklist>
