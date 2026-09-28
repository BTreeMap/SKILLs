# Run Template

Owns the agent's working state. At intake the agent creates
`<run-dir>/RUN.md` from the template below and `<run-dir>/TRACE.jsonl` (see
`trace-schema`). `RUN.md` is a scratchpad: the agent rewrites it freely as
the run evolves. It is never shown to the user unless asked.

Keep the fixed headers; put anything else under them.

<template for="RUN.md">
<![CDATA[
# Run: <slug>

## Status
- Verb:
- Format:
- Venue:
- Updated:

## Stage
- Current stage:
- Stage goal:
- Blocked on:

## Decisions
- <date>: <decision> (<why>)

## Open threads
- <thread>: <what is unresolved>

## Next
- <next concrete step>
]]>
</template>

## Resume

After interruption or compaction, read `RUN.md` for working state and the
tail of `TRACE.jsonl` for what already happened, then continue from `Next`.
Verify the trace first (see `trace-schema`); a failed verification means the
trace was edited or corrupted.
