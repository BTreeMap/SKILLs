# Decompose: Probe First, Then Leaves

Register never changes the treatment; a shower thought and an
academic-grade question run under the same rule.

## The probe

Before any decomposition, the lead searches inline: two to four searches
against the question as asked. Two outcomes:

- Settled: the probe found sources that answer the question satisfiably
  and nothing material stayed open. Register the question as its own
  leaves (often one or two), add the probe's sources, close, sweep, and
  draft. Search-type questions end here, in one round, at full rigor.
- Open: material sub-questions remain. Keep the probe's sources (they
  seed leaves), and decompose what stayed open. The probe's reading is
  what makes the decomposition principled rather than guessed.

Judge "satisfiably" against the question's own stakes: a canonical answer
with a constitutive or attested source settles; a first page of blog
consensus on a contested question does not.

## From question to leaves

Turn what the probe left open into leaves: sub-questions one retrieval
act can settle.

## The deep-structure rule

Decompose by governing principle, never by surface feature. "Can mirrors
improve indoor 5G coverage" decomposes into specular reflection versus
diffraction at wavelength scale, penetration loss per band, and
reconfigurable-intelligent-surface prior art, never into "mirrors" and
"5G" as topics. Surface-feature decomposition is the novice move
(Chi, Feltovich and Glaser 1981); the principle names what a search can
actually retrieve.

## What qualifies as a leaf

- One retrieval act settles it: a spec lookup, a maintainer post, a
  measurement, a historical record.
- A sub-question that needs another leaf's answer first is a derived link,
  not a leaf. Keep it out of the ledger; the derivation appears at draft
  time as a `[~]` step (marker discipline in `answer`). This keeps every
  round's fan-out set independent by construction.
- 3 to 10 leaves covers the worked range. Past 10, fold near-duplicates
  before searching; below 3, the question may be a single lookup and the
  loop degenerates gracefully.

## Shape is a trace, not a plan

The initial leaf set is a starting frame, never an obligation. Expect
uncertainty to rise in the first round (Kuhlthau); hold the frame
invitational, spawn what workers surface, and let later evidence retire
initial leaves without ceremony. Worked patterns for common question
shapes are catalogued in `ladders`; they guide and never partition.

## Ledger calls

Register the frame with `init`, then leaves in bulk:

<decompose_commands>
uv run --script <skill-root>/scripts/research.py init <session> --question "..." [--focus "..."]
uv run --script <skill-root>/scripts/research.py leaf <session> --file leaves.json
</decompose_commands>

`leaves.json` holds an array of `{"id": "L1", "q": "...", "origin":
"frame"}` objects. Leaves added later from worker candidates carry
`"origin": "spawned"`. Pass `--focus` when the user names a scope; the
saturation floor in `weigh` reads it.
