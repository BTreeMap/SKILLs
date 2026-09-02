# Report: The Review Document

Draft once from `check` output, then `cite-check` the file. Every objection
in the draft is a marker `[On]` from the scaffold's `fatal`, `major`,
`minor`, or `questions` lists; every claim is `[Cn]`. Withdrawn,
unanchored, and undated records stay out.

## Template

<review_template>
# Review: <title>

Version reviewed: <date>. Level: <level>. Reading: <pages> pages of
extracted text; corpus: <n records, or none>.

## Summary
<two or three sentences: task, method, main claims [C1] [C2], and the
evidence offered. No praise, no verdict here.>

## Claims
| Marker | Claim | Page | Verdict |
| --- | --- | --- | --- |
| C1 | <verbatim, trimmed> | p. 1 | contested by O1, O3 |

## Fatal
<none, or one paragraph per marker: what is wrong, where (page and
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
<writing, figures, formatting; no markers.>

## Recommendation
<the derived verdict verbatim from check>, confidence <band> (<walked
banks>; corpus <linked or none>; echo ratio <r>).

This review was produced by an agent following the peer-review skill;
every quoted anchor and prior-work key was verified by its script.
</review_template>

## Rules

- One paragraph per objection: what is wrong, where (page and quoted
  anchor, or the missing item and its expected place), and what resolves
  it. The resolving action is concrete: a table, a run, a citation, a
  restated scope.
- Order within a severity by the claim it contests, main claim first.
- The Summary is descriptive. Strengths appear only where a later objection
  needs the contrast ("the ablation in Table 3 isolates the encoder; no
  such ablation covers the router").
- Numbers come from the paper or the corpus and carry their page or key.
- No author names, affiliations, or venue guesses anywhere.
- Hedge by evidence class: a `question` reads as a question; an objection
  whose prior work was read at abstract level says so.
- Sweep the draft with `/humanize` in embedded mode before `cite-check`.
