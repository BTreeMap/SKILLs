# Verb: refactor

Behavior-preserving rewrite of existing code toward the kernel's target
vocabulary. The default verb. The kernel's preservation Core Law (values
through externally visible identity) binds every edit.

## Pipeline

### 1. Reconstruct the contract

Read the target, adjacent types, direct callers, and focused tests. Record:

- Input and output domains; ordering and duplicate semantics.
- Mutation, I/O, exceptions, async work, cancellation, and resource ownership.
- Eager or deferred evaluation; single-use or reusable traversal.
- Public type and identity guarantees.
- Known hot-path or memory constraints and real input sizes.
- Transaction, retry, idempotency, concurrency, and backpressure semantics.
- Required logging, tracing, metrics, and diagnostic context.

If code is supplied without repository context, state only assumptions capable
of affecting the result.

### 2. Recover the algebra

Classify each imperative region before rewriting it:

| Imperative signal | Algebraic reading |
| --- | --- |
| Append conditionally | `filter` followed by `map`, or `filterMap`/`choose` |
| Update accumulator | `fold`/`reduce` with a named invariant |
| Break on predicate | `find`, `any`, `all`, `takeWhile`, or short-circuit fold |
| Nullable/sentinel branch | `Option`/`Maybe` elimination |
| Exception-or-value flow | `Result`/`Either` composition |
| Flags controlling variants | Sum type plus exhaustive match |
| Mutable construction | Immutable constructor or validated builder boundary |
| Nested callbacks | Curried composition or `async`/`await` sequencing |
| Interleaved effects | Pure decision function plus effect interpreter |
| Partial operation | Total function returning `Option`/`Result`, or proved precondition |

Alongside the algebra, run the kernel's cost-signal table over the same
regions: a nested scan hiding a join, a linear search in a loop, a re-sorted
collection per iteration. When the sweep finds an $O(n^2)$ shape under the
cosmetic rewrite, propose the index or structure change as part of the same
design, or as a flagged follow-up when it would change behavior.

Distinguish collection algebra from state machines and resource protocols. Do
not force a resource lifetime or multi-step state transition into a cosmetic
pipeline.

### 3. Propose the pure target

Start from the strongest defensible FP representation:

- Immutable inputs and outputs.
- Closed domain states; no contradictory boolean or nullable combinations.
- Total pattern matches and explicit impossible cases.
- Curried, composable helpers where partial application removes duplication.
- Point-free composition where the transformation remains locally readable.
- Native `map`, `filter`, `fold` vocabulary and native monadic operations.
- One explicit effect boundary.

Default collection teaching preference: explicit combinators over
comprehension syntax. For a filter-transform shape,
prefer the target language's equivalent of the following when its profile
permits it:

<canonical_filter_map>
results = map(process, filter(lambda x: x > 5, data))
</canonical_filter_map>

This preference yields to a clearer named predicate, a fused native operator,
required eager collection type, or a measured single-pass constraint.

### 4. Apply the cost model

Evaluate the pure target against the loaded language profile:

- Stack growth and TCO guarantees.
- Intermediate collections, closures, wrappers, boxing, and heap escape.
- Laziness, strictness, repeated enumeration, and retained input.
- JIT object-shape or compiler optimization barriers.
- Borrowing, ownership, disposal, cancellation, and async scheduling.
- Early exit and traversal count.
- Boundedness, backpressure, retry amplification, and transaction scope.
- Instrumentation visibility and diagnostic stack quality.

On failure, descend exactly one abstraction level while preserving the algebra:

1. Structural recursion to a native iterator/stream pipeline.
2. Custom wrapper/transducer to a native monad or collection primitive.
3. Multi-pass collection chain to a fused operator or one reduction.
4. Higher-order hot path to a direct loop calling pure helpers.
5. Immutable whole-program copying to mutation confined to a fresh local value.

Stop descending once the guard passes. A disciplined loop is a valid backend
for a functional design; externally visible partial mutation is a defect.

### 5. Implement narrowly

- Preserve public APIs unless changing them is requested.
- Reuse existing repository abstractions before introducing new ones.
- Add no FP library merely to obtain familiar names.
- Keep object/data layouts flat when wrappers add no semantic distinction.
- Delete obsolete mutable helpers and flags made impossible by the new model.
- Comments state laws, invariants, and non-obvious cost decisions.

### 6. Explain the design

Name, briefly: the recovered algebra, the invalid state eliminated, why the
result is total or where partiality remains, the complexity before and after,
and the loaded language constraint behind any fallback. For a fuller teaching
treatment, the user invokes the `teach` verb.

### 7. Validate

Run the narrowest available formatter, typechecker, linter, and focused tests.
Add or update tests for changed domain modeling, empty inputs, error paths,
evaluation timing, effect order, cancellation, and resource cleanup. Test every
sum-type variant and smart-constructor rejection path. For a claimed hot-path
improvement, use an existing benchmark/profiler or label the cost conclusion
unmeasured.

## Output Contract

For a code-edit request, perform the edit and checks. Then report briefly:

1. Language profile loaded.
2. Algebra and invalid state made explicit.
3. Complexity delta (or "unchanged") and cost-guard outcome, including any
   one-level fallback.
4. Validation run and remaining uncertainty.

For advice or a snippet, return: contract assumptions, refactored form, PL
explanation, cost-model caveat.

## Completion Checks

<verb_checklist>
  <item>Observable contract and effect order remain intact.</item>
  <item>Imperative control flow was classified before transformation.</item>
  <item>Cost signals were scanned alongside the algebra; complexity regressions are impossible and improvements are stated or flagged.</item>
  <item>Any fallback descended only as far as the cost model required.</item>
  <item>Point-free and curried forms remain easier to reason about than alternatives.</item>
  <item>Relevant automated checks pass or unavailable checks are named.</item>
</verb_checklist>
