# Caveman Stats Verb

Display honest savings card. Edit nothing, write nothing, change no level.
NEVER fabricate or estimate per-session token counts: this skill has no
session-log instrumentation.

Card shows:

- Upstream benchmark: caveman project measured median 65 percent
  output-token reduction with full technical accuracy retained. Source:
  https://github.com/JuliusBrussee/caveman (benchmarks/ and
  docs/HONEST-NUMBERS.md).
- Rule overhead: caveman rules themselves cost input tokens every turn
  (upstream default estimate: about 1,250 tokens per turn). Net savings =
  output saved minus rule overhead; short sessions or short answers can be
  net NEGATIVE. When they are, say so plainly, suggest turning caveman off
  for that workload.
- Local numbers: only honest per-file figures here are `chars_before`,
  `chars_after`, `percent_smaller` fields refactor verb's guard script
  reports on `apply`. Character deltas are not token deltas; label them as
  characters.
