# Verb: review

Read-only findings on a screen, component, diff, or pull request. Default
verb for existing work. Change nothing.

## Procedure

1. **Reconstruct the intended read.** Infer the surface, audience, and
   primary goal from the artifact itself. State it. Most findings are
   disagreements between the intended read and the built result, and naming
   the read makes them arguable rather than assertive.
2. **Walk the flow before the pixels.** Trace the user's path to the primary
   goal and count the friction budget as built. Interaction failures
   outrank visual ones and are found by walking, not by reading style
   declarations.
3. **Pass in five sweeps**, in this order. Do not interleave; each sweep has
   a different attention mode.
   * **Logic**: does behavior follow from appearance, is state complete, are
     errors preventable, is work preserved, does the keyboard path exist?
   * **Hierarchy**: does the eye land on the right thing first, does
     grayscale still read, is contrast spent on what matters?
   * **Consistency**: one accent, one radius scale, one spacing scale, one
     type scale, one icon family, one theme, across the whole surface?
   * **Voice**: does the copy say what happened and what to do next, is
     anything fabricated, does anything read as generated?
   * **Structure**: does this re-implement something the repository already
     has, do prop APIs admit invalid combinations, is any closed set handled
     with a catch-all, do imports point downward, does an effect synchronize
     derivable state?
4. **Verify before reporting.** For each candidate finding, name the
   concrete failure: the input, state, or viewport where it breaks and what
   the user sees. Drop any finding without a failure scenario.
5. **Rank and report.** Most severe first.

## Severity

| Level | Meaning |
| --- | --- |
| Broken | The user cannot complete the goal, loses work, or is excluded. Blocking. |
| Friction | The goal is reachable but costs unjustified steps, waits, or confusion. |
| Incoherent | Violates the surface's own established system. Cheap to fix, compounds if not. |
| Generated | Reads as templated output. Undermines credibility without breaking function. |

## Finding format

<finding_format>
**{severity}** {location}: {one-sentence defect}
Fails when: {concrete input, state, or viewport, and what the user sees}
Fix: {the specific change, not a principle}
</finding_format>

## Rules

* Every finding names a fix that is a change, not a restatement of the rule.
* Report the whole-surface failures the diff cannot show: the section that
  inverts theme, the second accent introduced three commits ago, the layout
  family used four times. Reviewing only the changed lines misses the
  failures that matter most.
* Keep findings focused on the current design. Put a fundamentally different
  direction in one top finding instead of rewriting every finding beneath it.
* Say plainly when the work is good. A review that manufactures findings to
  appear thorough trains the reader to ignore reviews.
* State what was not checked: interactions requiring a running application,
  real data volumes, assistive-technology behavior, and anything else
  outside the artifact.

## Completion checks

<validation_checklist>
  <item>The intended read was reconstructed and stated before any finding.</item>
  <item>The flow was walked and the built friction budget counted.</item>
  <item>All five sweeps ran in order and whole-surface consistency was checked, not just the diff.</item>
  <item>The repository was checked for an existing implementation of anything the diff re-implements.</item>
  <item>Every finding carries a concrete failure scenario and a specific fix.</item>
  <item>Findings are ranked by severity and preferences were dropped.</item>
  <item>Coverage limits are stated and nothing was modified.</item>
</validation_checklist>
