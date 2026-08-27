# Answer: Sweep, Outline, Sections, and Markers

## The rival sweep

Once per run, after the last round (or straight after a settled probe)
and before drafting, sweep for the strongest account that contradicts the
emerging answer: the folk belief, the older explanation, the competing
mechanism. Record even an empty sweep as a `sweeps` entry in a `note`
batch (schema in the spine): what was checked, the candidates considered,
the survivors. An empty sweep with its scope named renders as a confident
absence. Survivors render in the Rival section beside every `refuted`
premise.

## Check first

Drafting starts from the script, never from transcript memory:

<answer_command>
uv run --script <skill-root>/scripts/ponder.py check <session>
</answer_command>

The check holds the derived section set, the numbered source table the
markers cite, every violation, and the hedge advisories. Resolve every
violation before drafting: close open leaves, run the missed sweep,
repair broken folds. The lead drafts alone, in one pass; parallel section
writing produces disjoint reports.

## Sections

Render exactly the sections the check derives, plus Boundary by your
own judgment. Absent sections are conclusions: a missing Rival section
says the sweep found nothing.

| Section | Carries |
| --- | --- |
| Answer | The claim, first, in the question's own register |
| Chain | The reasoning path when it exceeds a few links; else it collapses into the answer's sentences |
| Rival | Every `refuted` premise and every sweep survivor, stated at its strongest |
| Boundary | Where the answer flips within scope (band, version, workload) |
| Open | Each `unresolved` leaf with what was tried or why it was passed over |
| Sources | The check's table: marker, class, title, url |

These are Toulmin's claim, grounds, warrant, qualifier, and rebuttal
under reader-friendly names. `Retired` leaves render nowhere.

## Marker discipline

Markers bind to load-bearing claims only; connective prose stays bare.

- `[Sn]` after a claim a ledger source settles, using the check's
  numbering. No record, no marker, no claim stated as retrieved.
- `[~]` after a composition step: a conclusion derived from leaves rather
  than retrieved from any one of them. This is the warrant made explicit,
  the element arguments usually leave implied.
- Hedge every leaf the check lists under `hedges`, and name the class by
  stating the claim as attributed evidence: "benchmarks report [S4]",
  "practitioner accounts hold [S6]".

<answer_template>
## Answer
<claim, plainly> [S1]. <derived conclusion> [~].

## Rival
The strongest contrary account: <premise at its strongest> [S3]. It fails
because <evidence> [S1].

## Boundary
Below <threshold> the answer flips: <flipped claim> [S4].

## Open
- <unresolved leaf question>: searched, <what was tried>, nothing usable.

## Sources
- S1 (constitutive): <title>, <url>
- S3 (reported): <title>, <url>
</answer_template>
