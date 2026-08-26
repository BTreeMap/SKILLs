# Weigh: Join, Stopping, and the Rival Sweep

After admitting a round, decide: another round, a re-decomposition, or
the draft.

## Checkpoint and the leave-or-stay call

Close each round with a checkpoint carrying the round's declared search
count (sum of workers' `searches_spent`):

<weigh_commands>
uv run --script <skill-root>/scripts/research.py status <session> --checkpoint --searches <n> --label round-<k>
</weigh_commands>

The yield table compares new sources per search across rounds. Falling
yield is the patch-leaving signal (Pirolli and Card's foraging model):
weigh leaving the current decomposition, either by re-framing the weak
leaves or by stopping. The script keeps the count; the call is yours.
Floors and ceilings:

- Two unproductive rounds: stop, close remaining open leaves as
  `unresolved`, and draft.
- Saturation never fires before one round past the declared focus.
- Rounds run one to three. Needing a fourth means the decomposition is
  wrong, not the search: return to `decompose` and re-frame.
- A one-round question has no comparison; the floor rule alone governs.

## Frame discipline

Treat anomalous evidence as a test of the frame, not noise (Klein's
data-frame theory: explaining anomalies away, "preserving", is the named
failure). Before closing any leaf `retrieved`, name what evidence would
have refuted it; a close that nothing could refute is premature closure,
the "thinking stops when the diagnosis is made" failure. A refuted
premise is a finding, not a miss: close it `refuted` with the premise,
and it feeds the Rival account.

## The rival sweep

Once per run, after the last round and before drafting, sweep for the
strongest account that contradicts the emerging answer: the folk belief,
the older explanation, the competing mechanism. Record it even when
empty; the obligation is to look, never to find, and an empty sweep with
its scope named is a legitimate outcome that renders as a confident
absence rather than a forgotten check.

<sweep_command>
uv run --script <skill-root>/scripts/research.py sweep <session> --checked "what was examined" [--candidates a,b] [--survivors a]
</sweep_command>

Survivors render in the Rival section beside every `refuted` premise.
