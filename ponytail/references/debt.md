# Ponytail Debt Verb

Every deliberate ponytail shortcut is marked with a `ponytail:` comment
naming its ceiling and upgrade path. This verb collects them into one ledger
so deferrals stay visible.

## Scan

Grep the repository for comment markers, skipping `.git`, vendored
dependencies (e.g. `node_modules`), and build output:

<scan_command>
grep -rnE '(#|//) ?ponytail:' .
</scan_command>

Add other comment prefixes if the stack uses them. Each hit is one ledger
row; the comment prefix keeps prose that merely mentions the convention out
of the ledger.

## Output

One row per marker, grouped by file:

<ledger_row>
<file>:<line>, <what was simplified>. ceiling: <the limit named>. upgrade: <the trigger to revisit>.
</ledger_row>

The convention is `ponytail: <ceiling>, <upgrade path>`, so pull the ceiling
and the trigger straight from the comment. For an owner per row, add
`git blame -L<line>,<line>`.

Flag the rot risk: any `ponytail:` comment naming no upgrade path or trigger
gets a `no-trigger` tag; those silently rot.

End with `<N> markers, <M> with no trigger.`
Nothing found: `No ponytail: debt. Clean ledger.`

## Boundaries

Reads and reports only, changes nothing. To persist the ledger, ask first;
then write it to a file (e.g. `PONYTAIL-DEBT.md`).
