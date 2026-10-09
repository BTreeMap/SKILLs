# Verb: design

Types-first domain modeling before code exists. Deliverable: domain model
whose invalid states are already dead on paper, effect boundary, complexity
budget. Write no implementation code beyond type sketches unless user asks
to proceed to `write`.

## Pipeline

### 1. Gather the forces

From request and repository (existing types, storage schemas, wire formats,
traffic or data-size hints), record: operations domain must support, their
expected frequencies and sizes, external systems touched,
consistency/latency constraints. Ask at most one focused question, only when
answer changes model.

### 2. Model states and transitions

Run kernel's Domain Modeling steps over whole domain.

### 3. Draw the effect boundary

Partition design into pure core (decisions, transitions, derivations) and
thin shell (storage, network, clock, randomness, UI). Each shell effect:
note idempotency, retry policy, transaction scope, cancellation, capability
or permission it requires.

### 4. Set the complexity budget

Each frequent operation: state expected size, target bound, structure
achieving it, from cost-signal table.

### 5. Plan for evolution

Name which sums likely grow variants (exhaustive matching then turns
additions into compiler-guided edits), which boundaries version their wire
formats, which invariants future maintainer most likely breaks.

## Output Contract

Return, in order:

1. Domain model: type sketches in target language (or neutral pseudocode
   when no language fixed), one-line invariant on each type.
2. Transition table or function signatures for pure core.
3. Effect boundary: shell effects with idempotency/retry/transaction notes.
4. Complexity budget table: operation, expected n, bound, structure.
5. Rejected alternative: one plausible model dismissed, with law or cost
   that killed it.
6. Open questions, at most three, each with default you will assume.

## Completion Checks

- Every meaningless field combination unrepresentable or explicitly
  justified.
- Every transition total or returns explicit rejection.
- Untrusted data enters through named smart-constructor boundaries only.
- Dominant operations carry stated bounds and structures.
- Effect boundary names idempotency, retries, transactions, required
  capabilities.
- One rejected alternative documented with its killing constraint.
