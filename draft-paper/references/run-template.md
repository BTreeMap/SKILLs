# Run template

At intake, create `<run-dir>/RUN.md` from the template below and
`<run-dir>/TRACE.jsonl` per `trace-schema`. `RUN.md` is the agent's
scratchpad: rewrite it freely as the run evolves, and show it to the user
only when asked.

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

After interruption or compaction, verify the trace first (`trace-schema`); a
failed verification means the trace was edited or corrupted. Then read
`RUN.md` for working state and the tail of `TRACE.jsonl` for what already
happened, and continue from `Next`.
