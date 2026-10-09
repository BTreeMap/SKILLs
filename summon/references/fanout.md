# Verb: fanout

Partition open work, then run one send per bundle. Load `send` first: every
bundle ships full six-field brief defined there.

## Partition law

Bundles pairwise disjoint; their union is open work. Overlap is design
error, not redundancy: duplicates its share of fan's spend, buys nothing.
Enforce both axes in every bundle's bounds.

| Axis | Failure it prevents |
| --- | --- |
| Topic | Two delegates researching one question: duplicated spend, lost coverage. |
| Files | Two delegates writing one file: lost update, a correctness bug. |

## Bounds

Boundary names neighbouring agent's territory. Every bundle's bounds carry
all six lines. Session scratch directory harness shares across delegates is
file territory too: two delegates writing `notes.md` there lose an update,
so each bundle gets own subdirectory, named for bundle.

<template for="bounds">
BOUNDS
Your bundle: <the work this delegate closes>
Sibling territory, not yours: <the other bundles by name and subject>
On meeting sibling material: name it in one line under `handoffs`, do not follow it.
Files: you own <paths>. Do not write <paths>.
Scratch: write temporary files only under <scratch root>/<bundle name>/.
Spawning: no.
</template>

## Sizing and resumability

Size fan against spine's cited sizing and its concurrency cap; bundle too
small to justify a context goes back inline. Fanout not transactional, so
each brief closes own bundle without reference to another bundle's output;
dead bundle is re-sent alone.

## Joining returns

Returns arrive one per completion notification. Judge each under `review` on
arrival, then join. Lead owns coverage across bundles: reconcile handoff
lines, re-send only work no bundle claimed.

## Completion Checks

<checklist for="verb">
  <item>Bundles pairwise disjoint on topic and files; union is open work.</item>
  <item>Every bundle names neighbouring territory, carries refusal rule.</item>
  <item>Every bundle names owned and forbidden files and own scratch subdirectory.</item>
  <item>Each brief closes its bundle alone, so any one can be re-sent.</item>
  <item>Fan plus children fits concurrency cap.</item>
  <item>Handoff lines reconciled; unclaimed work named or re-sent.</item>
</checklist>
