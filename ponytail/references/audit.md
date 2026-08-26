# Ponytail Audit Verb

Judge the codebase: scan the whole tree for standing complexity. `review`
guards what a change brings in; `audit` ranks what already stands, biggest
cut first.

## Tags

- `delete:` dead code, unused flexibility, speculative feature. Replacement: nothing.
- `stdlib:` hand-rolled thing the standard library ships. Name the function.
- `native:` dependency or code doing what the platform already does. Name the feature.
- `yagni:` abstraction with one implementation, config nobody sets, layer with one caller.
- `shrink:` same logic, fewer lines. Show the shorter form.

## Hunt

Dependencies the stdlib or platform already ships, single-implementation
interfaces, factories with one product, wrappers that only delegate, files
exporting one thing, dead flags and config, hand-rolled stdlib.

## Output

One line per finding, ranked: `<tag> <what to cut>. <replacement>. [path]`.
End with `net: -<N> lines, -<M> deps possible.`
Nothing to cut: `Lean already. Ship.`

## Boundaries

Scope: over-engineering and complexity only; correctness bugs, security
holes, and performance route to `/pl-theorist audit`. A single smoke test
or `assert`-based self-check is the ponytail minimum and stays. Lists
findings; applying the cuts is `/ponytail refactor`.
