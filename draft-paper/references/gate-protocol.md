# Gate protocol

Three gates: the research plan (end of stage 1), the evidence ledger (end of
stage 2), the final draft (end of stage 8). Nothing past a gate proceeds
without human approval.

## Request

At a gate, present:

1. The artifact under review (plan, ledger, or draft).
2. The `TRACE.jsonl` events since the previous gate (or run start), so the
   human sees what changed, not the whole history.
3. One explicit question naming the decision: approve the artifact, reject
   it, or revise it with notes.

## Decision

- Approve: record the human's reply text verbatim in `TRACE.jsonl` as a
  `gate-approved` event with a timestamp, then continue the run.
- Revise: record the notes as a `gate-rejected` event with the requested
  changes, return to the stage, and request the gate again.
- The agent never approves its own gate. Silence is never approval.

## Resume

To resume, verify the trace before trusting it, then read `RUN.md` (working
state) and the tail of `TRACE.jsonl` (what already happened). A failed
verification means the trace was edited or corrupted; restart the current
stage from the last `gate-approved` event.
