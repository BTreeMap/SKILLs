# Verb: examine

Takes screen, component, diff, or pull request (default verb for existing
work); returns ranked findings. Read-only: change nothing.

## Procedure

1. **Reconstruct intended read.** Infer surface, audience, primary goal from
   artifact itself; state it. Most findings are disagreements between
   intended read and built result; naming read makes them arguable.
2. **Walk flow before pixels.** Trace user's path to primary goal; count
   friction budget as built. Interaction failures outrank visual ones, found
   by walking flow.
3. **Run five sweeps** in `signs`, in listed order. Do not interleave them;
   each needs different attention mode. Check repository for existing
   implementation of anything diff re-implements.
4. **Check beyond diff.** Report whole-surface failures changed lines cannot
   show, per spine's consistency gotcha: second accent introduced three
   commits ago, layout family used four times.
5. **Verify before reporting.** For each candidate finding, name concrete
   failure: input, state, or viewport where it breaks and what user sees.
   Drop any finding without failure scenario.
6. **Rank and report**, most severe first.

## Severity

Rate each finding on Severity scale in `signs`.

## Finding format

```markdown
**{severity}** {location}: {one-sentence defect}
Fails when: {concrete input, state, or viewport, and what the user sees}
Fix: {the specific change, not a principle}
```

## Rules

* Every finding names fix that is concrete change.
* Keep findings on current design. Fundamentally different direction: one
  top finding only.
* Say plainly when work is good. Review manufacturing findings to appear
  thorough trains reader to ignore reviews.
* State what was not checked: interactions requiring running application,
  real data volumes, assistive-technology behavior, anything else outside
  artifact.

## Completion checks

- Intended read reconstructed and stated before any finding.
- Flow walked; built friction budget counted.
- All five sweeps ran in order; whole-surface consistency checked beyond
  diff.
- Repository checked for existing implementation of anything diff
  re-implements.
- Every finding carries concrete failure scenario and specific fix.
- Findings ranked by severity; preferences dropped.
- Coverage limits stated; nothing modified.
