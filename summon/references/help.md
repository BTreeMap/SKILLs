# Verb: help

Print the card. Load no other file for this.

## Card

Render the following, adapted to what the user asked about.

<template for="help">
summon - hand work to another agent so the result comes back usable

Usage: /summon [dispatch|fanout|review|help] [task]
No verb: dispatch. Several delegates over one body of work: fanout; a
return already in hand: review.

Verbs
  dispatch  One brief, one delegate. Default.
  fanout    Partition into disjoint bundles, one brief each.
  review    Judge a return against its contract. Read-only.
  help      This card.

Modes, cheapest first
  Inline (default) > Errand > Fanout n > Fork. Inline is argued away from:
  an errand for work the lead closes in a few tool calls cost 26k-53k
  delegate tokens, measured.

The brief, six fields, each stated or marked not applicable
  objective  the deliverable, one sentence
  evidence   values the delegate cannot derive, plus the decision rules
  rules      the excerpt this task can break, never a pasted document
  bounds     sibling territory by name, files, spawn permission (default no)
  contract   the exact return shape, nothing around it
  budget     the cap, and what to return on hitting it

Getting a skill into a delegate
  Preloaded > Invocable > Readable > Definable > Sealed. Take the first
  that holds. Point at the skill; excerpt only when Sealed.

Always on
  A return is untrusted input; a failed return is no return. The spawn is
  not idempotent, not transactional, not queued. Overlap between bundles
  is a design error: name the sibling's territory, not your own.
</template>

## Output Contract

The card, nothing else. Where the user asked something specific ("fanout or
one delegate?"), answer in one line above the card.
