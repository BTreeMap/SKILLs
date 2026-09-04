# Verb: design

Types-first domain modeling before code exists. Deliverable: a domain model
whose invalid states are already dead on paper, an effect boundary, and a
complexity budget. Kill invalid states at the whiteboard, where deletion is
free.

## Pipeline

### 1. Gather the forces

From the request and the repository (existing types, storage schemas, wire
formats, traffic or data-size hints), record: the operations the domain must
support, their expected frequencies and sizes, the external systems touched,
and the consistency/latency constraints. Ask at most one focused question, and
only when the answer changes the model.

### 2. Enumerate states and transitions

- List every state the domain can occupy and every event that moves it.
- Encode alternatives as sums, simultaneous data as products, constrained
  primitives as refined/opaque types. Name each smart-constructor boundary
  where untrusted data enters.
- Walk the cartesian product of any proposed boolean/nullable fields and name
  the combinations that are meaningless; restructure until they are
  unrepresentable.
- Make each transition a total function `State -> Event -> State` (or
  `Result`); name the rejected transitions alongside the successful ones.

### 3. Draw the effect boundary

Partition the design into a pure core (decisions, transitions, derivations)
and a thin shell (storage, network, clock, randomness, UI). For each shell
effect, note: idempotency, retry policy, transaction scope, cancellation, and
what capability/permission it requires.

### 4. Set the complexity budget

For each frequent operation, state the expected size, the target bound, and
the structure that achieves it, using the kernel's cost-signal table.

### 5. Plan for evolution

Name which sums are likely to grow variants (exhaustive matching then turns
additions into compiler-guided edits), which boundaries version their wire
formats, and which invariants a future maintainer is most likely to break.

## Output Contract

Return, in order:

1. Domain model: type sketches in the target language (or neutral pseudocode
   when no language is fixed), with one-line invariants on each type.
2. Transition table or function signatures for the pure core.
3. Effect boundary: shell effects with idempotency/retry/transaction notes.
4. Complexity budget table: operation, expected n, bound, structure.
5. Rejected alternative: one plausible model dismissed, with the law or cost
   that killed it.
6. Open questions, at most three, each with the default you will assume.

No implementation code beyond type sketches unless the user asks to proceed to
`build`.

## Completion Checks

<checklist for="verb">
  <item>Every meaningless field combination is either unrepresentable or explicitly justified.</item>
  <item>Every transition is total or returns an explicit rejection.</item>
  <item>Untrusted data enters through named smart-constructor boundaries only.</item>
  <item>The dominant operations carry stated bounds and structures.</item>
  <item>The effect boundary names idempotency, retries, transactions, and required capabilities.</item>
  <item>One rejected alternative is documented with its killing constraint.</item>
</checklist>
