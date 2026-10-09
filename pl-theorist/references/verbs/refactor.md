# Verb: refactor

Behavior-preserving rewrite of existing code toward kernel's target
vocabulary. Kernel's preservation Core Law (values through externally
visible identity) binds every edit.

## Pipeline

### 1. Reconstruct the contract and recover the algebra

Run kernel's Reading Existing Code over target: record contract, then
classify each imperative region before rewriting it.

Run cost-signal table over same regions: nested scan hiding join, linear
search in loop, collection re-sorted per iteration. Sweep finds $O(n^2)$
shape under cosmetic rewrite: propose index or structure change as part of
same design, or as flagged follow-up when it would change behavior.

### 2. Propose the pure target

Start from strongest defensible FP representation:

- Immutable inputs and outputs.
- Closed domain states; no contradictory boolean or nullable combinations.
- Total pattern matches, explicit impossible cases.
- Curried, composable helpers where partial application removes duplication.
- Point-free composition where transformation stays locally readable.
- Native `map`, `filter`, `fold` vocabulary and native monadic operations.
- One explicit effect boundary.

Default collection teaching preference: explicit combinators over
comprehension syntax. Filter-transform shape: prefer target language's
equivalent of following when its profile permits:

<template for="filter-map">
results = map(process, filter(lambda x: x > 5, data))
</template>

Preference yields to clearer named predicate, fused native operator,
required eager collection type, or measured single-pass constraint.

### 3. Apply the cost guard

Evaluate pure target under kernel's Cost Guard with loaded profile's steps,
descending only as far as guard requires.

### 4. Implement narrowly

- Preserve public APIs unless changing them is requested.
- Reuse existing repository abstractions before introducing new ones.
- Add no FP library merely to obtain familiar names.
- Keep object/data layouts flat when wrappers add no semantic distinction.
- Delete obsolete mutable helpers and flags made impossible by new model.
- Comments state laws, invariants, non-obvious cost decisions.

### 5. Validate

Run kernel's Validation. Add or update tests for changed domain modeling,
empty inputs, error paths, evaluation timing, effect order, cancellation,
resource cleanup.

## Output Contract

Code-edit request: perform edit and checks. Then report briefly; fuller
explanation: user invokes `tell`:

1. Language profile loaded.
2. Recovered algebra and invalid state eliminated; why result is total, or
   where partiality remains.
3. Complexity before and after (or "unchanged") and cost-guard outcome,
   naming language constraint behind any one-level fallback.
4. Validation run; remaining uncertainty.

Advice or snippet: return contract assumptions, refactored form, PL
explanation, cost-model caveat.

## Completion Checks

<checklist for="verb">
  <item>Observable contract and effect order intact.</item>
  <item>Imperative control flow classified before transformation.</item>
  <item>Cost signals scanned alongside algebra; complexity regressions impossible; improvements stated or flagged.</item>
  <item>Any fallback descended only as far as cost model required.</item>
  <item>Point-free and curried forms easier to reason about than alternatives.</item>
  <item>Relevant automated checks pass or unavailable checks named.</item>
</checklist>
