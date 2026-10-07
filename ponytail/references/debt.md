# Ponytail Debt Verb

Harvest `ponytail:` comments into a ledger. Read and report only; change
nothing. To persist the ledger, ask first, then write it to a file (e.g.
`PONYTAIL-DEBT.md`).

## Scan

Grep the repository for comment markers, skipping `.git`, vendored
dependencies (e.g. `node_modules`), and build output; add other comment
prefixes the stack uses.

<commands for="scan">
grep -rnE '(#|//) ?ponytail:' .
</commands>

Each hit is one ledger row; the comment prefix keeps prose that merely
mentions the convention out of the ledger.

## Output

One row per marker, grouped by file:

<template for="ledger-row">
<file>:<line>, <what was simplified>. ceiling: <the limit named>. upgrade: <the trigger to revisit>.
</template>

Pull the ceiling and the trigger straight from the comment, which follows
`ponytail: <ceiling>, <upgrade path>`. For an owner per row, add
`git blame -L<line>,<line>`. Tag a marker naming no upgrade path or trigger
`no-trigger`: a rot risk.

End with `<N> markers, <M> with no trigger.` Nothing found:
`No ponytail: debt. Clean ledger.`
