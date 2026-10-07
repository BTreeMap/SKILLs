# Ponytail Review Verb

Judge the diff for smuggled complexity, and only that.

## Format

One line per finding, tagged with a cut tag from SKILL.md:
`L<line>: <tag> <what>. <replacement>.`, or `<file>:L<line>: ...` for
multi-file diffs.

<examples for="review">
  <before>This EmailValidator class might be more complex than necessary, have you considered whether all these validation rules are needed at this stage?</before>
  <after>L12-38: stdlib: 27-line validator class. "@" in email, 1 line, real validation is the confirmation mail.</after>
  <after>L4: native: moment.js imported for one format call. Intl.DateTimeFormat, 0 deps.</after>
  <after>repo.py:L88: yagni: AbstractRepository with one implementation. Inline it until a second one exists.</after>
  <after>L52-71: delete: retry wrapper around an idempotent local call. Nothing replaces it.</after>
  <after>L30-44: shrink: manual loop builds dict. dict(zip(keys, values)), 1 line.</after>
</examples>

## Scoring

End with `net: -<N> lines possible.` Nothing to cut: say
`Lean already. Ship.` and stop.
