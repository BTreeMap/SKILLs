# Caveman Stats Mode

Display an honest savings card when invoked. One-shot: change no level,
write nothing.

## What to show

- Upstream benchmark: the caveman project measured a median 65 percent output-token reduction with full technical accuracy retained. Source: https://github.com/JuliusBrussee/caveman (benchmarks/ and docs/HONEST-NUMBERS.md).
- Rule overhead: the caveman rules themselves cost input tokens every turn (upstream default estimate: about 1,250 tokens per turn). Net savings = output saved minus rule overhead; short sessions or short answers can be net NEGATIVE. When they are, say so plainly and suggest turning caveman off for that workload.
- Local numbers: the only honest per-file figures here are the `CHARS: X -> Y` lines the compress mode's guard script prints. Character deltas are not token deltas; label them as characters.

## Honesty Boundary

NEVER fabricate or estimate per-session token counts: this skill has no
session-log instrumentation, and an LLM guessing its own token usage is
exactly the dishonesty this card exists to avoid. Real per-session
measurement requires external tooling (the upstream project ships a
session-log hook for Claude Code); point there instead of inventing numbers.

## Boundaries

One-shot display. Edits nothing, changes no level.
