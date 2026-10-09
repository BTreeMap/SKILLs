# Analysis: Results and Statistics

Walk once per paper over every table and figure claims cite, then record
`walks` entry for `analysis`.

## Signalling questions

| Type | Question | Anchor or `missing` |
| --- | --- | --- |
| `variance` | Do results supporting main claim carry error bars, intervals, or test over several runs? | Table caption, or `missing: error bars for <table>` |
| `comparison` | Is "A beats B" backed by direct test of difference, or by two separate significance results? | Comparison sentence |
| `units` | Is unit of analysis the unit of independence (runs, subjects), with repeated measures or clustering handled? | The n sentence |
| `power` | Is sample large enough for effect claimed, or does extraordinary result rest on handful of items? | Sample sentence |
| `circular` | Were analyzed cases, features, or thresholds chosen using same data that reports effect? | Selection sentence |
| `multiplicity` | Are many tests or configurations reported without correction or stated selection rule? | Results sentence |
| `null` | Is non-significant or small difference read as "no effect" or "equivalent"? | Interpretive sentence |
| `causal` | Is causal language ("leads to", "because") used for observed association? | The sentence |
| `metric` | Do metrics measure claim (proxy standing in for target, one metric where claim needs two)? | Metric definition |

## Consistency reads

Numbers in abstract, text, tables, figures must agree. They differ: quote
both sides (`selective` or `reporting`, severity by size of gap).
Percentages must sum; means must sit inside reported ranges. On bounded
measure, standard deviation larger than half the mean flags non-normal
spread described as normal.

## Ultra: recomputation

Recompute every derivable number claims lean on: differences between rows,
relative improvements, averages over columns, totals. Do arithmetic on pad,
then object with both numbers quoted. Recomputed gap erasing headline
improvement is `fatal`.

## Severity

`fatal` when main result loses its support (no variance over gap smaller
than run-to-run noise, leaked or circular analysis); `major` when
interpretation changes; `minor` for presentation of otherwise sound numbers.
