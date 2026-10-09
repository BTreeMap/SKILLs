# Caveman Review Verb

Write terse, actionable review comments, one line per finding, ready to
paste. Review only: do not write fix, approve, request changes, or run
linters.

## Format

`L<line>: <tag>: <problem>. <fix>.`, or `<file>:L<line>: ...` for multi-file
diffs.

Tags, when findings are mixed:

- `bug:` broken behavior, will cause incident
- `risk:` works but fragile (race, missing null check, swallowed error)
- `nit:` style, naming, micro-optimization; author can ignore
- `q:` question needing answer

Plain-text tags canonical (fewer tokens); emoji markers optional decoration,
only when host renders them usefully.

Drop: "I noticed that...", "You might want to consider...", "This is just a
suggestion" (use `nit:`), per-comment praise (say it once at top), restating
what line does, hedging (unsure means `q:`).

Keep: exact line numbers, exact symbol names in backticks, concrete fix
(never "consider refactoring"), the why when fix is not obvious from
problem.

<examples for="review">
  <before>I noticed that on line 42 you're not checking if the user object is null before accessing the email property. This could potentially cause a crash. You might want to add a null check here.</before>
  <after>L42: bug: user can be null after .find(). Add guard before .email.</after>
  <after>L88-140: nit: 50-line fn does 4 things. Extract validate/normalize/persist.</after>
  <after>L23: risk: no retry on 429. Wrap in withBackoff(3).</after>
</examples>

## Auto-Clarity

Drop terse form for security findings (CVE-class bugs need full explanation
and reference), architectural disagreements (need rationale), onboarding
contexts where author needs the why. Write those as normal paragraph, then
resume terse for rest.
