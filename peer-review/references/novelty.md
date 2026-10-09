# Novelty: The Literature Check

Reviewer's own search, run through `/lit-review` at lite. Its corpus is the
only place novelty objection can point.

## Procedure

1. From `claims` list, write one lit-review question naming paper's core
   task and its claimed advances.
2. Build inclusion criteria admitting any work claiming same contribution or
   reporting on same task with comparable method; exclusion criteria drop
   surveys and unrelated tasks.
3. Run `/lit-review lite` with that protocol. Queries: one per claim in
   paper's own terms plus one synonym variant per claim, six to twelve in
   total; pass `--to-year` as paper's year. Snowball backward from paper's
   two most-cited references when reachable.
4. Screen to works overlapping a claim. Read at abstract level; read full
   text for any work that would carry `major` objection.
5. `attach` lit-review session to this one. Every corpus key with year
   before paper's is now citable as `prior`; later key is refused. Key
   sharing paper's year passes with advisory; confirm prior work was public
   first before keeping objection at major.
6. Walk questions below; note `walks` entry for `novelty`.

Ultra adds forward snowball from every key cited as `prior`, so rebuttal
already published is in corpus before review says "predates".

## Signalling questions

| Kind | Question | Anchor and prior |
| --- | --- | --- |
| `prior` | Does corpus work make same contribution, in substance, before this paper? | Claim sentence; prior key; text states what overlaps and what differs |
| `first` | Is "first", "novel", or "no prior work" claim contradicted by dated corpus work? | Claim sentence; prior key |
| `sota` | Is state-of-the-art claim made without strongest result available at paper's date? | Claim sentence; prior key holding stronger result, with its number |
| `positioning` | Is directly relevant corpus work absent from paper's related work or comparisons? | `missing: citation of <key>` with `where: related work`; prior key |

Objection text states overlap in prior work's own terms and difference that
remains. "X (2021) routes prompts with a bandit over the same candidate set;
the present paper adds a learned prior, which the claim of being first does
not survive" is the shape.

## Severity

`major` when `first` or `sota` claim contradicted, or `prior` work covers
main contribution; `minor` for positioning gaps leaving contribution intact;
`question` when overlap depends on reading of prior work abstract cannot
settle.
