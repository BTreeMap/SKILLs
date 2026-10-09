# Verb: audit

Judge codebase: read-only, whole-repository or module-level sweep through PL
lens, producing ranked ledger of modeling and cost debt. `examine` is total
over diff and gates decision; `audit` samples by blast radius and ranks
backlog.

## Pipeline

### 1. Map the terrain

Enumerate modules in scope (whole repo unless user narrows it). Identify hot
paths and trust boundaries first: entry points, request handlers, parsers of
external data, loops over unbounded collections, CI and scripts. Budget
depth by blast radius: partial function in request handler outranks one in
test helper.

### 2. Sweep

Apply kernel's Finding Categories across scope, plus these repo-scale
categories only audit can see:

| Repo-scale category | Signal |
| --- | --- |
| Duplicated machinery | Parallel bespoke `Result`/`Option`/monad frameworks, competing domain types for one concept |
| Inconsistent error channel | Exceptions here, result types there, sentinel returns elsewhere, for same failure class |
| Missing shared boundary | Same untrusted format parsed ad hoc at many call sites instead of one decoder |
| Systemic complexity debt | Same accidental $O(n^2)$ pattern or linear re-scan idiom repeated across modules |
| Standard drift | Configured language standard rose (edition, target, `requires-python`) but code still writes to old one |
| Capability sprawl | Scripts and workflows holding broader permissions or secrets than their effects require |

Scope forces sampling: choose by blast radius; name every unexamined area.

### 3. Rank

Order findings by `severity x reach`: severity from Optimization Order
(correctness above totality above cost above idiom), reach by how many call
sites or how much traffic defect touches.

## Output Contract

Ledger table, ranked:

`| # | location | category | finding | suggested shape | effort (S/M/L) |`

Then at most five lines: systemic themes, highest-value fix, unexamined
areas. Fixing proceeds through `refactor` or `write` invocations per ledger
row.

## Completion Checks

- Working tree untouched.
- Hot paths and trust boundaries examined before peripheral code.
- Both diff-scale and repo-scale categories swept.
- Unexamined areas named.
- Ranking reflects severity times reach.
