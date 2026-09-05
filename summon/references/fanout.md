# Verb: fanout

Partition the open work, then run one dispatch per bundle. Load `dispatch`
first: every bundle ships a full six-field brief, and the fields are
defined there.

## Partition law

The bundles are pairwise disjoint and their union is the open work.
Overlap is a design error, not redundancy.

Two disjointness axes, both enforced in every bundle's bounds:

| Axis | Failure it prevents |
| --- | --- |
| Topic | Two delegates researching one question: duplicated spend, lost coverage. |
| Files | Two delegates writing one file: a lost update, which is a correctness bug. |

## Boundary text

Naming your own bundle is not a boundary. Naming the neighbouring agent's
territory is.

Measured, one pair per arm: two bundles named but unboundaried duplicated 5
of 8 techniques (62.5%), yielding 11 unique results from 16 slots. The same
two bundles plus about 60 words naming the neighbouring bundle's territory
and the refusal rule duplicated 0 of 8, yielding 16 from 16, at identical
per-agent cost (within 2%). Each boundaried delegate's handoff list named
the neighbour's material by name, so the refusal fired rather than the
boundary being ignored.

Every bundle's bounds carry all five lines:

<template for="bounds">
BOUNDS
Your bundle: <the work this delegate closes>
Sibling territory, not yours: <the other bundles by name and subject>
On meeting sibling material: name it in one line under `handoffs`, do not follow it.
Files: you own <paths>. Do not write <paths>.
Spawning: no.
</template>

## Sizing and resumability

Size the fan against the spine's cited sizing and its concurrency cap; a
bundle too small to justify a context goes back inline. A fanout is not
transactional, so each brief closes its own bundle without reference to
another bundle's output, and a dead bundle re-dispatches alone.

## Joining returns

Returns arrive one per completion notification; capture telemetry at each
arrival. Judge each under `review`, then join. The lead owns coverage
across bundles: reconcile the handoff lines, and re-dispatch only the work
no bundle claimed.

## Completion Checks

<checklist for="verb">
  <item>Bundles are pairwise disjoint on topic and on files, and their union is the open work.</item>
  <item>Every bundle names the neighbouring territory and carries the refusal rule.</item>
  <item>Every bundle names its owned and forbidden files.</item>
  <item>Each brief closes its bundle alone, so any one can be re-dispatched.</item>
  <item>The fan plus its children fits the concurrency cap.</item>
  <item>Handoff lines were reconciled, and unclaimed work is named or re-dispatched.</item>
</checklist>
