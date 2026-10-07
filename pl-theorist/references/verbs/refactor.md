# Verb: refactor

Behavior-preserving rewrite of existing code toward the kernel's target
vocabulary. The kernel's preservation Core Law (values through externally
visible identity) binds every edit.

## Pipeline

### 1. Reconstruct the contract and recover the algebra

Run the kernel's Reading Existing Code over the target: record the contract,
then classify each imperative region before rewriting it.

Run the cost-signal table over the same regions: a nested scan hiding a
join, a linear search in a loop, a re-sorted collection per iteration. When
the sweep finds an $O(n^2)$ shape under the cosmetic rewrite, propose the
index or structure change as part of the same design, or as a flagged
follow-up when it would change behavior.

### 2. Propose the pure target

Start from the strongest defensible FP representation:

- Immutable inputs and outputs.
- Closed domain states; no contradictory boolean or nullable combinations.
- Total pattern matches and explicit impossible cases.
- Curried, composable helpers where partial application removes duplication.
- Point-free composition where the transformation remains locally readable.
- Native `map`, `filter`, `fold` vocabulary and native monadic operations.
- One explicit effect boundary.

Default collection teaching preference: explicit combinators over
comprehension syntax. For a filter-transform shape, prefer the target
language's equivalent of the following when its profile permits it:

<template for="filter-map">
results = map(process, filter(lambda x: x > 5, data))
</template>

This preference yields to a clearer named predicate, a fused native
operator, required eager collection type, or a measured single-pass
constraint.

### 3. Apply the cost guard

Evaluate the pure target under the kernel's Cost Guard with the loaded
profile's steps, descending only as far as the guard requires.

### 4. Implement narrowly

- Preserve public APIs unless changing them is requested.
- Reuse existing repository abstractions before introducing new ones.
- Add no FP library merely to obtain familiar names.
- Keep object/data layouts flat when wrappers add no semantic distinction.
- Delete obsolete mutable helpers and flags made impossible by the new
  model.
- Comments state laws, invariants, and non-obvious cost decisions.

### 5. Validate

Run the kernel's Validation. Add or update tests for changed domain
modeling, empty inputs, error paths, evaluation timing, effect order,
cancellation, and resource cleanup.

## Output Contract

For a code-edit request, perform the edit and checks. Then report briefly;
for a fuller teaching treatment, the user invokes `teach`:

1. Language profile loaded.
2. Recovered algebra and the invalid state eliminated; why the result is
   total, or where partiality remains.
3. Complexity before and after (or "unchanged") and the cost-guard outcome,
   naming the language constraint behind any one-level fallback.
4. Validation run and remaining uncertainty.

For advice or a snippet, return: contract assumptions, refactored form, PL
explanation, cost-model caveat.

## Completion Checks

<checklist for="verb">
  <item>Observable contract and effect order remain intact.</item>
  <item>Imperative control flow was classified before transformation.</item>
  <item>Cost signals were scanned alongside the algebra; complexity regressions are impossible and improvements are stated or flagged.</item>
  <item>Any fallback descended only as far as the cost model required.</item>
  <item>Point-free and curried forms remain easier to reason about than alternatives.</item>
  <item>Relevant automated checks pass or unavailable checks are named.</item>
</checklist>
