# Design: Study Design and Execution

Walk once per paper; note `walks` entry for `design` with what was ruled
out. Pick profile by study type, then answer every question.

## Profiles

| Study type | Questions to add |
| --- | --- |
| Randomized trial | Five bias domains below in full: randomization, deviation, attrition, measurement, selective |
| Observational or benchmark study | Same domains, "assignment" replacing randomization |
| ML or systems experiment | `baseline`, `ablation`, `data`, `reporting` with reproducibility items |
| Theory paper | Route to claims bank: every theorem's assumptions stated, every proof present or sketched with full version located |

## Signalling questions

| Kind | Question | Anchor or `missing` |
| --- | --- | --- |
| `control` | Is there comparison condition isolating manipulation? | Design sentence, or `missing: control condition` |
| `assignment` | Were units assigned to conditions by stated process; groups comparable at baseline? | Assignment sentence or baseline table |
| `deviation` | Did intervention as run match intervention as described (protocol, hyperparameters, prompts)? | Methods sentence versus appendix or code note |
| `attrition` | Are excluded runs, dropped samples, or missing outcomes counted and explained? | Exclusion sentence, or `missing: exclusion counts` |
| `measurement` | Is outcome measured same way across conditions, by party blind to condition where that matters? | Metric definition |
| `selective` | Are results chosen by direction, size, or significance (best run, best seed, best checkpoint, subset of tasks)? | Selection sentence |
| `baseline` | Are baselines tuned with same budget and search as proposed method, and strongest available at paper's date? | Tuning sentence; stronger baseline needs corpus key via `novelty` |
| `ablation` | Is each component's contribution separated, so gain's source is identified? | Ablation table, or `missing: ablation of <component>` |
| `data` | Are datasets adequate and appropriate for claim (size, domain, leakage between train and test, contamination)? | Data sentence |
| `reporting` | Are splits, hyperparameter ranges and selection, run counts, seeds, compute stated? | `missing: <item>` with `where` |

## Reproducibility items

For `reporting`, check each: model and algorithm description; assumptions;
train/validation/test splits; excluded data and preprocessing;
hyperparameter range and selection method; exact number of runs; central
tendency and variation; compute per result; code or data location. One
`reporting` objection may carry several missing items in its text.

## Severity

`fatal` when design cannot test main claim (no control, leaked test set);
`major` when flaw plausibly changes headline result (selective reporting,
untuned baselines, unidentified gain source); `minor` for reporting gaps
re-running would close.
