# Caveman Stats Verb

Display an honest savings card. Edit nothing, write nothing, and change no
level. NEVER fabricate or estimate per-session token counts: this skill has
no session-log instrumentation.

The card shows:

- Upstream benchmark: the caveman project measured a median 65 percent
  output-token reduction with full technical accuracy retained. Source:
  https://github.com/JuliusBrussee/caveman (benchmarks/ and
  docs/HONEST-NUMBERS.md).
- Rule overhead: the caveman rules themselves cost input tokens every turn
  (upstream default estimate: about 1,250 tokens per turn). Net savings =
  output saved minus rule overhead; short sessions or short answers can be
  net NEGATIVE. When they are, say so plainly and suggest turning caveman
  off for that workload.
- Local numbers: the only honest per-file figures here are the
  `chars_before`, `chars_after`, and `percent_smaller` fields the refactor
  verb's guard script reports on `apply`. Character deltas are not token
  deltas; label them as characters.
