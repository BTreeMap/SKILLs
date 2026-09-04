# Ponytail Review Verb

Judge the diff for smuggled complexity, and only that. One line per
finding: location, what to cut, what replaces it. The diff's best outcome
is getting shorter.

## Format

`L<line>: <tag> <what>. <replacement>.`, or `<file>:L<line>: ...` for
multi-file diffs.

Tags:

- `delete:` dead code, unused flexibility, speculative feature. Replacement: nothing.
- `stdlib:` hand-rolled thing the standard library ships. Name the function.
- `native:` dependency or code doing what the platform already does. Name the feature.
- `yagni:` abstraction with one implementation, config nobody sets, layer with one caller.
- `shrink:` same logic, fewer lines. Show the shorter form.

## Examples

<review-examples>
  <invalid>This EmailValidator class might be more complex than necessary, have you considered whether all these validation rules are needed at this stage?</invalid>
  <valid>L12-38: stdlib: 27-line validator class. "@" in email, 1 line, real validation is the confirmation mail.</valid>
  <valid>L4: native: moment.js imported for one format call. Intl.DateTimeFormat, 0 deps.</valid>
  <valid>repo.py:L88: yagni: AbstractRepository with one implementation. Inline it until a second one exists.</valid>
  <valid>L52-71: delete: retry wrapper around an idempotent local call. Nothing replaces it.</valid>
  <valid>L30-44: shrink: manual loop builds dict. dict(zip(keys, values)), 1 line.</valid>
</review-examples>

## Scoring

End with the only metric that matters: `net: -<N> lines possible.`
Nothing to cut: say `Lean already. Ship.` and stop.

## Boundaries

Scope: over-engineering and complexity only; correctness bugs, security
holes, and performance route to `/pl-theorist review`. A single smoke test
or `assert`-based self-check is the ponytail minimum and stays. Lists
findings; applying the cuts is `/ponytail refactor`.
