# Verb: test

Derive tests from the code's algebra: state the laws the design relies on,
then make each one checkable. The suite is a proof sketch.

## Pipeline

### 1. Recover the algebra

Read the target as in `refactor` steps 1-2: contract, effects, and the
algebraic reading of each region. List the laws the implementation implicitly
relies on. Typical harvest:

| Structure in the code | Law to test |
| --- | --- |
| Fold/monoid aggregation | Identity element; associativity (required before any parallel/reassociated fold) |
| Parser/serializer pair | Roundtrip: `parse . print = id` on the domain, and `print . parse` normalizes |
| Smart constructor | Total rejection: every invalid input refused; every accepted value satisfies the invariant thereafter |
| Sum elimination | Exhaustiveness: one test per variant, including the awkward ones |
| Idempotent effect or normalizer | `f . f = f` |
| Order-insensitive aggregation | Permutation invariance |
| Cache/index/memo | Coherence: cached answer equals recomputed answer |
| Optimized structure (heap, index, automaton) | Equivalence against the naive $O(n^2)$ oracle on small inputs |

### 2. Choose the harness

Use the repository's existing test framework and directory conventions. Use
its property-based library (Hypothesis, proptest, fast-check, QuickCheck,
jqwik) for the laws above when present; otherwise encode each law over a small
fixed set of representative and adversarial values. Do not add a property
framework to a repository that lacks one unless the user asks.

### 3. Cover the boundaries

Beyond laws: empty input, single element, large-but-fast size, duplicate keys,
Unicode and empty strings where strings flow, error paths, effect order,
cancellation, and resource cleanup on both success and failure. For
concurrency, test the bound (capacity, ordering under contention), not just
the happy path.

### 4. Guard the complexity

Where a stated bound matters, prefer an operation-counting or oracle test over
a wall-clock assertion: count comparisons/probes via instrumentation the
repository already has, or assert result-equivalence against the naive oracle
at sizes where the naive form still runs. Wall-clock thresholds are flaky;
use them only where the repository already has a benchmark harness.

### 5. Run and report

Run the new tests and the narrowest surrounding suite. A failing law test is
a finding about the code: report it and keep the law as written.

## Output Contract

Deliver the tests, then report:

1. Laws derived, one line each, mapped to their test names.
2. Boundary and effect coverage added.
3. Any law that failed and what it reveals.
4. Coverage honestly declined (untestable effects, missing harness) and why.

## Completion Checks

<verb_checklist>
  <item>Each law the implementation relies on has a named test or a stated reason it cannot have one.</item>
  <item>Every sum variant and smart-constructor rejection path is exercised.</item>
  <item>Optimized structures are checked against a naive oracle or operation count.</item>
  <item>Tests use the repository's existing frameworks and conventions.</item>
  <item>Failing law tests are reported as code findings and kept as written.</item>
</verb_checklist>
