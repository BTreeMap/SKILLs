# Verb: help

Print a compact reference card. Do not load other verb files or language
profiles for this.

## Card

Render the following, adapted to what the user asked about:

<help_card>
pl-theorist - one discipline, eight verbs, per-language cost models

Usage: /pl-theorist [verb] [files-or-code] [language]
No verb: refactor when changing existing code, build when writing new code.

Verbs
  design    Types-first domain model, effect boundary, complexity budget. No code.
  build     New code: domain types first, pure core, thin shell, tests included.
  refactor  Behavior-preserving rewrite toward functional style. (default)
  review    Read-only ranked findings on a diff/PR: partiality, invalid states,
            effect leaks, complexity, stale idioms.
  audit     Read-only repo/module ledger, ranked by severity x reach.
  test      Law-derived tests: fold laws, roundtrips, rejection paths, oracles.
  teach     PL explanation of a design, calibrated to human or model audience.
  help      This card.

Languages (cost model loaded on demand)
  Python, JavaScript, TypeScript, Rust, Go, Haskell, C, C++, Java, Kotlin,
  C#, Bash, GitHub Actions YAML. Others: derived from repo config, with
  stated uncertainty.

Always on (kernel)
  Optimization order: correctness > totality/effects > time-space complexity
  > native idioms at the configured standard > composition > surface elegance.
  Invalid states unrepresentable; parse, don't validate; pure core, thin
  shell; complexity stated against real sizes; structures from the
  cost-signal table; library first; measured claims only.
</help_card>

## Output Contract

The card, nothing else. If the user asked a specific question ("which verb
for X?"), answer it in one line above the card.
