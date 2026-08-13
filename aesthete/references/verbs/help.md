# Aesthete: quick reference

Design mastermind for user interfaces. Reads the brief, commits to a
direction, enforces logic and craft, refuses generated defaults.

## Invocation

`/aesthete [verb] [target] [surface]`

Without a verb: `build` for new work, `review` for existing work.

## Verbs

| Verb | Use it to |
| --- | --- |
| design | Commit to a direction and composition plan before code |
| build | Implement an interface (default for new work) |
| review | Report findings on a screen or diff, changing nothing (default for existing work) |
| audit | Sweep a whole product and rank remediation by leverage |
| redesign | Rework an existing interface, evolving or overhauling |
| teach | Explain a design decision so the next one is self-served |
| help | This card |

One verb file per invocation. Multi-verb work runs as sequential
invocations.

## Surfaces

| Surface | Covers |
| --- | --- |
| marketing | Landing, portfolio, editorial, campaign, docs home |
| product | App UI, dashboard, table, form, wizard, settings, console |

## Dials

Set after the read, stated with reasons, never left at baseline.

| Dial | 1 | 10 | Baseline |
| --- | --- | --- | --- |
| VARIANCE | Perfect symmetry | Deliberate asymmetry | 6 |
| MOTION | Static | Choreographed | 5 |
| DENSITY | Gallery | Cockpit | 4 |

## The read

One line, before anything else:
`Reading this as: {surface} for {audience}, optimizing for {goal}, with a
{aesthetic} language, built on {stack}.`

## What always applies

* Every element names the job it does for the user, or it is deleted.
* One accent, one radius scale, one spacing scale, one type scale, one icon
  family, one theme, across the whole surface.
* Full state sets: rest, hover, focus-visible, active, disabled, loading,
  error, success. Containers add empty and partial.
* Response budgets: instant under 100ms, no spinner under 400ms, determinate
  progress past 1s, background past 10s.
* Undo outranks confirm. User work is never lost. The URL reflects state.
* Zero U+2014 characters in user-visible copy.
* Nothing fabricated: no invented metrics, logos, testimonials, or fake
  product screenshots.

## Reference map

Loaded on demand, one level deep, never chained.

| Need | File |
| --- | --- |
| Verb procedure | `references/verbs/{verb}.md` |
| Surface profile | `references/surfaces/{marketing,product}.md` |
| Craft decision | `references/craft/{typography,color,layout,motion,interaction,platform}.md` |
| Official design systems | `references/systems.md` |
| Generated-output catalogue | `references/tells.md` |
| Ship gate | `references/preflight.md` |
