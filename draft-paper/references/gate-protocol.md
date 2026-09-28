# Gate Protocol

Owns the approval handshake. Three gates: the research plan (end of stage
1), the evidence ledger (end of stage 2), the final draft (end of stage 8).
Nothing past a gate proceeds without human approval.

## Request

At a gate, the agent presents:

1. The artifact under review (plan, ledger, or draft).
2. The `TRACE.jsonl` events since the previous gate (or run start), so the
   human sees what changed, not the whole history.
3. One explicit question naming the decision: approve the artifact, reject
   it, or revise it with notes.

## Decision

- **Approve.** The human's reply text is recorded verbatim in `TRACE.jsonl`
  as a `gate-approved` event with a timestamp. The run continues.
- **Revise.** The notes are recorded as a `gate-rejected` event with the
  requested changes; the agent returns to the stage and re-requests.
- The agent never approves its own gate. Silence is never approval.

## Resume

A run resumes by reading `RUN.md` (working state) and the tail of
`TRACE.jsonl` (what already happened). Verify the trace before trusting it;
a failed verification means the trace was edited or corrupted, and the run
restarts its current stage from the last `gate-approved` event.
