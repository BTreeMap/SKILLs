# Ponytail Examine Verb

Judge diff for smuggled complexity, and only that.

## Format

One line per finding, tagged with cut tag from SKILL.md:
`L<line>: <tag> <what>. <replacement>.`, or `<file>:L<line>: ...` for
multi-file diffs.

**Example: examine**

Before: This EmailValidator class might be more complex than necessary, have
you considered whether all these validation rules are needed at this stage?

After: L12-38: stdlib: 27-line validator class. "@" in email, 1 line, real
validation is the confirmation mail.

After: L4: native: moment.js imported for one format call.
Intl.DateTimeFormat, 0 deps.

After: repo.py:L88: yagni: AbstractRepository with one implementation.
Inline it until a second one exists.

After: L52-71: delete: retry wrapper around an idempotent local call.
Nothing replaces it.

After: L30-44: shrink: manual loop builds dict. dict(zip(keys, values)), 1
line.

## Scoring

End with `net: -<N> lines possible.` Nothing to cut: say
`Lean already. Ship.` and stop.
