# Verb: review

Judge a change: read-only PL-lens review of a diff, PR, or file set, total
over its scope. This lens hunts unsound domain modeling and unsound cost.

## Pipeline

### 1. Scope and contract

Identify the exact changed or named code. Reconstruct its contract under the
kernel's Reading Existing Code, only as deeply as judging the categories
requires. Read callers when a finding depends on how the code is used.

### 2. Hunt by category

Sweep the whole scope once per row of the kernel's Finding Categories,
citing file and line for each hit.

### 3. Verify before reporting

Re-derive each candidate finding against the loaded profile's cost model and
the repository's conventions. An imperative loop that is the right backend
is sound; a missing `Result` where the repository's error channel is
exceptions is sound. Report only what survives.

## Output Contract

Ranked findings, most severe first, one line each:

`<file:line> - <category> - <violated law or bound> - <minimal fix shape>`

After the list: at most three lines naming what was checked and found sound
(so silence is distinguishable from omission). Findings and one-line fix
shapes are the whole deliverable; when the user asks to apply fixes, switch
to the `refactor` verb per finding.

## Completion Checks

<checklist for="verb">
  <item>The working tree is untouched.</item>
  <item>Every category was swept over the full scope or the skipped remainder is named.</item>
  <item>Every finding survived the cost-model and convention check.</item>
  <item>Findings are ranked by severity with file:line anchors.</item>
  <item>Sound areas are named so silence is meaningful.</item>
</checklist>
