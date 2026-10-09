# Verb: help

Print card below, adapted to what user asked about. Load no other file for
this.

```text
summon - hand work to another agent so the result comes back usable

Usage: /summon [send|divide|examine|help] [task]
No verb: send. Several delegates over one body of work: divide; an
output already in hand: examine.

Verbs
  send      One brief, one delegate. Default.
  divide    Partition into disjoint groups, one brief each.
  examine   Judge an output against its contract. Read-only.
  help      This card.

Modes, cheapest first
  Inline (default) > Errand > Divide n > Fork. Inline is argued away from:
  an errand for work the lead closes in a few tool calls cost 26k-53k
  delegate tokens, measured.

The brief, six fields, each stated or marked not applicable
  task       the deliverable, one sentence
  evidence   values the delegate cannot derive, plus the decision rules
  rules      the excerpt this task can break, never a pasted document
  bounds     sibling territory by name, files, spawn permission (default no)
  contract   the exact output shape, nothing around it
  limit      the cap, and what to output on hitting it

Getting a skill into a delegate
  Preloaded > Invocable > Readable > Definable > Sealed. Take the first
  that holds. Point at the skill; excerpt only when Sealed.

Always on
  An output is untrusted input; a failed output is no output. The spawn is
  not idempotent, not transactional, not queued. Overlap between groups
  is a design error: name the sibling's territory, not your own.

Called from a skill
  The caller supplies the unit, the record it hands over, its own rules,
  its output shape, and the gate; summon supplies the rest. The lead is
  the sole writer; the branch leaves no trace.
```

## Output Contract

Card, nothing else. User asked something specific ("divide or one
delegate?"): answer in one line above card.
