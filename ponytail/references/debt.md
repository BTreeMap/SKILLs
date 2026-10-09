# Ponytail Debt Verb

Harvest `ponytail:` comments into ledger. Read and report only; change
nothing. To persist ledger, ask first, then write it to a file (e.g.
`PONYTAIL-DEBT.md`).

## Scan

Grep repository for comment markers, skipping `.git`, vendored dependencies
(e.g. `node_modules`), build output; add other comment prefixes the stack
uses.

```bash
grep -rnE '(#|//) ?ponytail:' .
```

Each hit is one ledger row; comment prefix keeps prose merely mentioning the
convention out of ledger.

## Output

One row per marker, grouped by file:

**Template: ledger-row**

```text
<file>:<line>, <what was simplified>. ceiling: <the limit named>. upgrade: <the trigger to revisit>.
```

Pull ceiling and trigger straight from comment, which follows
`ponytail: <ceiling>, <upgrade path>`. Owner per row: add
`git blame -L<line>,<line>`. Tag marker naming no upgrade path or trigger
`no-trigger`: rot risk.

End with `<N> markers, <M> with no trigger.` Nothing found:
`No ponytail: debt. Clean ledger.`
