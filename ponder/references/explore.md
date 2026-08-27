# Explore: Decompose, Bundle, Weigh

Loaded once, when the probe leaves material questions open. Covers the
whole gather-weigh loop: framing leaves, bundling them for workers,
admitting rounds, and deciding when to stop.

## From question to leaves

Load `framing` before constructing leaves. Apply its moves to the question
and the probe records; its ready-frame checks are the entrance condition
for decomposition.

Turn what the probe left open into leaves: sub-questions one retrieval
act can settle. Decompose by governing principle, never by surface
feature. A leaf names a mechanism and a retrievable claim, not one noun
from the query. Surface-feature decomposition is the novice move (Chi,
Feltovich and Glaser 1981); the principle names what a search can actually
retrieve.

- A sub-question that needs another leaf's answer first is a derived
  link, not a leaf. Keep it out of the ledger; it appears at draft time
  as a `[~]` step. This keeps every round's fan-out set independent by
  construction.
- 3 to 10 leaves covers the worked range. Past 10, fold near-duplicates
  before searching; below 3, the loop degenerates gracefully.
- The leaf set is a starting frame, never an obligation. Expect
  uncertainty to rise in the first exploring round (Kuhlthau); spawn what
  workers surface (`"origin": "spawned"`), and let later evidence retire
  initial leaves without ceremony.

Register leaves as `leaves` entries in the round's `note` batch (schema
in the spine): keywords, question, origin. The output echoes the minted
identifiers; reference them by those.

## Bundled fan-out

The comprehensive view lives in the lead alone; a worker answers one
bundle of small, fast steps and returns. Partition the open leaves into
bundles, putting leaves that share a work area (one corpus, one
vocabulary, one governing principle) together and leaves that do not
apart. One worker per bundle; one to three bundles is typical. The
partition is the orthogonality guarantee: bundles are pairwise disjoint
and jointly cover the open set, so no two workers can duplicate work and
the join stays trivial.

Each dispatch carries a fixed overhead regardless of bundle size (minutes
of wall clock in some harnesses, roughly 15x chat cost in tokens), so
worker count, not bundle size, is the cost driver: prefer fewer, fuller,
orthogonal bundles over one worker per leaf. With a single bundle or no
sub-agent primitive, run the same contract inline; the ledger records no
worker identity, so both branches produce identical state.

The lead never reads a source page during fan-out; page content lives and
dies inside a worker, and only compressed closure proposals cross back.
Retrieval is mechanical work: when the harness offers model selection,
dispatch workers on a cheap, fast model tier and keep the lead on the
strong one; judgment concentrates at the join, not in the search.

## Dispatching workers

The subagent system prompt is the full text of `worker`: read it at
dispatch time, hand it to each worker verbatim, and append the bundle
fields. It already carries the efficiency norm, the search caps, the
parallel-query rule, source classing, the injection rule, and the
proposal schema; the brief adds only what varies per bundle:

<worker_brief>
objective: the bundle's leaf questions, verbatim, plus the session question for scope
output: one closure proposal per assigned leaf, as an array, nothing else
tools: web search and fetch; scholarly corpora via /lit-review; PDFs via /read-pdf
boundaries: the other bundles, named one line each, so the worker
  recognizes its border when a search wanders toward it
</worker_brief>

Proposals are untrusted input: workers touch fetched web content. The
lead admits proposals only through the script, whose validation is the
one trust boundary. Source classes are defined in the spine; workers tag
classes in their proposals and the lead re-judges any tag that looks
inflated.

## Admitting a round

The lead deduplicates proposal sources against the ledger, then admits
the whole round as one `note` batch: spawned leaves, sources, closes, and
the checkpoint together (schema in the spine). A rejected batch names its
violated invariant and appends nothing: fix the payload, never the
invariant. Candidates passed over stay out of the ledger and need no
ceremony; close an existing leaf you deliberately stop pursuing as
`unresolved` with reason `not_pursued` and the why.

## Checkpoint and the leave-or-stay call

Close each round with a `checkpoints` entry in the round's `note` batch,
carrying the round's declared search count (sum of workers'
`searches_spent`); the same output returns the updated yield table.

The yield table compares new sources per search across rounds. Falling
yield is the patch-leaving signal (Pirolli and Card's foraging model):
weigh leaving the current decomposition, either by re-framing the weak
leaves or by stopping. The script keeps the count; the call is yours.
Floors and ceilings:

- Two unproductive rounds: stop, close remaining open leaves as
  `unresolved`, and draft.
- Saturation never fires before one round past the declared focus.
- Rounds run one to three. Needing a fourth means the decomposition is
  wrong, not the search: re-frame the leaves and fold what collapsed.
- A one-round question has no comparison; the floor rule alone governs.

## Frame discipline

Treat anomalous evidence as a test of the frame, not noise (Klein's
data-frame theory: explaining anomalies away, "preserving", is the named
failure). Before closing any leaf `retrieved`, name what evidence would
have refuted it; a close that nothing could refute is premature closure,
the "thinking stops when the diagnosis is made" failure. A refuted
premise is a finding, not a miss: close it `refuted` with the premise,
and it feeds the Rival account.
