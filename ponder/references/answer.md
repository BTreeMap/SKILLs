# Answer: sweep, check, draft

Load once no material question stays open; run steps in order.

## 1. Rival sweep

Sweep once for strongest contrary account: folk belief, older explanation,
or competing mechanism. Record scope, candidates, survivors as `sweeps`
entry. Empty scoped sweep establishes absence; valid result.

## 2. Check

<commands for="answer">
$R check "$S"
</commands>

At default `draft` view, `check` returns derived `sections`; `scaffold`
holding each close's stored premise and detail keyed by marker;
`violations`, lite-demoted ones under `advisories`; `hedges`; `markers`
table, `S1` onward, with class, title, url, plus `doi`, `arxiv_id`,
`authors`, `year`, `venue` where source carries them. Exits 0 even with
violations: read them; resolve every violation and every `open` leaf before
drafting. Lite mode: open leaf may remain; disclose it in Open section.

## 3. Draft once

Lead drafts once by transforming scaffold's rows; reuse premise and detail
written into closes. Render derived sections; add Boundary when answer flips
within scope.

| Section | Carries |
| --- | --- |
| Answer | Claim, first, in question's own register, from `retrieved` leaves |
| Chain | Reasoning path through `retrieved` leaves when it exceeds a few links; else collapses into answer's sentences |
| Rival | Every `refuted` premise and every sweep survivor, stated at its strongest |
| Boundary | Where answer flips within scope (band, version, workload) |
| Open | Each `unresolved` leaf with what was tried or why it was passed over |
| Sources | Check's table: marker, class, title, url; authors, year, venue where present |

Omit `retired` leaves. Absent Rival records empty sweep.

Bind markers to claims answer depends on; leave connective prose bare.

- `[Sn]` marks claim settled by its numbered ledger source.
- `[~]` marks conclusion composed from leaves.
- Hedge every leaf check lists under `hedges`; name class by stating claim
  as attributed evidence: "benchmarks report [S4]", "practitioner accounts
  hold [S6]".
- Strongest source in close sets leaf's entry in `hedges`: close holding
  `constitutive` or `attested` source, or two `measured` ones, never listed,
  whatever else it holds. Same rule per sentence by its own markers: hedge
  sentence and name its class unless its markers include `constitutive` or
  `attested` source or two `measured` ones, even inside leaf `hedges` does
  not list.

<template for="answer">
## Answer
<claim, plainly> [S1]. <derived conclusion> [~].

## Rival
The strongest contrary account: <premise at its strongest> [S3]. It fails
because <evidence> [S1].

## Boundary
Below <threshold> the answer flips: <flipped claim> [S4].

## Open
- <unresolved leaf question>: searched <what was tried>; status unresolved.

## Sources
- S1 (constitutive): <title>, <url>
- S3 (reported): <title>, <url>
</template>

## Handoffs

After delivery, offer each next step whose condition holds; name sibling,
verb, artifact to pass. Invoke none unasked.

- Answer needs scholarly record (survey, related work, priority claim):
  `/lit-review` with question; pass DOIs from source records as seeds.
- Answer became research plan: `/draft-paper design` with answer and its
  Sources section; pass this session's project to its `init --project`.
- Answer rests on qualitative text (interviews, tickets, open responses)
  read only in samples: `/thematic-analysis` on that corpus.
