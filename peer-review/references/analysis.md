# Analysis: Results and Statistics

Walk once per paper over every table and figure the claims cite; note a
`walks` entry for `analysis`.

## Signalling questions

| Kind | Question | Anchor or `missing` |
| --- | --- | --- |
| `variance` | Do results supporting a main claim carry error bars, intervals, or a test over several runs? | The table caption, or `missing: error bars for <table>` |
| `comparison` | Is "A beats B" backed by a direct test of the difference, or by two separate significance results? | The comparison sentence |
| `units` | Is the unit of analysis the unit of independence (runs, subjects), with repeated measures or clustering handled? | The n sentence |
| `power` | Is the sample large enough for the effect claimed, or is an extraordinary result resting on a handful of items? | The sample sentence |
| `circular` | Were the analyzed cases, features, or thresholds chosen using the same data that reports the effect? | The selection sentence |
| `multiplicity` | Are many tests or configurations reported without correction or a stated selection rule? | The results sentence |
| `null` | Is a non-significant or small difference read as "no effect" or "equivalent"? | The interpretive sentence |
| `causal` | Is causal language ("leads to", "because") used for an observed association? | The sentence |
| `metric` | Do the metrics measure the claim (a proxy standing in for the target, one metric where the claim needs two)? | The metric definition |

## Consistency reads

Numbers in the abstract, text, tables, and figures must agree. Quote both
sides when they differ (`selective` or `reporting`, severity by the size of
the gap). Percentages must sum, means must sit inside their reported ranges,
a standard deviation larger than half the mean on a bounded measure is a
flag for a non-normal spread described as normal.

## Ultra: recomputation

Recompute every derivable number the claims lean on: differences between
rows, relative improvements, averages over columns, totals. Do the
arithmetic on the pad, then object with both numbers quoted. A recomputed
gap that erases the headline improvement is `fatal`.

## Severity

`fatal` when the main result loses its support (no variance over a gap
smaller than run-to-run noise, a leaked or circular analysis); `major` when
the interpretation changes; `minor` for presentation of otherwise sound
numbers.
