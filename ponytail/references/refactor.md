# Ponytail Refactor Verb

Apply cuts: rewrite existing code onto highest ladder rung that holds,
behavior preserved. This verb edits: `examine` and `audit` list, `refactor`
deletes.

## Pipeline

1. Read target and every caller first.
2. Climb ladder from SKILL.md per site. On existing code, rung 1 means
   deleting dead flexibility; rung 6 means same logic in fewer lines.
3. Preserve behavior: values, ordering, errors, effect order, public names
   stay.
4. Mark cut with real ceiling with `ponytail:` comment naming ceiling and
   upgrade path.
5. Leave the check: existing tests still pass; non-trivial surviving logic
   keeps one minimal runnable check.

## Output

Diff, then at most three short lines:
`cut: [X], replaced by [Y]. net: -N lines.` Nothing to cut: say
`Lean already.` and change nothing.
