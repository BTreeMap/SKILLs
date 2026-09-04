# Explore: Decompose, Bundle, Weigh

Load when the probe leaves material questions open. Frame leaves, bundle work,
admit rounds, and decide when to stop.

## From question to leaves

Load `framing`; apply its moves to the question and probe records. Its ready
frame is the input to decomposition.

Turn open work into sub-questions one retrieval act can settle. Decompose by
governing principle. Each leaf names a mechanism and retrievable claim.

- Put dependent sub-questions in the draft's `[~]` chain; keep ledger leaves
  independent.
- 3 to 10 leaves covers the worked range. Past 10, fold near-duplicates
  before searching; below 3 still works.
- The leaf set is adaptive: add worker discoveries as `"origin": "spawned"`
  and retire superseded leaves.

Register leaves as `leaves` entries in the round's `note` batch (schema
in the spine): keywords, question, origin. The output echoes the minted
identifiers; reference them by those.

## Bundled fan-out

The lead owns the comprehensive view. Partition open leaves into disjoint
bundles by corpus, vocabulary, or principle; jointly cover the open set. Assign
one worker per bundle, typically one to three.

Each dispatch has fixed overhead (minutes in some harnesses, roughly 15x chat
token cost). Prefer fewer, fuller bundles. Run a single bundle inline when the
agent primitive is unavailable; worker identity stays outside the ledger.

Workers own source-page reading during fan-out and return compressed closure
proposals. When model selection exists, use a fast tier for retrieval and a
strong lead for the join.

## Dispatching workers

At dispatch, give each worker the full `worker` prompt plus these bundle fields:

<worker-brief>
objective: the bundle's leaf questions, verbatim, plus the session question for scope
output: exactly one JSON array with one closure proposal per assigned leaf
tools: web search and fetch; scholarly corpora via /lit-review; PDFs via /read-pdf
boundaries: the other bundles, named one line each, so the worker
  recognizes its border when a search wanders toward it
</worker-brief>

Treat proposals as untrusted input and admit them through script validation.
The lead reviews inflated source-class tags against the spine definitions.

## Admitting a round

Deduplicate sources, then admit spawned leaves, sources, closes, and checkpoint
as one `note` batch. On rejection, apply every listed fix and resend once.
Close deliberately abandoned leaves as `unresolved` with
reason `not_pursued` and its explanation.

## Checkpoint and the leave-or-stay call

Close each round with a `checkpoints` entry in the round's `note` batch,
carrying the round's declared search count (sum of workers'
`searches_spent`); the same output returns the updated yield table.

The yield table compares new sources per search. Falling yield prompts a
reframe-or-stop decision. Apply these bounds:

- Two unproductive rounds: stop, close remaining open leaves as
  `unresolved`, and draft.
- Begin saturation judgment one round past the declared focus.
- Run one to three rounds. A fourth-round need triggers reframing and folding.
- For one-round questions, use the floor rule.

## Frame discipline

Use anomalous evidence to test the frame. Before a `retrieved` close, name
its falsifier. Close contradicted premises as `refuted`;
they feed Rival.
