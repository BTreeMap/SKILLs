# Verb: fanout

Partition the open work, then run one dispatch per bundle. Load `dispatch`
first: every bundle ships the full six-field brief defined there.

## Partition law

The bundles are pairwise disjoint and their union is the open work. Overlap
is a design error, not redundancy: it duplicates its share of the fan's
spend and buys nothing. Enforce both axes in every bundle's bounds.

| Axis | Failure it prevents |
| --- | --- |
| Topic | Two delegates researching one question: duplicated spend, lost coverage. |
| Files | Two delegates writing one file: a lost update, which is a correctness bug. |

## Bounds

A boundary names the neighbouring agent's territory. Every bundle's bounds
carry all five lines:

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

Returns arrive one per completion notification. Judge each under `review`
when it arrives, then join. The lead owns coverage across bundles: reconcile
the handoff lines, and re-dispatch only the work no bundle claimed.

## Completion Checks

<checklist for="verb">
  <item>Bundles are pairwise disjoint on topic and on files, and their union is the open work.</item>
  <item>Every bundle names the neighbouring territory and carries the refusal rule.</item>
  <item>Every bundle names its owned and forbidden files.</item>
  <item>Each brief closes its bundle alone, so any one can be re-dispatched.</item>
  <item>The fan plus its children fits the concurrency cap.</item>
  <item>Handoff lines were reconciled, and unclaimed work is named or re-dispatched.</item>
</checklist>
