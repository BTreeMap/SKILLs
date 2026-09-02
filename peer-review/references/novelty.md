# Novelty: The Literature Check

The reviewer's own search, run through `/lit-review` at lite. Its corpus
is the only place a novelty objection can point.

## Procedure

1. From the `claims` list, write one lit-review question naming the
   paper's core task and its claimed advances.
2. Build inclusion criteria that admit any work claiming the same
   contribution or reporting on the same task with a comparable method;
   exclusion criteria drop surveys and unrelated tasks.
3. Run `/lit-review lite` with that protocol. Queries: one per claim in
   the paper's own terms plus one synonym variant per claim, six to twelve
   in total; pass `--to-year` as the paper's year. Snowball backward from
   the paper's two most-cited references when reachable.
4. Screen to the works that overlap a claim. Read at abstract level;
   read full text for any work that would carry a `major` objection.
5. `link` the lit-review session to this one. Every corpus key with a year
   before the paper's is now citable as `prior`; a key sharing the year
   passes with an advisory; a later key is refused.
6. Walk the questions below; note a `walks` entry for `novelty`.

Ultra adds a forward snowball from every key cited as `prior`, so a
rebuttal already published is in the corpus before the review says
"predates".

## Signalling questions

| Kind | Question | Anchor and prior |
| --- | --- | --- |
| `prior` | Does a corpus work make the same contribution, in substance, before this paper? | The claim sentence; the prior key; text states what overlaps and what differs |
| `first` | Is a "first", "novel", or "no prior work" claim contradicted by a dated corpus work? | The claim sentence; the prior key |
| `sota` | Is a state-of-the-art claim made without the strongest result available at the paper's date? | The claim sentence; the prior key holding the stronger result, with its number |
| `positioning` | Is a directly relevant corpus work absent from the paper's related work or comparisons? | `missing: citation of <key>` with `where: related work`; the prior key |

## Severity

`major` when a `first` or `sota` claim is contradicted, or a `prior` work
covers the main contribution; `minor` for positioning gaps that leave the
contribution intact; `question` when the overlap depends on a reading of
the prior work the abstract cannot settle. Lack of state-of-the-art results
alone is no objection (see `firewall`).

## Text discipline

The objection text states the overlap in the prior work's own terms and
the difference that remains. "X (2021) routes prompts with a bandit over
the same candidate set; the present paper adds a learned prior, which the
claim of being first does not survive" is the shape.
