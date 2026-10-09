# Ponytail Audit Verb

Judge codebase: scan whole tree for standing complexity, rank it, biggest
cut first. `review` guards what a change brings in; `audit` ranks what
already stands.

## Hunt

Dependencies stdlib or platform already ships, single-implementation
interfaces, factories with one product, wrappers that only delegate, files
exporting one thing, dead flags and config, hand-rolled stdlib.

## Output

One line per finding, ranked, tagged with cut tag from SKILL.md:
`<tag> <what to cut>. <replacement>. [path]`. End with
`net: -<N> lines, -<M> deps possible.` Nothing to cut: `Lean already. Ship.`
