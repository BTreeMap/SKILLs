# Report: The Review Document

Draft once from `check` output, sweep draft with `/humanize` in embedded
mode, then `cite-check` file. Every objection in draft is mark `[On]` from
scaffold's `fatal`, `major`, `minor`, or `questions` lists; every claim is
`[Cn]`. Withdrawn, unanchored, undated records stay out.

## Template

<template for="review">
# Review: <title>

Version reviewed: <date>. Level: <level>. Reading: <pages> pages of
extracted text; corpus: <n records, or none>.

## Summary
<two or three sentences: task, method, main claims [C1] [C2], and the
evidence offered. No praise, no verdict here.>

## Claims
| Mark | Claim | Page | Verdict |
| --- | --- | --- | --- |
| C1 | <verbatim, trimmed> | p. 1 | contested by O1, O3 |

## Fatal
<none, or one paragraph per mark: what is wrong, where (page and
quote), what would resolve it.>

## Major
[O1] (design/selective, p. 2) "We report the best run over five seeds."
Report mean and spread over all seeds; the 12-point gain is within
run-to-run range if the spread is typical for this benchmark.

## Minor
...

## Questions for the authors
<the `questions` list, each answerable in a rebuttal.>

## Points that did not affect the recommendation
<writing, figures, formatting; no marks.>

## Recommendation
<the derived verdict verbatim from check>, confidence <band> (<walked
banks>; corpus <attached or none>; echo ratio <r>).

This review was produced by an agent following the peer-review skill;
every quoted anchor and prior-work key was verified by its script.
</template>

## Rules

- One paragraph per objection: what is wrong, where (page and quoted anchor,
  or missing item and its expected place), concrete resolving action: table,
  run, citation, restated scope.
- Order within severity by claim it contests, main claim first.
- Summary is descriptive. Strengths appear only where later objection needs
  contrast ("the ablation in Table 3 isolates the encoder; no such ablation
  covers the router").
- Numbers come from paper or corpus, carry their page or key.
- No author names, affiliations, or venue guesses anywhere.
- Hedge by evidence class: `question` reads as question; objection whose
  prior work was read at abstract level says so.

## Handoffs

After delivery, offer next step whose condition holds. Invoke none unasked.

- Paper is user's own and review answers it: `/draft-paper rebut` with
  review file as reviews input; start its run with
  `--verb rebut --state reviews`.
