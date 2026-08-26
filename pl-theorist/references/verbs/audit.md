# Verb: audit

Judge a codebase: whole-repository or module-level sweep through the PL
lens, producing a ranked ledger of modeling and cost debt. `review` is total
over a diff and gates a decision; `audit` samples by blast radius and ranks
a backlog. Read-only. Over-engineering and bloat route to `/ponytail audit`.

## Pipeline

### 1. Map the terrain

Enumerate the modules in scope (whole repo unless the user narrows it).
Identify the hot paths and trust boundaries first: entry points, request
handlers, parsers of external data, loops over unbounded collections, CI and
scripts. Budget depth by blast radius: a partial function in a request handler
outranks one in a test helper.

### 2. Sweep

Apply the `review` verb's category table across the scope, plus these
repo-scale categories only an audit can see:

| Repo-scale category | Signal |
| --- | --- |
| Duplicated machinery | Parallel bespoke `Result`/`Option`/monad frameworks, competing domain types for one concept |
| Inconsistent error channel | Exceptions here, result types there, sentinel returns elsewhere, for the same failure class |
| Missing shared boundary | The same untrusted format parsed ad hoc at many call sites instead of one decoder |
| Systemic complexity debt | The same accidental $O(n^2)$ pattern or linear re-scan idiom repeated across modules |
| Standard drift | The configured language standard rose (edition, target, `requires-python`) but the code still writes to the old one |
| Capability sprawl | Scripts and workflows holding broader permissions or secrets than their effects require |

Sample honestly: if scope forces sampling, choose by blast radius and name
every unexamined area.

### 3. Rank

Order findings by `severity x reach`: severity from the Optimization Order
(correctness above totality above cost above idiom), reach by how many call
sites or how much traffic the defect touches.

## Output Contract

A ledger table, ranked:

`| # | location | category | finding | suggested shape | effort (S/M/L) |`

Then: at most five lines summarizing systemic themes, the single
highest-value fix, and the unexamined areas. Fixing proceeds through
`refactor` or `build` invocations per ledger row.

## Completion Checks

<verb_checklist>
  <item>The working tree is untouched.</item>
  <item>Hot paths and trust boundaries were examined before peripheral code.</item>
  <item>Both diff-scale and repo-scale categories were swept.</item>
  <item>Unexamined areas are named explicitly.</item>
  <item>Ranking reflects severity times reach.</item>
</verb_checklist>
