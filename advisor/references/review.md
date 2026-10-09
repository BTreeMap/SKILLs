# Verb: review

Judge one artifact, a paper, proposal, draft, or result set, after the four
moves. Read-only: no file changes, no re-run of experiments. Output the
template alone.

* Direction: one paragraph saying where the project wins given the
  constitution, the currency table, and the envelope, which claim goes
  first, and what the lab stops doing. The target is the pattern's "what it
  has to show" row. It is a headline; `design` expands it into a plan.
* Sound: each line names what was checked; silence means unchecked.
* Routed: each piece of work outside the lens, one line, with the sibling
  the spine's Redirects name for it; the word none when nothing left the
  lens.

<template for="review">
# Review: <artifact title>
<path, URL, or DOI>; read <YYYY-MM-DD>.

## Constitution
<origin 1> + <origin 2> + ... [+ new]. Patterns: <rows from the spine's table>.
<one line per mechanism: the mechanism, its origin with citation, and its tag: as-is, tweaked (what changed), transferred (from where), or new>

## Setup
| element | paper | current practice | class | source |
| --- | --- | --- | --- | --- |
<one row per element: scale, topology, substrate, hardware, workload, baseline, metric>

## Envelope (assumption)
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
</template>

## Completion Checks

<checklist for="verb">
  <item>The template's header and sections appear in order with nothing around them.</item>
  <item>Routed names each item outside the lens with its sibling, or says none.</item>
  <item>Every mechanism line names an origin and a tag, or is tagged new.</item>
  <item>The Setup table has one row per element, each classed and sourced.</item>
  <item>Every claim carries a concrete instrument and a kill test.</item>
  <item>The Direction names the first claim to test and what stops.</item>
  <item>Nothing was edited.</item>
</checklist>
