# Verb: review

Read-only PL-lens review of a diff, PR, or file set. Produce ranked findings;
change nothing. This lens hunts unsound domain modeling and unsound cost, not
bloat.

## Pipeline

### 1. Scope and contract

Identify the exact changed or named code. Reconstruct its contract as in
`refactor` step 1, but only deeply enough to judge the categories below. Read
callers when a finding depends on how the code is used.

### 2. Hunt by category

Sweep the scope once per category, citing file and line for each hit:

| Category | Signal |
| --- | --- |
| Partiality | Unchecked index/unwrap/cast, non-exhaustive match, "unreachable" by optimism |
| Representable invalid states | Boolean/nullable field bags encoding a state machine, sentinel values, stringly typed domains |
| Unparsed input | Untrusted data flowing past the boundary without one decoder/smart constructor |
| Effect leakage | I/O, clock, randomness, or mutation inside a nominally pure core; instrumentation buried or erased |
| Unlawful algebra | Fold reassociated without associativity, `map` changing cardinality, `reduce` where `sum`/`any`/`find` is the law |
| Complexity | Accidental $O(n^2)$: membership/join/extremum re-scanned in a loop; structure mismatched to the operation mix (kernel cost-signal table) |
| Unbounded effects | Missing backpressure, unbounded fan-out or queues, retries without idempotency, resources outliving scope, lost cancellation |
| Stale surface | Conditional ladders or legacy idioms where the configured standard already provides guards, let-chains, records, or sealed variants |

### 3. Verify before reporting

Re-derive each candidate finding against the loaded profile's cost model and
the repository's conventions. An imperative loop is not a finding when it is
the honest backend; a missing `Result` is not a finding when the repository's
error channel is exceptions. Drop what does not survive.

## Output Contract

Ranked findings, most severe first, one line each:

`<file:line> - <category> - <violated law or bound> - <minimal fix shape>`

After the list: at most three lines naming what was checked and found sound
(so silence is distinguishable from omission). No edits, no patches beyond
one-line fix shapes, unless the user explicitly asks to apply fixes - then
switch to the `refactor` verb per finding.

## Completion Checks

<verb_checklist>
  <item>No file was modified.</item>
  <item>Every category was swept over the full scope or the skipped remainder is named.</item>
  <item>Every finding survived the cost-model and convention check.</item>
  <item>Findings are ranked by severity with file:line anchors.</item>
  <item>Sound areas are named so silence is meaningful.</item>
</verb_checklist>
