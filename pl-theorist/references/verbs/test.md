# Verb: test

Derive tests from code's algebra: state laws design relies on, then make
each checkable.

## Pipeline

### 1. Recover the laws

Run kernel's Reading Existing Code over target, then list laws
implementation implicitly relies on. Typical harvest:

| Structure in the code | Law to test |
| --- | --- |
| Fold/monoid aggregation | Identity element; associativity (required before any parallel/reassociated fold) |
| Parser/serializer pair | Roundtrip: `parse . print = id` on domain, and `print . parse` normalizes |
| Smart constructor | Total rejection: every invalid input refused; every accepted value satisfies invariant thereafter |
| Sum elimination | Exhaustiveness: one test per variant, including awkward ones |
| Idempotent effect or normalizer | `f . f = f` |
| Order-insensitive aggregation | Permutation invariance |
| Cache/index/memo | Coherence: cached answer equals recomputed answer |
| Optimized structure (heap, index, automaton) | Equivalence against naive $O(n^2)$ oracle on small inputs |

Tests accompany refactor that changes API (renamed functions, new types,
changed signatures): audit laws on pre-refactor code before suite exists.
Write each law against old API in throwaway script outside test tree, run it
on old code, record which laws held, then delete script and write suite
against new API. Running new suite on old code instead mixes two kinds of
failure: name or signature error (`ImportError`, `AttributeError`,
wrong-arity `TypeError`) is API difference; only failed assertion is law
failure. Report the two apart.

### 2. Choose the harness

Use repository's existing test framework and directory conventions. Use its
property-based library (Hypothesis, proptest, fast-check, QuickCheck, jqwik)
for laws above when present; otherwise encode each law over small fixed set
of representative and adversarial values. Add no property framework to
repository lacking one unless user asks.

### 3. Cover the boundaries

Beyond laws: empty input, single element, large-but-fast size, duplicate
keys, Unicode and empty strings where strings flow, error paths, effect
order, cancellation, resource cleanup on both success and failure.
Concurrency: test bound (capacity, ordering under contention), not just
happy path.

### 4. Guard the complexity

Stated bound matters: prefer operation-counting or oracle test over
wall-clock assertion: count comparisons/probes via instrumentation
repository already has, or assert result-equivalence against naive oracle at
sizes where naive form still runs. Wall-clock thresholds flaky; use only
where repository already has benchmark harness.

### 5. Run and report

Run new tests and narrowest surrounding suite under kernel's Validation.
Failing law test is finding about code: report it, keep law as written.

## Output Contract

Deliver tests, then report:

1. Laws derived, one line each, mapped to test names.
2. Boundary and effect coverage added.
3. Any law that failed and what it reveals.
4. Coverage declined (untestable effects, missing harness) and why.

## Completion Checks

<checklist for="verb">
  <item>Each law implementation relies on has named test or stated reason it cannot have one.</item>
  <item>Every sum variant and smart-constructor rejection path exercised.</item>
  <item>Optimized structures checked against naive oracle or operation count.</item>
  <item>Tests use repository's existing frameworks and conventions.</item>
  <item>Failing law tests reported as code findings, kept as written.</item>
  <item>Refactor changed API: laws audited on old code first; API errors reported apart from law failures.</item>
</checklist>
