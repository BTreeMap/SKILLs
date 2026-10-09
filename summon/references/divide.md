# Verb: divide

Partition open work, then run one send per group. Load `send` first: every
group ships full six-field brief defined there.

## Partition law

Groups pairwise disjoint; their union is open work. Overlap is design error,
not redundancy: duplicates its share of division's spend, buys nothing.
Enforce both axes in every group's bounds.

| Axis | Failure it prevents |
| --- | --- |
| Topic | Two delegates researching one question: duplicated spend, lost coverage. |
| Files | Two delegates writing one file: lost update, a correctness bug. |

## Bounds

Boundary names neighbouring agent's territory. Every group's bounds carry
all six lines. Session scratch directory harness shares across delegates is
file territory too: two delegates writing `notes.md` there lose an update,
so each group gets own subdirectory, named for group.

<template for="bounds">
BOUNDS
Your group: <the work this delegate closes>
Sibling territory, not yours: <the other groups by name and subject>
On meeting sibling material: name it in one line under `handoffs`, do not follow it.
Files: you own <paths>. Do not write <paths>.
Scratch: write temporary files only under <scratch root>/<group name>/.
Spawning: no.
</template>

## Sizing and resumability

Size division against spine's cited sizing and its concurrency cap; group
too small to justify a context goes back inline. Spawns not transactional,
so each brief closes own group without reference to another group's output;
dead group is re-sent alone.

## Joining outputs

Outputs arrive one per completion notification. Judge each under `examine`
on arrival, then join. Lead owns coverage across groups: reconcile handoff
lines, re-send only work no group claimed.

## Completion Checks

<checklist for="verb">
  <item>Groups pairwise disjoint on topic and files; union is open work.</item>
  <item>Every group names neighbouring territory, carries refusal rule.</item>
  <item>Every group names owned and forbidden files and own scratch subdirectory.</item>
  <item>Each brief closes its group alone, so any one can be re-sent.</item>
  <item>Groups plus children fit concurrency cap.</item>
  <item>Handoff lines reconciled; unclaimed work named or re-sent.</item>
</checklist>
