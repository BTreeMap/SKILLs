# Ponytail Refactor Verb

Apply the cuts. Rewrite existing code onto the highest ladder rung that
holds, behavior preserved. This is the verb that edits: `review` lists,
`refactor` deletes.

## Pipeline

1. Read the target and every caller first.
2. Climb the ladder per site: delete dead flexibility, then reuse the
   codebase's own helpers, then stdlib, then native platform features, then
   an installed dependency, then the same logic in fewer lines.
3. Preserve behavior: values, ordering, errors, effect order, and public
   names stay.
4. Mark a cut with a real ceiling with a `ponytail:` comment naming the
   ceiling and upgrade path.
5. Leave the check: existing tests still pass, and non-trivial surviving
   logic keeps one minimal runnable check.

## Output

The diff, then at most three short lines:
`cut: [X], replaced by [Y]. net: -N lines.`
Nothing to cut: say `Lean already.` and change nothing.

## Boundaries

Over-engineering only. A correctness or modeling rewrite routes to
`/pl-theorist refactor`.
