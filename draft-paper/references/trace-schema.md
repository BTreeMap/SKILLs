# Trace schema

`TRACE.jsonl` is the append-only run log, beside `RUN.md` in the run
directory: one JSON object per line, coarse events only (stage transitions,
gate decisions, experiments, claims, major decisions). Put fine-grained work
notes in `RUN.md`, which the agent may rewrite freely; the agent only
appends to the trace.

## Event vocabulary

`run-started`, `stage-entered`, `stage-exited`, `gate-requested`,
`gate-approved`, `gate-rejected`, `experiment-registered`,
`experiment-completed`, `claim-added`, `claim-dropped`, `decision`.

## Entry shape

<template for="trace-entry">
<![CDATA[
{
  "seq": 1,
  "t": "2026-09-28T07:00:00+00:00",
  "run_id": "<slug>",
  "event": "stage-entered",
  "detail": {"stage": 1}
}
]]>
</template>

`seq` starts at 1 and counts appended events with no gaps. `t` is an ISO
8601 timestamp. `run_id` is constant across the file. `detail` holds the
event payload. A gate approval records the human's verbatim reply text and
its timestamp inside `detail`.

## Verification

Verify with the bundled script; `SKILL.md` defines the binding and the
output contract.

<commands>
<![CDATA[
$R trace verify <run-dir>
]]>
</commands>

The verifier checks that each line parses, that the required fields are
present with the right shapes, that `seq` runs 1..N with no gaps or repeats,
that every `event` is in the vocabulary, that `run_id` never changes, that
no unknown fields appear, and that the file stays under the kernel's event
cap. It exits 0 with a JSON summary, or 1 naming the first defect.

## Integrity

The log is append-only by convention. Verification detects corruption,
truncation, and reordering; it cannot detect a rewrite that preserves the
schema, such as an edit that renumbers `seq` cleanly. Treat a failed
verification as a compromised trace: restart the current stage from the last
`gate-approved` event.
