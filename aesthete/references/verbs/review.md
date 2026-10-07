# Verb: review

Takes a screen, component, diff, or pull request (the default verb for
existing work) and returns ranked findings. Read-only: change nothing.

## Procedure

1. **Reconstruct the intended read.** Infer the surface, audience, and
   primary goal from the artifact itself, and state it. Most findings are
   disagreements between the intended read and the built result; naming the
   read makes them arguable.
2. **Walk the flow before the pixels.** Trace the user's path to the primary
   goal and count the friction budget as built. Interaction failures outrank
   visual ones and are found by walking the flow.
3. **Run the five sweeps** the spine defines, in the order listed. Do not
   interleave them; each needs a different attention mode. Check the
   repository for an existing implementation of anything the diff
   re-implements.
4. **Check beyond the diff.** Report the whole-surface failures the changed
   lines cannot show, per the spine's consistency gotcha: the second accent
   introduced three commits ago, the layout family used four times.
5. **Verify before reporting.** For each candidate finding, name the
   concrete failure: the input, state, or viewport where it breaks and what
   the user sees. Drop any finding without a failure scenario.
6. **Rank and report**, most severe first.

## Severity

| Level | Meaning |
| --- | --- |
| Broken | The user cannot complete the goal, loses work, or is excluded. Blocking. |
| Friction | The goal is reachable but costs unjustified steps, waits, or confusion. |
| Incoherent | Violates the surface's own established system. Cheap to fix, compounds if not. |
| Generated | Reads as templated output. Undermines credibility without breaking function. |

## Finding format

<template for="finding">
**{severity}** {location}: {one-sentence defect}
Fails when: {concrete input, state, or viewport, and what the user sees}
Fix: {the specific change, not a principle}
</template>

## Rules

* Every finding names a fix that is a concrete change.
* Keep findings on the current design. Put a fundamentally different
  direction in one top finding only.
* Say plainly when the work is good. A review that manufactures findings to
  appear thorough trains the reader to ignore reviews.
* State what was not checked: interactions requiring a running application,
  real data volumes, assistive-technology behavior, and anything else
  outside the artifact.

## Completion checks

<checklist>
  <item>The intended read was reconstructed and stated before any finding.</item>
  <item>The flow was walked and the built friction budget counted.</item>
  <item>All five sweeps ran in order and whole-surface consistency was checked beyond the diff.</item>
  <item>The repository was checked for an existing implementation of anything the diff re-implements.</item>
  <item>Every finding carries a concrete failure scenario and a specific fix.</item>
  <item>Findings are ranked by severity and preferences were dropped.</item>
  <item>Coverage limits are stated and nothing was modified.</item>
</checklist>
