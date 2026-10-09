# Verb: examine

Judge change: read-only PL-lens examination of diff, PR, or file set, total
over its scope.

## Pipeline

### 1. Scope and contract

Identify exact changed or named code. Reconstruct its contract under
kernel's Reading Existing Code, only as deeply as judging categories
requires. Read callers when finding depends on how code is used.

### 2. Hunt by category

Sweep whole scope once per row of kernel's Finding Categories, citing file
and line for each hit.

### 3. Verify before reporting

Re-derive each candidate finding against loaded profile's cost model and
repository's conventions. Imperative loop that is right backend: sound.
Missing `Result` where repository's error channel is exceptions: sound.
Report only what survives.

## Output Contract

Ranked findings, most severe first, one line each:

`<file:line> - <category> - <violated law or bound> - <minimal fix shape>`

After list: at most three lines naming what was checked and found sound (so
silence is distinguishable from omission). Findings and one-line fix shapes
are whole deliverable; user asks to apply fixes: switch to `refactor` verb
per finding.

## Completion Checks

- Working tree untouched.
- Every category swept over full scope, or skipped remainder named.
- Every finding survived cost-model and convention check.
- Findings ranked by severity with file:line anchors.
- Sound areas named so silence is meaningful.
