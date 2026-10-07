# Ponytail Refactor Verb

Apply the cuts: rewrite existing code onto the highest ladder rung that
holds, behavior preserved. This is the verb that edits: `review` and `audit`
list, `refactor` deletes.

## Pipeline

1. Read the target and every caller first.
2. Climb the ladder from SKILL.md per site. On existing code, rung 1 means
   deleting dead flexibility and rung 6 means the same logic in fewer lines.
3. Preserve behavior: values, ordering, errors, effect order, and public
   names stay.
4. Mark a cut with a real ceiling with a `ponytail:` comment naming the
   ceiling and upgrade path.
5. Leave the check: existing tests still pass, and non-trivial surviving
   logic keeps one minimal runnable check.

## Output

The diff, then at most three short lines:
`cut: [X], replaced by [Y]. net: -N lines.` Nothing to cut: say
`Lean already.` and change nothing.
