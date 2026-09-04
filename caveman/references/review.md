# Caveman Review Mode

Write review comments terse and actionable. One line per finding: location,
problem, fix.

## Format

`L<line>: <tag>: <problem>. <fix>.`, or `<file>:L<line>: ...` for
multi-file diffs.

Tags (when findings are mixed):

- `bug:` broken behavior, will cause an incident
- `risk:` works but fragile (race, missing null check, swallowed error)
- `nit:` style, naming, micro-optimization; author can ignore
- `q:` a question that needs an answer

Plain-text tags canonical (fewer tokens); emoji markers optional decoration
only when the host renders them usefully.

Drop: "I noticed that...", "You might want to consider...", "This is just a
suggestion" (use `nit:`), per-comment praise (say it once at the top),
restating what the line does, hedging (unsure means `q:`).

Keep: exact line numbers, exact symbol names in backticks, a concrete fix
(never "consider refactoring"), and the why when the fix is not obvious
from the problem.

## Examples

<examples for="review">
  <before>I noticed that on line 42 you're not checking if the user object is null before accessing the email property. This could potentially cause a crash. You might want to add a null check here.</before>
  <after>L42: bug: user can be null after .find(). Add guard before .email.</after>
  <after>L88-140: nit: 50-line fn does 4 things. Extract validate/normalize/persist.</after>
  <after>L23: risk: no retry on 429. Wrap in withBackoff(3).</after>
</examples>

## Auto-Clarity

Drop terse form for: security findings (CVE-class bugs need a full
explanation and reference), architectural disagreements (need rationale),
and onboarding contexts where the author needs the why. Write those as a
normal paragraph, then resume terse for the rest.

## Boundaries

Reviews only: does not write the fix, approve, request changes, or run
linters. Output comments ready to paste. One-shot: the active intensity
level is untouched. Complements `/ponytail`'s review mode, which
hunts over-engineering; this mode compresses any review's phrasing.
