# Verb: examine

Judge one artifact (paper, proposal, draft, result set) after four moves.
Read-only: no file changes, no re-run of experiments. Output template alone.

* Direction: one paragraph saying where project wins given constitution,
  currency table, range; which claim goes first; what lab stops doing.
  Target is pattern's "what it has to show" row. Headline only; `design`
  expands it into plan.
* Sound: each line names what was checked; silence means unchecked.
* Routed: each piece of work outside lens, one line, with sibling spine's
  Redirects name for it; word none when nothing left lens.

**Template: examine**

```markdown
# Review: <artifact title>
<path, URL, or DOI>; read <YYYY-MM-DD>.

## Constitution
<origin 1> + <origin 2> + ... [+ new]. Patterns: <rows from the spine's table>.
<one line per mechanism: the mechanism, its origin with citation, and its tag: as-is, tweaked (what changed), transferred (from where), or new>

## Setup
| element | paper | current practice | class | source |
| --- | --- | --- | --- | --- |
<one row per element: scale, topology, substrate, hardware, workload, baseline, metric>

## Range (assumption)
<compute, network, data, people, money: one line each; "unknown" where unknown>

## Claims
1. <claim>. Instrument: <row from the spine's table, made concrete>. Kill test: <outcome that ends it>.
2. ...

## Direction
<one paragraph>

## Sound
<at most three lines>

## Routed
<one line per item: the work and its sibling skill in slash form, or the word none>

## Ask
<the one question whose answer changes the direction, or the word none>
```

## Completion Checks

- Template's header and sections in order, nothing around them.
- Routed names each item outside lens with its sibling, or says none.
- Every mechanism line names origin and tag, or is tagged new.
- Setup table: one row per element, each classed and sourced.
- Every claim carries concrete instrument and kill test.
- Direction names first claim to test and what stops.
- Nothing edited.
