# Claims: Extraction and the Support Test

The claim list is the review's target set. Fix it before the paper's
framing can move it.

## Extraction

Read the abstract, introduction, and conclusion only. Copy each
contribution sentence verbatim (cue phrases: "we propose", "we show", "our
contributions", "the first", "state of the art", "outperforms") into a
`claims` entry, one sentence each, under 60 words. Split a sentence that
bundles two results. Then read the rest of the paper.

Three to eight claims is the usual range. A paper with none stated in
those sections earns a `rhetoric` objection with `missing`.

## Signalling questions

Answer per claim while reading methods and results. A "no" is an objection
of the named kind; the hint names the evidence to quote.

| Kind | Question | Anchor |
| --- | --- | --- |
| `unsupported` | Does a method, proof, or experiment in this paper test this claim as worded? | The claim plus the nearest result that falls short |
| `overreach` | Does the claim's scope (all tasks, any model, in general) match the settings run? | The claim plus the settings table or dataset list |
| `speculation` | Is a mechanism stated as explanation when only the outcome was measured? | The explanatory sentence |
| `rhetoric` | Does the wording carry the weight (suggestive terms, math that restates prose, "significant" without a test)? | The sentence |

## Severity

`fatal` when the main claim has no test in the paper; `major` when a
headline claim exceeds its evidence; `minor` when a secondary claim does;
`question` when a re-read or the authors could settle it.

## Support test

For each claim, name in the objection text the section, table, or theorem
that would have to support it and what it shows instead. "Table 2 covers
two of the three benchmarks the abstract names" is an objection; "the
evidence is weak" is a pad note.
