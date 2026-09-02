# Design: Study Design and Execution

Walk once per paper; note a `walks` entry for `design` with what was ruled
out. Pick the profile by study type, then answer every question.

## Profiles

| Study type | Questions to add |
| --- | --- |
| Randomized trial | The five bias domains below in full: randomization, deviation, attrition, measurement, selective |
| Observational or benchmark study | Same domains, with "assignment" replacing randomization |
| ML or systems experiment | `baseline`, `ablation`, `data`, `reporting` with the reproducibility items |
| Theory paper | Route to `claims`: every theorem's assumptions stated, every proof present or sketched with the full version located |

## Signalling questions

| Kind | Question | Anchor or `missing` |
| --- | --- | --- |
| `control` | Is there a comparison condition that isolates the manipulation? | The design sentence, or `missing: control condition` |
| `assignment` | Were units assigned to conditions by a stated process, and were groups comparable at baseline? | The assignment sentence or the baseline table |
| `deviation` | Did the intervention as run match the intervention as described (protocol, hyperparameters, prompts)? | The methods sentence versus the appendix or code note |
| `attrition` | Are excluded runs, dropped samples, or missing outcomes counted and explained? | The exclusion sentence, or `missing: exclusion counts` |
| `measurement` | Is the outcome measured the same way across conditions, by a party blind to condition where that matters? | The metric definition |
| `selective` | Are results chosen by direction, size, or significance (best run, best seed, best checkpoint, subset of tasks)? | The selection sentence |
| `baseline` | Are baselines tuned with the same budget and search as the proposed method, and are they the strongest available at the paper's date? | The tuning sentence; a stronger baseline needs a corpus key via `novelty` |
| `ablation` | Is each component's contribution separated, so the source of the gain is identified? | The ablation table, or `missing: ablation of <component>` |
| `data` | Are the datasets adequate and appropriate for the claim (size, domain, leakage between train and test, contamination)? | The data sentence |
| `reporting` | Are splits, hyperparameter ranges and selection, run counts, seeds, and compute stated? | `missing: <item>` with `where` |

## Reproducibility items

For `reporting`, check each: model and algorithm description; assumptions;
train/validation/test splits; excluded data and preprocessing; hyperparameter
range and selection method; exact number of runs; central tendency and
variation; compute per result; code or data location. One `reporting`
objection may carry several missing items in its text.

## Severity

`fatal` when the design cannot test the main claim (no control, leaked test
set); `major` when a flaw plausibly changes the headline result (selective
reporting, untuned baselines, unidentified gain source); `minor` for
reporting gaps that re-running would close.
